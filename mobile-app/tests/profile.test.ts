import { test } from "node:test";
import assert from "node:assert/strict";
import { newProfile, readProfile, profileName, recordRide } from "../src/profile.ts";
test("local names accept Unicode, reject empty and oversized values", () => {
  assert.equal(profileName("  Kush   Sharma  "), "Kush Sharma");
  assert.equal(profileName("कुश"), "कुश");
  assert.throws(() => profileName(" \n "));
  assert.throws(() => profileName("x".repeat(33)));
});
test("stored preferences validate values and unique learning progress", () => {
  const p = readProfile(JSON.stringify({ ...newProfile(), avatar: "invalid", units: "mph", learned: [1, 1, 0, -1, 4, "2"], rides: [{ samples: -1 }] }));
  assert.deepEqual(p.learned, [1, 0]);
  assert.equal(p.units, "km/h"); assert.equal(p.rides.length, 0);
  assert.throws(() => readProfile("broken"));
});
test("repeat frames and reconnect cannot multiply local ride history or samples", () => {
  const r = { id: "host/run/vehicle", role: "Rider", samples: 3, arrived: false, date: "2026-10-10" };
  let p = recordRide(newProfile(), r);
  p = recordRide(p, { ...r, samples: 0 });
  p = recordRide(p, { ...r, samples: 4, arrived: true });
  p = recordRide(p, r);
  assert.equal(p.rides.length, 1); assert.equal(p.rides[0].samples, 4); assert.equal(p.rides[0].arrived, true);
  for (let i = 0; i < 30; i++) p = recordRide(p, { ...r, id: String(i) });
  assert.equal(p.rides.length, 20);
});
