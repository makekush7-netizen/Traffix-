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
  constructor() {
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
