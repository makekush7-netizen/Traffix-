import { test } from "node:test";
import assert from "node:assert/strict";
import {
  serverAddress,
  invitation,
  validFrame,
  validWorld,
  validOwn,
  eligible,
} from "../src/protocol.ts";
const claim = {
  run_id: "run.1",
  session_id: "s.1",
  vehicle_id: "v.1",
  token: "private",
};
const frame = {
  run_id: "run.1",
  sim_time_s: 10,
  payload: {
    vehicle_id: "v.1",
    frame_id: "frame.1",
    state: "active",
    pose: { x_m: 1, y_m: 2, speed_mps: 0, edge_id: "e.1" },
  },
};
test("an incompatible host response cannot become a broken map or route", () => {
  assert.equal(
    validWorld({
      roads: [
        {
          shape: [
            [1, 2],
            [3, 4],
          ],
          width: 3,
          internal: false,
        },
      ],
    }),
    true,
  );
  assert.equal(validWorld({ roads: [] }), false);
  assert.equal(
    validOwn({
      role: "Rider",
      route_id: "route.demo.A",
      route_path: [
        [
          [1, 2],
          [3, 4],
        ],
      ],
      paused: false,
      ended: false,
    }),
    true,
  );
  assert.equal(
    validOwn({
      role: "Rider",
      route_id: "route.demo.A",
      route_path: null,
      paused: false,
      ended: false,
    } as any),
    false,
  );
});
test("host configuration rejects cleartext internet and credentials", () => {
  assert.equal(
    serverAddress("http://127.0.0.1:8004/driver"),
    "http://127.0.0.1:8004",
  );
  assert.equal(
    serverAddress("https://demo.example.org/api"),
    "https://demo.example.org",
  );
  assert.throws(() => serverAddress("http://demo.example.org"));
  assert.throws(() => serverAddress("https://user:pass@demo.example.org"));
  assert.throws(() => serverAddress("file:///tmp"));
  assert.throws(() => serverAddress("http://192.168.evil.example"));
});
test("QR invitation preserves the actual host and requires a code", () => {
  assert.deepEqual(
    invitation("http://192.168.137.1:8004/driver#join=abc123xy"),
    { code: "abc123xy", server: "http://192.168.137.1:8004" },
  );
  assert.throws(() => invitation("https://example.org/driver"));
  assert.throws(() => invitation("x"));
  assert.deepEqual(
    invitation(
      "traffix://join?code=abc123xy&server=http%3A%2F%2F127.0.0.1%3A8004",
    ),
    { code: "abc123xy", server: "http://127.0.0.1:8004" },
  );
});
test("wrong-run, wrong-vehicle and invalid poses cannot light up the map", () => {
  assert.ok(validFrame(frame, claim));
  assert.equal(validFrame({ ...frame, run_id: "run.2" }, claim), false);
  assert.equal(
    validFrame(
      { ...frame, payload: { ...frame.payload, vehicle_id: "v.2" } },
      claim,
    ),
    false,
  );
  assert.equal(
    validFrame(
      {
        ...frame,
        payload: {
          ...frame.payload,
          pose: { ...frame.payload.pose, speed_mps: NaN },
        },
      },
      claim,
    ),
    false,
  );
});
test("expired, stale, wrong-vehicle and arrived advice cannot be accepted", () => {
  const offer = {
    advisory_id: "a.1",
    vehicle_id: "v.1",
    kind: "reroute",
    message: "Route B",
    expires_sim_s: 20,
  };
  assert.ok(eligible(offer, frame, true));
  assert.equal(eligible(offer, frame, false), false);
  assert.equal(eligible({ ...offer, vehicle_id: "v.2" }, frame, true), false);
  assert.equal(eligible({ ...offer, expires_sim_s: 10 }, frame, true), false);
  assert.equal(
    eligible(
      offer,
      { ...frame, payload: { ...frame.payload, state: "arrived", pose: null } },
      true,
    ),
    false,
  );
});
