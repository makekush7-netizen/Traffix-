// Explicit integration test. Use a disposable response server, never a mentor run.
const assert = require("node:assert/strict");
const { TrafficClient } = require("./load-client.cjs");
const host = process.env.TRAFFIX_TEST_HOST || "http://127.0.0.1:8005";
async function waitFor(predicate, label) {
  const deadline = Date.now() + 15000;
  while (!predicate()) {
    assert.ok(Date.now() < deadline, "Timed out: " + label);
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
}
(async () => {
  const token = (await (await fetch(host + "/api/operator/bootstrap")).json())
    .token;
  const headers = {
    Authorization: "Bearer " + token,
    "Content-Type": "application/json",
  };
  const post = async (path, body) => {
    const r = await fetch(host + path, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    assert.ok(r.ok, path + " returned " + r.status);
    return r.json();
  };
  const operator = async () =>
    (await fetch(host + "/api/operator/state", { headers })).json();
  const client = new TrafficClient(
    () => {},
    () => {},
  );
  try {
    await client.configure(host);
    assert.ok(client.world.roads.length > 0);
    const join = await post("/api/operator/join", {
      vehicle_id: "veh.role.delivery",
    });
    await client.join(join.join_code);
    await waitFor(
      () => client.state.connection === "connected" && client.state.fresh,
      "bound frame",
    );
    assert.equal(client.state.frame.payload.vehicle_id, "veh.role.delivery");
    assert.equal(client.state.sharing, false);
    assert.equal((await operator()).accepted_uplinks, 0);
    client.toggle(true);
    await waitFor(
      () => client.state.sharing && client.state.samples > 0,
      "server-confirmed consent and sample",
    );
    await post("/api/control", { action: "play" });
    await waitFor(() => client.state.samples >= 3, "moving simulation samples");
    await post("/api/control", { action: "pause" });
    const accepted = (await operator()).accepted_uplinks;
    client.toggle(false);
    await waitFor(
      () => !client.state.sharing && !client.state.pending,
      "sharing withdrawal",
    );
    assert.equal(
      (await operator()).sessions.find(
        (s) => s.vehicle_id === "veh.role.delivery",
      ).reporting,
      false,
    );
    client.suspend();
    client.connect();
    await waitFor(
      () => client.state.connection === "connected",
      "session reconnect",
    );
    assert.equal(client.state.sharing, false);
    assert.equal((await operator()).accepted_uplinks, accepted);
    await post("/api/control", { action: "reset", scenario: "rain", seed: 42 });
    await waitFor(
      () => client.state.connection === "rejoin",
      "reset invalidates session",
    );
    console.log(
      JSON.stringify(
        {
          passed: true,
          host,
          actualAdapter: true,
          source: "emulated_probe",
          acceptedUplinks: accepted,
          checks: [
            "own vehicle frame",
            "zero uplinks before consent",
            "confirmed sharing",
            "validated samples",
            "withdrawal",
            "reconnect consent off",
            "reset rejoin",
          ],
        },
        null,
        2,
      ),
    );
  } finally {
    client.suspend();
    await post("/api/control", { action: "pause" });
  }
})().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
