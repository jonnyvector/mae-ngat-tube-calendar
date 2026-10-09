import { test } from "node:test";
import assert from "node:assert/strict";
import { loadLogic } from "./harness.mjs";
import { fixture } from "./fixture.mjs";

const L = loadLogic(fixture);

test("observed days classify by the tube line", () => {
  assert.equal(L.classify("2026-01-01").kind, "no");
  assert.equal(L.classify("2026-01-03").kind, "yes");
  assert.equal(L.classify("2026-01-08").kind, "no");   // latest reading is observed, not forecast
});

test("forecast days classify into bands, boundaries inclusive", () => {
  assert.equal(L.classify("2026-01-09").kind, "good");
  assert.equal(L.classify("2026-01-12").kind, "good");     // p === T.good
  assert.equal(L.classify("2026-01-10").kind, "maybe");
  assert.equal(L.classify("2026-01-13").kind, "maybe");    // p === T.possible
  assert.equal(L.classify("2026-01-11").kind, "unlikely");
});

test("dates with no data classify as null", () => {
  assert.equal(L.classify("2025-12-31"), null);
  assert.equal(L.classify("2026-02-01"), null);
});

test("weekendDays counts Saturdays and Sundays", () => {
  assert.equal(L.weekendDays("2026-01-09", "2026-01-12"), 2);  // Fri..Mon
});

test("reliability is empty without a backtest", () => {
  const L2 = loadLogic({ ...fixture, backtest: null });
  assert.equal(L2.reliability("2026-01-09", L2.classify("2026-01-09")), "");
});
