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

test("moodFor maps every day kind to a rat", () => {
  assert.equal(L.moodFor("yes"), "tubable");
  assert.equal(L.moodFor("good"), "good");
  assert.equal(L.moodFor("maybe"), "possible");
  assert.equal(L.moodFor("no"), "dry");
  assert.equal(L.moodFor("unlikely"), "dry");
  assert.equal(L.moodFor(undefined), "sleep");
  for (const m of ["tubable", "good", "possible", "dry", "sleep"]) assert.ok(L.RAT_ALT[m]);
});

test("hero copy", () => {
  assert.equal(L.heroVerdict({ tubable: true }), "Send it!");
  assert.equal(L.heroVerdict({ tubable: false }), "Rat's waiting.");
  assert.match(L.heroLine({ outflow: 0.42, tubable: false }), /letting out <b>0\.42<\/b> million m³\/day\. Tubing starts at <b>0\.8<\/b>\./);
  assert.doesNotMatch(L.heroLine({ outflow: 0.42, tubable: false }), /into the river/);
  assert.match(L.heroLine({ outflow: 1.24, tubable: true }), /about <b>10\.1<\/b> m³\/s into the river/);
});

test("ctaText names the next window, or nothing", () => {
  assert.equal(L.ctaText(fixture.windows[0]), "Next float: 9 Jan–12 Jan · 68%");
  assert.equal(L.ctaText(undefined), "");
});

test("dayVerdict covers observed, forecast and missing days", () => {
  assert.equal(L.dayVerdict("2026-01-03", L.classify("2026-01-03")).title, "It was flowing!");
  assert.equal(L.dayVerdict("2026-01-01", L.classify("2026-01-01")).title, "Dry rocks.");
  const f = L.dayVerdict("2026-01-10", L.classify("2026-01-10"));   // a Saturday
  assert.equal(f.title, "Possible · 45%");
  assert.match(f.line, /on this weekend day/);
  assert.doesNotMatch(L.dayVerdict("2026-01-09", L.classify("2026-01-09")).line, /weekend/);   // a Friday
  // spread: objects built inside the vm have another realm's prototype, which deepEqual rejects
  assert.deepEqual({ ...L.dayVerdict("2026-02-01", null) }, { title: "No data.", line: "No reading or forecast for this date." });
});

test("derived releases say so", () => {
  assert.match(L.dayVerdict("2026-01-06", L.classify("2026-01-06")).line, /estimated from the change in storage/);
});

test("monthStats and monthMood", () => {
  const s = { ...L.monthStats(2026, 0) };
  assert.deepEqual(s, { yes: 5, no: 3, good: 2, maybe: 2, unlikely: 1, none: 18 });
  assert.equal(L.monthMood(s), "yes");
  assert.equal(L.monthMood(L.monthStats(1990, 0)), "none");
  assert.equal(L.monthTag(s), "5 tubable · 2 good · 2 maybe");
  assert.equal(L.monthTag(L.monthStats(1990, 0)), "no data");
  assert.equal(L.monthMood({ yes: 2, no: 0, good: 2, maybe: 0, unlikely: 0, none: 27 }), "yes");   // ties go to the more tubable kind
  assert.equal(L.monthMood({ yes: 0, no: 3, good: 0, maybe: 0, unlikely: 3, none: 25 }), "no");
  assert.equal(L.monthTag({ yes: 0, no: 0, good: 0, maybe: 0, unlikely: 9, none: 22 }), "unlikely");
});

test("stepMonth clamps to the 12 shown months", () => {
  assert.equal(L.stepMonth(0, -1), 0);
  assert.equal(L.stepMonth(11, 1), 11);
  assert.equal(L.stepMonth(4, 1), 5);
});

test("isSwipe ignores vertical scrolls and small drags", () => {
  assert.equal(L.isSwipe(-60, 10), true);
  assert.equal(L.isSwipe(30, 0), false);
  assert.equal(L.isSwipe(60, 50), false);
});

test("thaiDate uses the Buddhist year", () => {
  assert.equal(L.thaiDate("2026-01-10"), "10 ม.ค. 2569");
});

test("prefs survive a throwing or missing store", () => {
  const bad = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };
  assert.equal(L.readPref(bad, "nerd", "closed"), "closed");
  assert.doesNotThrow(() => L.writePref(bad, "nerd", "open"));
  assert.equal(L.readPref(undefined, "nerd", "closed"), "closed");
  const mem = new Map(); const ok = { getItem: k => mem.get(k) ?? null, setItem: (k, v) => mem.set(k, v) };
  L.writePref(ok, "nerd", "open");
  assert.equal(L.readPref(ok, "nerd", "closed"), "open");
});

test("reliability picks the nearest backtest lead and band", () => {
  assert.equal(L.reliability("2026-01-09", L.classify("2026-01-09")), "1 day out. Days we called “good odds” this far ahead were tubable 85% of the time.");
  assert.equal(L.reliability("2026-01-13", L.classify("2026-01-13")), "5 days out. Days we called “possible” this far ahead were tubable 50% of the time.");
});

test("todayISO uses Thai time", () => {
  assert.equal(L.todayISO(new Date("2026-01-08T16:59:00Z")), "2026-01-08");   // 23:59 in Bangkok
  assert.equal(L.todayISO(new Date("2026-01-08T17:00:00Z")), "2026-01-09");   // midnight in Bangkok
});

test("hero says today, or how old the reading is", () => {
  assert.equal(L.heroDateLabel("2026-01-08", "2026-01-08"), "Today · Thu 8 Jan");
  assert.equal(L.heroDateLabel("2026-01-08", "2026-01-10"), "Last reading · Thu 8 Jan");
  assert.equal(L.heroVerdict({ tubable: true }, false), "Was flowing.");
  assert.equal(L.heroVerdict({ tubable: false }, false), "Rat was waiting.");
  assert.match(L.heroLine({ outflow: 0.42, tubable: false }, false), /^Dam was letting out <b>0\.42<\/b>/);
});
