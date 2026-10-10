const { test } = require("node:test");
const assert = require("node:assert/strict");
const { TrafficClient } = require("./load-client.cjs");
const claim = {
  run_id: "run.1",
  session_id: "s.1",
  vehicle_id: "v.1",
  token: "private",
};
class Socket {
  static OPEN = 1;
  static instances = [];
  readyState = 1;
  sent = [];
  constructor(url) {
    this.url = url;
    Socket.instances.push(this);
  }
  send(data) {
    this.sent.push(JSON.parse(data));
  }
  close() {
    this.readyState = 3;
    this.onclose?.({ code: 1000, reason: "" });
  }
  message(type, payload, time = 10, run = "run.1") {
    this.onmessage({
      data: JSON.stringify({
        type,
        payload,
        seq: 1,
        sim_time_s: time,
        run_id: run,
      }),
    });
  }
}
function setup(t) {
  const ws = global.WebSocket,
    fetch = global.fetch;
  global.WebSocket = Socket;
  global.fetch = async () => ({
    ok: true,
    json: async () => ({ route_id: "route.demo.A", paused: false }),
  });
  const client = new TrafficClient(
    () => {},
    () => {},
  );
  client.server = "http://127.0.0.1:8004";
  client.restore(claim, 4);
  const socket = Socket.instances.at(-1);
  socket.onopen();
  socket.message("session.ready", { vehicle_id: "v.1" });
  t.after(() => {
    client.suspend();
    global.WebSocket = ws;
    global.fetch = fetch;
  });
  return { client, socket };
}
const pose = { x_m: 1, y_m: 2, speed_mps: 3, edge_id: "e.1" };
const frame = { frame_id: "f.1", vehicle_id: "v.1", state: "active", pose };
test("joining and new frames never enable sharing without confirmed consent", (t) => {
  const { client, socket } = setup(t);
  socket.message("vehicle.frame", frame);
  assert.equal(
    socket.sent.some((m) => m.type === "probe.sample"),
    false,
  );
  client.toggle(true);
  assert.equal(client.state.sharing, false);
  const toggle = socket.sent.at(-1);
  socket.message("ack", {
    in_reply_to: toggle.msg_id,
    status: "applied",
    reason: "sharing_on",
  });
  assert.equal(client.state.sharing, true);
  assert.equal(socket.sent.filter((m) => m.type === "probe.sample").length, 1);
  socket.message("vehicle.frame", frame);
  assert.equal(socket.sent.filter((m) => m.type === "probe.sample").length, 1);
  socket.message("vehicle.frame", { ...frame, vehicle_id: "other" });
  socket.message(
    "vehicle.frame",
    { ...frame, frame_id: "wrong-run" },
    11,
    "run.2",
  );
  assert.equal(socket.sent.filter((m) => m.type === "probe.sample").length, 1);
});
test("route is never claimed applied before acknowledgment; expired advice cannot send a decision", (t) => {
  const { client, socket } = setup(t);
  socket.message("vehicle.frame", frame);
  socket.message("guidance", {
    advisory_id: "a.1",
    vehicle_id: "v.1",
    kind: "reroute",
    message: "Try B",
    expires_sim_s: 20,
  });
  client.decide("accept");
  assert.equal(client.state.pending, true);
  assert.match(client.state.notice, /has not changed/);
  const decision = socket.sent.at(-1);
  socket.message("ack", {
    in_reply_to: decision.msg_id,
    status: "rejected",
    reason: "bypass_blocked",
  });
  assert.match(client.state.notice, /busy/);
  socket.message("guidance", {
    advisory_id: "a.2",
    vehicle_id: "v.1",
    kind: "reroute",
    message: "Try B",
    expires_sim_s: 9,
  });
  const count = socket.sent.length;
  client.decide("accept");
  assert.equal(socket.sent.length, count);
});
test("reconnect and app suspension withdraw consent and old sockets cannot inject advice", (t) => {
  const { client, socket } = setup(t);
  socket.message("vehicle.frame", frame);
  client.state.sharing = true;
  client.connect();
  assert.equal(client.state.sharing, false);
  assert.equal(client.state.fresh, false);
  socket.message("guidance", {
    advisory_id: "old",
    vehicle_id: "v.1",
    kind: "reroute",
    expires_sim_s: 20,
  });
  assert.equal(client.state.offer, null);
  client.suspend();
  assert.equal(client.state.connection, "offline");
  assert.equal(client.state.sharing, false);
});
test("run reset requires rejoin rather than reconnecting an obsolete vehicle", (t) => {
  const { client, socket } = setup(t);
  socket.onclose({ code: 1008, reason: "run_reset" });
  assert.equal(client.state.claim, null);
  assert.equal(client.state.connection, "rejoin");
});
test("v2 discovery loads no admin map and claim loads only driver-authorized geometry", async (t) => {
  const oldFetch = global.fetch, oldSocket = global.WebSocket;
  global.WebSocket = Socket;
  const calls = [];
  const world = { roads: [{ id: "edge.1", width: 4, internal: false, shape: [[0, 0], [10, 10]] }] };
  global.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    const data = url.endsWith('/capabilities') ? { api_version: "2.0" } : url.endsWith('/claim') ? claim : world;
    return { ok: true, status: 200, json: async () => data };
  };
  const client = new TrafficClient(() => {}, () => {});
  t.after(() => { client.suspend(); global.fetch = oldFetch; global.WebSocket = oldSocket; });
  assert.equal(await client.configure('http://127.0.0.1:8013'), null);
  assert.equal(calls.length, 1);
  await client.join('valid-code');
  assert.match(calls[1].url, /\/api\/v2\/phones\/claim$/);
  assert.match(calls[2].url, /\/api\/v2\/phones\/world\?/);
  assert.equal(calls[2].options.headers.Authorization, 'Bearer private');
  assert.deepEqual(client.world, world);
  assert.match(Socket.instances.at(-1).url, /\/api\/v2\/phones\/ws$/);
  assert.equal(client.state.sharing, false);
  assert.equal(calls.some(c => /\/api\/v2\/world/.test(c.url)), false);
});
test("v2 own-trip rejects another vehicle's events and accepts scoped route restrictions", async (t) => {
  const oldFetch = global.fetch, oldSocket = global.WebSocket;
  global.WebSocket = Socket;
  let vehicle = 'other';
  const event = { event_id: 'event.1', edge_id: 'edge.1', kind: 'blockage', status: 'active', start_s: 0, end_s: 30, effect: 'Simulated speed restriction' };
  global.fetch = async () => ({ ok: true, status: 200, json: async () => ({ api_version: '2.0', run_id: 'run.1', vehicle_id: vehicle, role: 'Car', route_id: 'unified.route', route_path: ['edge.1'], paused: true, ended: false, route_events: [event] }) });
  const client = new TrafficClient(() => {}, () => {});
  client.server = 'http://127.0.0.1:8013';
  client.world = { roads: [{ id: 'edge.1', width: 4, internal: false, shape: [[0, 0], [1, 1]] }] };
  t.after(() => { client.suspend(); global.fetch = oldFetch; global.WebSocket = oldSocket; });
  client.restore({ ...claim, api_version: '2.0' }, 0);
  const socket = Socket.instances.at(-1); socket.onopen(); socket.message('session.ready', { vehicle_id: 'v.1' });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(client.state.own, null);
  vehicle = 'v.1';
  await client.pollOwn();
  assert.deepEqual(client.state.own.events, [event]);
  assert.deepEqual(client.state.own.route_path, [[[0, 0], [1, 1]]]);
  assert.equal(client.state.sharing, false);
});
