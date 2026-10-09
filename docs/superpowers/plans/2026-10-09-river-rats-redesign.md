# Mae Ngat River Rats Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Mae Ngat tube calendar as a bright retro river-trip poster with a mood-matching river rat mascot: first in Pencil (`design/river-rats.pen`), then built into `app/template.html`.

**Architecture:** The page stays one static template. `scripts/build_app.py` replaces `/*__DATA__*/null` with the `D` JSON object. All pure logic (date maths, classification, copy, month stats, preferences) moves into a block marked `// logic:start` / `// logic:end`. A Node test harness evaluates just that block against a small fixture `D`. The DOM code (render functions, pager, sheet) sits below the block and is verified in Chrome. The rat art is generated in Pencil, exported as WebP into `app/img/`, and published next to `index.html`.

**Tech Stack:**
- page: plain HTML/CSS/JS, Google Fonts (Shrikhand, Mitr, Sarabun, IBM Plex Mono)
- tests: Node 22 `node:test`
- design and art: Pencil MCP (`execute`, `Generate`, `Export`)
- image compression: `cwebp`
- build: existing Python `.venv` for `build_app.py`

**Spec:** `docs/superpowers/specs/2026-10-09-river-rats-redesign-design.md`. Read it before any task; the frames and the template must match it.

## Global Constraints

- Work only in the worktree `/Users/jonathanhicks/dev/mae-gnat-river-rats` on branch `redesign/river-rats`. Never switch branches in `/Users/jonathanhicks/dev/mae-gnat-dam-flow-predictor`: its launchd job commits data there twice a day.
- The data contract does not change. Keep the line `const D = /*__DATA__*/null;` exactly, and don't edit `scripts/build_app.py`.
- Light theme only. Delete all `prefers-color-scheme` and `[data-theme]` CSS.
- Wordmark: `MAE NGAT RIVER RATS`. The river is always spelled "Ngat".
- Thresholds always come from `D.thresholds` (`tube` 0.8, `good` 0.6, `possible` 0.3, `canal` 0.37). Never hard-code them in logic.
- Colour tokens. Two values differ from the spec on purpose: they are the contrast-tuned values, and Task 1's contrast test enforces them.
  - `--paper #FFF3DC`, `--card #FFFAF0`, `--ink #2A1A10`, `--ink-muted #6B5444`
  - `--river #087A72` (spec `#0B8A80` gave cream text only 4.07:1)
  - `--river-ink #06625B` (odds text on tint), `--river-tint #BFE6E0`, `--river-faint #E4F3EF`
  - `--lagoon #5CC8B8`, `--sun #FFC23D`, `--sand #EBDDC2`, `--tube #FF5E2B`
  - `--hibiscus #EC5585` (spec `#E8457A` gave ink text 4.44:1)
- Text on `--tube` and `--hibiscus` is always `--ink`, never cream.
- Orange (`--tube`) is only for buttons and calls to action. It never marks a day, today or a weekend.
- Minimum tap target 44px. Motion only under `prefers-reduced-motion: no-preference`.
- No CI and no GitHub Actions. All checks run locally.
- Every command Jonny runs is a short script in the repo root (`./test`, `./calendar`, `./publish`). Don't hand him long commands.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.

## Review Focus

1. **A date with neither history nor forecast** (before 2000, after the last forecast day, or a gap). The cell is disabled; if reached, the sheet shows "No data." and the sleeping rat, and nothing throws. Pinned in Task 2 (`dayVerdict(s, null)`, `moodFor(undefined)`).
2. **No tubing windows in the next 12 months.** The hero shows no CTA, the floats section shows the sleeping rat and "Nothing on the horizon for 12 months.", and the default selection falls back to the first forecast day. Pinned in Task 2 (`ctaText(undefined)`).
3. **Forecast probability exactly on a band boundary** (`p === T.good` or `p === T.possible`). `p === T.good` is "good" and `p === T.possible` is "maybe", matching `build_app.band()`. Pinned in Task 1.
4. **A vertical scroll that starts on the month card.** It must scroll the page, not flip the month. A month only changes when the horizontal movement is over 40px and over 1.5× the vertical. Pinned in Task 2 (`isSwipe`).
5. **localStorage missing or throwing** (private mode, blocked storage). The nerd-stats panel still renders, closed, and toggling it doesn't throw. Pinned in Task 2 (`readPref`/`writePref`).

---

## File Structure

| Path | Status | Responsibility |
|---|---|---|
| `app/template.html` | rewrite | The page: CSS, markup, the logic block, DOM rendering |
| `app/img/rat-{tubable,good,possible,dry,sleep}.webp`, `app/img/tube.webp` | create | Mascot art and the tube badge |
| `tests/logic.test.mjs` | create | Unit tests for the logic block |
| `tests/contrast.test.mjs` | create | Checks that the colour tokens in `template.html` meet AA |
| `tests/harness.mjs` | create | Loads the logic block from `template.html` into a VM with a fixture `D` |
| `tests/fixture.mjs` | create | A small, hand-checkable `D` object |
| `test` | create | `./test` runs `node --test tests/` |
| `publish` | modify | Also copy `app/img` to gh-pages |
| `design/river-rats.pen` | create | Pencil design: style guide, art, phone and desktop frames |

---

### Task 1: Test harness and logic block (no visible change)

Moves the existing pure functions into a marked block and puts them under test before anything changes. The page must look exactly the same after this task.

**Files:**
- Modify: `app/template.html:164-201` (script top: constants through `LABEL`)
- Create: `tests/harness.mjs`, `tests/fixture.mjs`, `tests/logic.test.mjs`, `tests/contrast.test.mjs`, `test`

**Interfaces:**
- Produces: `loadLogic(D) -> object` (from `tests/harness.mjs`). Each name listed in the block's `// exports:` line becomes a property. `fixture` (from `tests/fixture.mjs`) is the D object described below.
- Produces: `cssTokens() -> Record<string,string>` (from `tests/harness.mjs`), which parses the first `:root { ... }` block of the template.

- [ ] **Step 1: Set up the worktree so the build runs**

```bash
cd /Users/jonathanhicks/dev/mae-gnat-river-rats
ln -s ../mae-gnat-dam-flow-predictor/.venv .venv
./calendar
```
Expected: it prints "Built .../app/index.html ..." and the current page opens. (`.venv/` is gitignored, so the symlink is never committed.)

- [ ] **Step 2: Write the fixture**

Create `tests/fixture.mjs`:

```js
// A tiny D: history 1–8 Jan 2026 (latest = 8 Jan), forecast 9–11 Jan. 1 Jan 2026 is a Thursday.
export const fixture = {
  generated: "2026-01-08",
  latest: "2026-01-08",
  now: { pct: 61.5, outflow: 0.42, inflow: 0.2, tubable: false },
  enso_now: { oni: -0.6, phase: "la_nina" },
  thresholds: { tube: 0.8, good: 0.6, possible: 0.3, canal: 0.37 },
  month_odds: [0.2, 0.55, 0.62, 0.48, 0.1, 0.05, 0.08, 0.12, 0.2, 0.3, 0.25, 0.15],
  windows: [{ start: "2026-01-09", end: "2026-01-12", days: 4, band: "good", p_max: 0.8, p_avg: 0.68 }],
  forecast: [
    { date: "2026-01-09", p: 0.8, median: 0.95, q75: 1.2 },
    { date: "2026-01-10", p: 0.45, median: 0.7, q75: 0.9 },
    { date: "2026-01-11", p: 0.1, median: 0.4, q75: 0.55 },
    { date: "2026-01-12", p: 0.6, median: 0.85, q75: 1.0 },
    { date: "2026-01-13", p: 0.3, median: 0.6, q75: 0.8 },
  ],
  history: {
    start: "2026-01-01",
    out:     [0.5, 0.5, 0.9, 0.9, 1.0, 1.1, 0.9, 0.42],
    pct:     [60, 60, 61, 61, 62, 62, 61, 61.5],
    inflow:  [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
    derived: [0, 0, 0, 0, 0, 1, 0, 0],
    rain:    [0, 1.5, null, 0, 0, 0, 2, 0],
    enso: { "2026-01": [-0.6, "la_nina"] },
  },
  backtest: { years: [2019, 2024], leads: [
    { lead_days: 1, hit_rate: 0.9, band_rate: { good: 0.85, possible: 0.5, unlikely: 0.1 } },
    { lead_days: 30, hit_rate: 0.7, band_rate: { good: 0.64, possible: 0.4, unlikely: 0.12 } },
  ] },
};
```

- [ ] **Step 3: Write the harness**

Create `tests/harness.mjs`:

```js
import fs from "node:fs";
import vm from "node:vm";

const SRC = fs.readFileSync(new URL("../app/template.html", import.meta.url), "utf8");

// Runs the code between "// logic:start" and "// logic:end" with a given D and returns its exports.
// The block's first line after logic:start is "// exports: a, b, c".
export function loadLogic(D) {
  const m = SRC.match(/\/\/ logic:start\n\/\/ exports: ([^\n]+)\n([\s\S]*?)\/\/ logic:end/);
  if (!m) throw new Error("template.html has no // logic:start ... // logic:end block");
  const names = m[1].split(",").map(s => s.trim());
  const ctx = vm.createContext({ D: structuredClone(D) });
  return vm.runInContext(`${m[2]}\n;({${names.join(",")}})`, ctx);
}

export function cssTokens() {
  const root = SRC.match(/:root\s*{([^}]*)}/)[1];
  return Object.fromEntries([...root.matchAll(/--([\w-]+):\s*([^;]+);/g)].map(x => [x[1], x[2].trim()]));
}
```

- [ ] **Step 4: Write the failing tests**

Create `tests/logic.test.mjs`:

```js
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
```

Create `tests/contrast.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { cssTokens } from "./harness.mjs";

const lum = hex => {
  const c = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map(v => v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

// [text token, background token]: every text/background pairing the page uses
const PAIRS = [
  ["ink", "paper"], ["ink", "card"], ["ink-muted", "paper"], ["ink-muted", "card"],
  ["card", "river"], ["ink", "river-tint"], ["river-ink", "river-tint"],
  ["ink", "river-faint"], ["ink-muted", "river-faint"], ["ink", "tube"], ["ink", "hibiscus"],
  ["ink", "lagoon"], ["ink", "sand"], ["ink-muted", "sand"],
];

test("text tokens meet WCAG AA (4.5:1)", () => {
  const t = cssTokens();
  for (const [fg, bg] of PAIRS) {
    assert.ok(t[fg] && t[bg], `missing token --${fg} or --${bg}`);
    const r = ratio(t[fg], t[bg]);
    assert.ok(r >= 4.5, `--${fg} on --${bg} is ${r.toFixed(2)}:1`);
  }
});
```

Create `test` (then `chmod +x test`):

```sh
#!/bin/sh
# Run the page's unit tests (logic block + colour contrast)
cd "$(dirname "$0")" && node --test tests/
```

- [ ] **Step 5: Run the tests and confirm they fail**

Run: `./test`
Expected: FAIL. `logic.test.mjs` throws "template.html has no // logic:start ... // logic:end block". The contrast test fails on "missing token --paper" (the old template uses `--bg`).

- [ ] **Step 6: Add the logic block to the current template**

In `app/template.html`, find the script that starts with `const D = /*__DATA__*/null;` and ends at the `LABEL` line. Wrap everything from `const T = D.thresholds;` through `const LABEL = ...` in the markers. Then move `weekendDays`, `sameDayHistory` and `reliability` inside the block, just above `// logic:end`, cutting them from where they are now. The top of the script becomes:

```js
const D = /*__DATA__*/null;
// logic:start
// exports: T, classify, observed, weekendDays, sameDayHistory, reliability, LABEL, parse, utc, iso, isWeekend, fmt, toRiver, short, longDate
const T = D.thresholds;
...                       // existing code unchanged, through const LABEL = {...};
function weekendDays(a, b) { ... }        // moved, unchanged
function sameDayHistory(s) { ... }        // moved, unchanged
function reliability(s, c) { ... }        // moved, unchanged
// logic:end
```

Don't change any function body. The contrast test stays red until Task 7 replaces the CSS. That's expected, so leave it failing and note it in the commit message.

- [ ] **Step 7: Run the tests**

Run: `./test`
Expected: all 5 tests in `logic.test.mjs` PASS. `contrast.test.mjs` FAILS with "missing token --paper" (expected until Task 7).

- [ ] **Step 8: Check the page is unchanged**

Run: `./calendar`
Expected: the page looks exactly as before. Click a day: the sheet updates. The DevTools console shows no errors.

- [ ] **Step 9: Commit**

```bash
git add app/template.html tests test
git commit -m "Add logic block and Node tests for the tube calendar page

Contrast test is expected to fail until the new palette lands.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: New pure logic (mood, copy, month stats, swipe, prefs)

**Files:**
- Modify: `app/template.html` (inside the logic block)
- Test: `tests/logic.test.mjs`

**Interfaces:**
- Consumes: `classify`, `fmt`, `toRiver`, `isWeekend`, `LABEL`, `T`, `parse`, `iso` from Task 1.
- Produces (all added to the `// exports:` line):
  - `moodFor(kind?: string) -> "tubable"|"good"|"possible"|"dry"|"sleep"`
  - `RAT_ALT: Record<mood, string>`
  - `heroVerdict(now) -> string`
  - `heroLine(now) -> string` (HTML)
  - `ctaText(w?: window) -> string` (`""` when there is no window)
  - `dayVerdict(s: string, c: ReturnType<classify>) -> {title: string, line: string}`
  - `monthStats(y: number, m: number) -> {yes,no,good,maybe,unlikely,none}`
  - `monthMood(stats) -> "yes"|"good"|"maybe"|"no"|"unlikely"|"none"`
  - `monthTag(stats) -> string`
  - `stepMonth(i: number, delta: number, n = 12) -> number`
  - `isSwipe(dx: number, dy: number) -> boolean`
  - `thaiDate(s) -> string`
  - `readPref(store, key, dflt) -> string`, `writePref(store, key, value) -> void`

- [ ] **Step 1: Write the failing tests** (append to `tests/logic.test.mjs`)

```js
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
  assert.deepEqual(L.dayVerdict("2026-02-01", null), { title: "No data.", line: "No reading or forecast for this date." });
});

test("derived releases say so", () => {
  assert.match(L.dayVerdict("2026-01-06", L.classify("2026-01-06")).line, /estimated from the change in storage/);
});

test("monthStats and monthMood", () => {
  const s = L.monthStats(2026, 0);
  assert.deepEqual(s, { yes: 5, no: 3, good: 2, maybe: 2, unlikely: 1, none: 18 });
  assert.equal(L.monthMood(s), "yes");
  assert.equal(L.monthMood(L.monthStats(1990, 0)), "none");
  assert.equal(L.monthTag(s), "5 tubable · 2 good · 2 maybe");
  assert.equal(L.monthTag(L.monthStats(1990, 0)), "no data");
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
```

Hand-check of `monthStats(2026, 0)`:
- yes: 3–7 Jan are 0.9, 0.9, 1.0, 1.1, 0.9, so 5
- no: 1, 2 and 8 Jan, so 3
- good: 9 and 12 Jan, so 2
- maybe: 10 and 13 Jan, so 2
- unlikely: 11 Jan, so 1
- none: 31 − 13 = 18

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `./test`
Expected: the new tests FAIL with `L.moodFor is not a function` (and similar for the others).

- [ ] **Step 3: Implement inside the logic block, just above `// logic:end`**

```js
const MOOD = { yes: "tubable", good: "good", maybe: "possible", no: "dry", unlikely: "dry" };
const RAT_ALT = {
  tubable: "River rat floating happily in an inner tube with a drink",
  good: "River rat pumping up an inner tube",
  possible: "River rat squinting up at the sky",
  dry: "River rat sitting on dry rocks with a flat tube",
  sleep: "River rat asleep in a hammock",
};
const moodFor = kind => MOOD[kind] || "sleep";
const pct = p => Math.round(p * 100);

const heroVerdict = n => n.tubable ? "Send it!" : "Rat's waiting.";
const heroLine = n => `Dam's letting out <b>${fmt(n.outflow)}</b> million m³/day.`
  + (n.tubable ? ` That's about <b>${fmt(toRiver(n.outflow), 1)}</b> m³/s into the river.` : "")
  + ` Tubing starts at <b>${T.tube}</b>.`;
const ctaText = w => w ? `Next float: ${short(w.start)}–${short(w.end)} · ${pct(w.p_avg)}%` : "";

function dayVerdict(s, c) {
  if (!c) return { title: "No data.", line: "No reading or forecast for this date." };
  if (c.o) {
    const est = c.o.derived ? " (estimated from the change in storage)" : "";
    return c.kind === "yes"
      ? { title: "It was flowing!", line: `Release ${fmt(c.o.out)} M m³${est} · about ${fmt(toRiver(c.o.out), 1)} m³/s into the river.` }
      : { title: "Dry rocks.", line: `Release ${fmt(c.o.out)} M m³${est}. Tubing starts at ${T.tube}.` };
  }
  return { title: `${LABEL[c.kind]} · ${pct(c.f.p)}%`, line: `chance it's tubable${isWeekend(s) ? " on this weekend day" : ""}.` };
}

function monthStats(y, m) {
  const st = { yes: 0, no: 0, good: 0, maybe: 0, unlikely: 0, none: 0 };
  const n = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  for (let d = 1; d <= n; d++) { const c = classify(iso(y, m, d)); st[c ? c.kind : "none"]++; }
  return st;
}
// most common day kind, ties going to the more tubable one; "none" only when nothing else
const MOOD_ORDER = ["yes", "good", "maybe", "no", "unlikely"];
const monthMood = st => MOOD_ORDER.reduce((best, k) => st[k] > (best === "none" ? 0 : st[best]) ? k : best, "none");
const monthTag = st => [st.yes || st.no ? `${st.yes} tubable` : "", st.good ? `${st.good} good` : "", st.maybe ? `${st.maybe} maybe` : ""]
  .filter(Boolean).join(" · ") || (st.unlikely ? "unlikely" : "no data");

const stepMonth = (i, delta, n = 12) => Math.min(n - 1, Math.max(0, i + delta));
const isSwipe = (dx, dy) => Math.abs(dx) > 40 && Math.abs(dx) > 1.5 * Math.abs(dy);
const thaiDate = s => { const p = parse(s); return `${p.d} ${THAI_M[p.m]} ${p.y + 543}`; };

function readPref(store, key, dflt) { try { return store?.getItem(key) ?? dflt; } catch { return dflt; } }
function writePref(store, key, value) { try { store?.setItem(key, value); } catch { /* storage blocked: keep going */ } }
```

Then extend the exports line to:

```js
// exports: T, classify, observed, weekendDays, sameDayHistory, reliability, LABEL, parse, utc, iso, isWeekend, fmt, toRiver, short, longDate, moodFor, RAT_ALT, heroVerdict, heroLine, ctaText, dayVerdict, monthStats, monthMood, monthTag, stepMonth, isSwipe, thaiDate, readPref, writePref, pct
```

`THAI_M` and `MONTHS` must be defined inside the block. They already are if Task 1 wrapped from `const T` through `LABEL`; check that they come before `thaiDate`.

- [ ] **Step 4: Run the tests**

Run: `./test`
Expected: every `logic.test.mjs` test PASSES. Contrast still fails (expected).

- [ ] **Step 5: Commit**

```bash
git add app/template.html tests/logic.test.mjs
git commit -m "Add mood, copy, month-stat, swipe and pref logic for the redesign

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Pencil style guide and components

**Files:**
- Create: `design/river-rats.pen` (only through Pencil MCP tools; never Read or Write the `.pen` file directly)

**Interfaces:**
- Produces reusable Pencil components, named exactly: `Day / Tubable`, `Day / Too low`, `Day / Good`, `Day / Possible`, `Day / Unlikely`, `Day / No data`, `Ticket`, `Sticker Button`, `Fact Tile`, `Gauge`, `Card`. Tasks 5 and 6 instance these by name.

- [ ] **Step 1: Read the Pencil skill docs**

Call `mcp__pencil__read_skill()`, then `read_skill({path: "pen-schema.md"})`, `read_skill({path: "execute.md"})`, `read_skill({path: "guide/mobile-app.md"})` and `read_skill({path: "guide/components.md"})`. Then call `mcp__pencil__get_app_state` and open or create `/Users/jonathanhicks/dev/mae-gnat-river-rats/design/river-rats.pen`. Pass `filePath` on every `execute` call.

- [ ] **Step 2: Set variables**

One `execute` with `SetVariables`. Create colour variables for every token in Global Constraints (`paper`, `card`, `ink`, `ink-muted`, `river`, `river-ink`, `river-tint`, `river-faint`, `lagoon`, `sun`, `sand`, `tube`, `hibiscus`), plus `weekend` = `#FFE6AE` (the flat equivalent of 28% sun on paper). Create string variables `font-display` = `Shrikhand`, `font-head` = `Mitr`, `font-body` = `Sarabun`, `font-data` = `IBM Plex Mono`, and number variables `radius` = 16, `border` = 3.

- [ ] **Step 3: Build the "Style Guide" frame** (1280 wide, `placeholder: true` while building)

Top row: the 14 colour swatches, each labelled with name, hex and role (copy the roles from the spec's palette table). Second row: a type specimen with the real copy from the spec:
- "Send it!" — Shrikhand 52
- "Rat's waiting." — Shrikhand 44
- "MAE NGAT RIVER RATS" and "เขื่อนแม่งัดสมบูรณ์ชล" — Mitr 600 / 400
- "Dam's letting out 0.42 million m³/day." — Sarabun 16
- "1.24 M m³ · 64%" — IBM Plex Mono 14

- [ ] **Step 4: Build the components** (the "Components" frame sits above the screens)

Every card-like component has a 3px `$ink` stroke, radius 16, and an `$ink` drop shadow at offset 4,4 with blur 0.

| Component | Size | Look |
|---|---|---|
| `Day / Tubable` | 52×52, radius 10 | fill `$river`, ink stroke 2, number "6" Mitr 600 17 in `$card`. An 18×18 tube badge, absolutely positioned at the top-right (−7, −7); use a placeholder ring until Task 4 delivers the tube art |
| `Day / Too low` | 52×52 | no fill, `$sand` stroke 2, number in `$ink-muted` |
| `Day / Good` | 52×52 | fill `$river-tint`, dashed `$river` stroke 2. Number `$ink`, plus "74%" Mitr 600 11 in `$river-ink` on a second line |
| `Day / Possible` | 52×52 | fill `$river-faint`, dashed stroke `#9CCFC8`, "41%" in `$ink-muted` |
| `Day / Unlikely` | 52×52 | no fill, dashed `$sand` stroke, number and "12%" in `$ink-muted` |
| `Day / No data` | 52×52 | no fill, no stroke, number in `$sand` |
| `Ticket` | 280 wide | `$card` with a 6px left edge (`$river` for good; dashed for possible). Date range Mitr 600 22, starburst badge ("68%" ink on `$hibiscus`), small line "4 days · 2 weekend days · peak 80%" |
| `Sticker Button` | height 44 | pill, `$tube` fill, ink stroke 2, Mitr 500 15 in `$ink`; second variant `$card` fill |
| `Fact Tile` | 160 wide | `$card`, ink stroke 2, radius 12. Label (Mitr 500 11 caps, `$ink-muted`), value (Plex Mono 18) |
| `Gauge` | 340×64 | 20px-tall bar, radius 10: `$sand` up to 0.8 on a 0–2.5 scale, `$river` after. Ink tick at 0.8 labelled "tube line". Tube marker at the value. Scale labels 0, 0.5 … 2.5 |
| `Card` | — | `$card`, ink stroke 3, radius 16, shadow 4,4,0 `$ink`, padding 20, vertical layout, gap 12 |

Day cells "TODAY" and "Selected" are shown as instances in the style guide:
- TODAY: a small ink tab with "TODAY" (Mitr 600 9, `$card`) above the cell.
- Selected: a 3px ink ring with a 2px gap.

- [ ] **Step 5: Verify**

Run a layout-problems visitor:
`Get(styleGuideId, (n, c) => c.problems && Print(n.name, "|", c.parentCtx?.node.name, "|", c.problems))`.
Expected: no output. Then `TakeScreenshot([styleGuideId, componentsId])` and check:
- the six day states are distinguishable at a glance
- only `Day / Tubable` has a solid fill and a badge
- text is readable

Fix by updating nodes, never by deleting and redrawing. Then clear `placeholder`.

- [ ] **Step 6: Commit**

```bash
git add design/river-rats.pen
git commit -m "Pencil: River Rats style guide and components

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Rat art (Jonny picks the final set)

**Files:**
- Modify: `design/river-rats.pen` (an "Art" frame)
- Create: `app/img/rat-tubable.webp`, `rat-good.webp`, `rat-possible.webp`, `rat-dry.webp`, `rat-sleep.webp`, `tube.webp`

**Interfaces:**
- Produces: six files at those exact paths. Task 7 onwards references `img/rat-<mood>.webp` (moods from `moodFor`) and `img/tube.webp`.

- [ ] **Step 1: Read `generate.md`**

`mcp__pencil__read_skill({path: "generate.md"})`. Generation is async; check fills in a later `execute` and never re-generate pending work.

- [ ] **Step 2: Generate the character reference**

Insert an "Art" frame (`placeholder: true`) and a 768×768 frame "Rat Reference" inside it. Run `Generate("ai", refId, PROMPT_REF)` with:

> PROMPT_REF = "Character sheet of one cartoon river rat mascot, 1970s screen-print surf poster style, limited palette of teal #087A72, cream #FFF3DC, sunny yellow #FFC23D, orange #FF5E2B, pink #EC5585 and dark brown ink #2A1A10 outlines, visible halftone grain and slight print misregistration. The rat is a scrappy, friendly brown river rat with a big grin, round ears, a long pink tail, wearing small round sunglasses pushed up on its head and teal board shorts. Front view, three-quarter view and side view, full body, plain cream background, no text."

- [ ] **Step 3: Generate the five moods and the tube icon**

All six can run in the same `execute`. Each target is a 768×768 frame. Every prompt starts with the shared `STYLE` text, so the character stays the same:

> STYLE = "The same cartoon river rat mascot: scrappy friendly brown river rat, big grin, round ears, long pink tail, small round sunglasses, teal board shorts. 1970s screen-print surf poster style, limited palette teal #087A72, cream #FFF3DC, yellow #FFC23D, orange #FF5E2B, pink #EC5585, dark brown #2A1A10 ink outlines, halftone grain. Centered single character, plain flat cream background, no text. Scene: "

| Frame | Scene text appended to STYLE |
|---|---|
| `Rat Tubable` | "lying back in an orange inner tube floating down a fast teal river, holding a drink with a tiny umbrella, splashes, thrilled" |
| `Rat Good` | "standing on a riverbank pumping up an orange inner tube with a foot pump, excited, river glinting behind" |
| `Rat Possible` | "sitting on a half-inflated orange inner tube on the riverbank, shading its eyes with one paw, squinting hopefully at the sky" |
| `Rat Dry` | "sitting glumly on dry cracked river rocks next to a flat deflated orange inner tube, a trickle of water, sun beating down" |
| `Rat Sleep` | "asleep in a striped hammock between two palm trees, orange inner tube hanging from the tree, Z's floating up" |
| `Tube Icon` | "no rat, just a single orange inner tube icon seen from above, thick dark brown outline, simple bold sticker icon" |

- [ ] **Step 4: Wait, check consistency, remove backgrounds**

In a later `execute`, check each frame's fill URL is no longer `pencil:pending-image-…`. Then take `TakeScreenshot` of the Art frame and compare the rats:
- same face
- same shorts
- same sunglasses
- same tail

If one mood clearly drifts off-model, regenerate only that frame with the same prompt plus "matching the reference character exactly". If two or more drift, stop and report to Jonny: the fallback is treg image models that accept a reference image (Gemini Image or GPT Image edit), using the reference sheet as input.

When the set is consistent, replace each fill in one `execute` per image (the url must be applied in the same call):
`Update(id, {fill: {type: "image", url: Generate("remove-background", imageUrl(id))}})`.

- [ ] **Step 5: Jonny picks** (gate)

Screenshot the Art frame and show it to Jonny. Ask him to approve the set or name which moods to redo. Don't continue until he approves. Redo any rejected mood with Step 3's prompt and his notes.

- [ ] **Step 6: Export and compress**

```js
Export([tubableId, goodId, possibleId, dryId, sleepId, tubeId], "png", "/Users/jonathanhicks/dev/mae-gnat-river-rats/.cache/art", {scale: 1})
```

Then rename by node id and compress. Hero art is shown at up to 260px, so 2× is 520 wide; the tube is shown at up to 28px, so 2× is 64.

```bash
cd /Users/jonathanhicks/dev/mae-gnat-river-rats && mkdir -p app/img
# map each exported <nodeId>.png to its name (ids printed by the Export response)
for pair in "<tubableId>:rat-tubable" "<goodId>:rat-good" "<possibleId>:rat-possible" "<dryId>:rat-dry" "<sleepId>:rat-sleep"; do
  cwebp -quiet -q 80 -alpha_q 90 -resize 520 0 ".cache/art/${pair%%:*}.png" -o "app/img/${pair##*:}.webp"
done
cwebp -quiet -q 85 -resize 64 0 ".cache/art/<tubeId>.png" -o app/img/tube.webp
ls -l app/img
```

Expected: six files, each rat ≤ 100KB. If one is bigger, re-run that file with `-q 70`.

- [ ] **Step 7: Put the real tube art in the components**

In Pencil, set the `Day / Tubable` badge and the `Gauge` marker to an image fill using the Tube Icon frame's url (copy the fill). Screenshot the Components frame.

- [ ] **Step 8: Commit**

```bash
git add app/img design/river-rats.pen
git commit -m "Add River Rats mascot art (5 moods + tube badge)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Pencil phone frames (390 wide)

**Files:**
- Modify: `design/river-rats.pen`

**Interfaces:**
- Consumes: the components from Task 3 and the art frames from Task 4.
- Produces: six top-level frames, named exactly: `Phone / Top · Tubable`, `Phone / Top · Not tubable`, `Phone / Calendar`, `Phone / Sheet · Observed`, `Phone / Sheet · Forecast`, `Phone / Footer`.

Use realistic copy from the spec. For numbers, open `app/index.html` in Chrome and read `D.now`, `D.windows` and `D.month_odds` in the console. Build each frame with `placeholder: true`, `clip: true`, fill `$paper` and 16px side padding; verify it (Step 7) before starting the next.

- [ ] **Step 1: `Phone / Top · Tubable`**

From the top:
1. Header row: "MAE NGAT RIVER RATS" (Mitr 600 13, letter spacing 2), the Thai dam name in `$ink-muted`, and the "Latest 8 Oct" date on the right.
2. Hero `Card` on a sunburst: a radial ray pattern of `$sun` rays at 45% opacity behind the card, made as a rotated frame of thin rectangles or a gradient, not a hand-drawn path. Inside the card:
   - `Rat Tubable` image at 260 tall
   - "Send it!" in Shrikhand 52, `$tube`, with an ink text shadow 3,3
   - the `heroLine` text, for example "Dam's letting out **1.12** million m³/day. That's about **8.7** m³/s into the river. Tubing starts at **0.8**."
   - `Gauge` instance
   - footnote "Dam 64% full · Pacific: la nina (−0.6)"
3. "Next floats" (Shrikhand 28 `$river`) with a horizontal row of 3 `Ticket`s that overflows to the right (clipped by the frame, to show it scrolls).
4. "Tubing season" `Card` with 12 bars:
   - bars are fill frames in a horizontal layout, heights proportional to `month_odds`
   - ≥ 0.4 is `$river`, otherwise `$lagoon`
   - % labels above each bar and month initials below
   - the current month's initial is bold ink
   - caption underneath

- [ ] **Step 2: `Phone / Top · Not tubable`**

Copy frame 1 and change these descendants in the `Copy` call:
- art: `Rat Dry`
- verdict: "Rat's waiting."
- line: no river m³/s
- add a `Sticker Button`-styled ticket CTA under the gauge: "Next float: 14 Feb–22 Feb · 68%"

- [ ] **Step 3: `Phone / Calendar`**

1. "The Float Calendar" (Shrikhand 30 `$river`).
2. Toggles: `Sticker Button` "Next 12 months" (pressed: `$ink` fill, `$card` text) and "Pick a year ▾" (card variant).
3. A collapsed legend row: "What the colours mean ▾".
4. One month `Card`:
   - header `◀  February 2027  ▶`, where ◀ ▶ are 44×44 `Sticker Button`s and the title is Mitr 600 20
   - summary under the title: "11 tubable · 6 good · 3 maybe"
   - S M T W T F S header row; both S headers in `$ink`, the rest `$ink-muted`
   - 5 week rows of Day instances, mixing states realistically: tubable early in the month, forecasts after today, odds fading
   - a `$weekend` band behind the Saturday and Sunday columns (two tall frames behind the grid, absolute)
   - one cell with the TODAY tab, one Selected
5. Under the card: 12 month dots (12px circles, filled by each month's `monthMood` colour; the current one ringed in ink).
6. An expanded legend in a second copy of the frame, sitting to its right, named `Phone / Calendar · Legend open`.

- [ ] **Step 4: `Phone / Sheet · Observed`**

1. The calendar frame dimmed underneath: a copy with a 50% `$ink` overlay frame.
2. A bottom sheet `Card` 85% of the frame height (717 of 844), anchored to the bottom, top radius 24, with a 40×5 drag handle and an X `Sticker Button` (44×44) at the top right.
3. Contents:
   - "Saturday 6 February 2027" (Mitr 600 20)
   - "6 ก.พ. 2570" in `$ink-muted`
   - `Rat Tubable` at 160
   - "It was flowing!" (Shrikhand 30 `$river`)
   - line "Release 1.24 M m³ · about 10.1 m³/s into the river."
   - `Gauge`
   - 2×2 `Fact Tile`s: Dam release 1.24 M m³ / Into the river 10.1 m³/s / Dam fill 64% / Catchment rain 2.0 mm
   - closed "🤓 Nerd stats ▾" row

- [ ] **Step 5: `Phone / Sheet · Forecast`**

Same structure as Step 4, with these differences:
- date 13 Feb 2027
- `Rat Possible`
- "Possible · 48%" and "chance it's tubable on this weekend day."
- the gauge shows the median, with a `$river` band at 25% opacity up to q75
- two fact tiles: Likely release / High end (1 in 4)
- trust note: "128 days out. Days we called 'possible' this far ahead were tubable 41% of the time. This far ahead it mostly reflects the usual pattern for the date, so check back closer to the day."
- Nerd stats expanded:
  - "This date in past years" bars: 19 bars; tubable ones `$river`, others `$sand`; 2026 outlined in ink; dashed tube line
  - "Tubable in 9 of 19 years."
  - a table of 6 visible rows: Year / Release pill / Dam fill / Rain mm / Pacific

  The sheet scrolls, so make this frame taller (1400) to show the full contents.

- [ ] **Step 6: `Phone / Footer`**

1. "How this works ▾" expanded, using the current footer copy from `app/template.html` `renderFoot()`.
2. `Rat Sleep` at 120.
3. "Built 9 Oct 2026."
4. A second state with no windows, inside the same frame below a divider: the "Next floats" heading, `Rat Sleep`, and "Nothing on the horizon for 12 months."

- [ ] **Step 7: Verify each frame as it is finished**

1. Run the layout-problems visitor on the frame and expect no output.
2. `TakeScreenshot([frameId])`. Check:
   - no clipped text
   - 16px side gutters
   - all tap targets ≥ 44
   - only tubable cells are solid with a badge
3. Clear `placeholder`.

- [ ] **Step 8: Commit**

```bash
git add design/river-rats.pen
git commit -m "Pencil: River Rats phone frames

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Pencil desktop frame and design sign-off

**Files:**
- Modify: `design/river-rats.pen`

- [ ] **Step 1: `Desktop / Page` (1280 wide, 40px side padding)**

1. Header row.
2. Hero + side layout: hero `Card` 60% width on the left (rat 300 tall next to the verdict and line, gauge under both); on the right, 3 `Ticket`s stacked vertically, then the season card.
3. "The Float Calendar" header, toggles, legend row.
4. Body: a grid of 12 month cards (4 per row, 3 rows; each row is its own horizontal frame) on the left, and a sticky day panel `Card` (380 wide) on the right with the forecast-day content from `Phone / Sheet · Forecast` (nerd stats closed).
5. Footer.

Copy instances and frames from the phone frames where possible.

- [ ] **Step 2: Verify**

Run the layout-problems visitor and take a screenshot. Expected: no problems; the four month columns line up; the panel top aligns with the first month row.

- [ ] **Step 3: Jonny signs off on the design** (gate)

Screenshot all frames (Style Guide, Components, the six phone frames, Desktop) and send them to Jonny. Ask him to approve the design or say what to change. Apply any changes by updating nodes. Don't start Task 7 until he approves.

- [ ] **Step 4: Commit**

```bash
git add design/river-rats.pen
git commit -m "Pencil: River Rats desktop frame

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Template — tokens, base styles, header and hero

From here on, each task replaces part of the page. In-between states may look half-old and half-new; only the end of Task 11 has to be complete. Keep the console free of errors at the end of every task.

**Files:**
- Modify: `app/template.html` (head, `<style>`, markup, `renderAnswer` becomes `renderHero`)

**Interfaces:**
- Consumes: `heroVerdict`, `heroLine`, `ctaText`, `moodFor`, `RAT_ALT`, `fmt`, `longDate`, `short` (logic block).
- Produces:
  - `ratImg(mood: string, cls: string) -> string` (HTML `<img>`)
  - `gaugeSVG(value: number, high?: number) -> string` (restyled, same signature)
  - `openDay(s: string, from?: Element)`: the one entry point that selects a day. Declared here as a stub; Task 10 adds the sheet behaviour.

- [ ] **Step 1: Run the contrast test and confirm it fails**

Run: `./test`
Expected: `contrast.test.mjs` FAILS with "missing token --paper".

- [ ] **Step 2: Replace the head and the `:root`/base CSS**

Replace lines 1–45 (from the `<title>` to the focus-visible rule) and delete both dark-mode blocks:

```html
<title>Mae Ngat River Rats</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shrikhand&family=Mitr:wght@400;500;600&family=Sarabun:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Retro river-trip poster on cream paper. Phone first: answer (hero) → next floats → season → one-month
   calendar with a bottom sheet. ≥980px: hero beside floats, 12-month grid beside a sticky day panel. */
:root {
  --paper: #FFF3DC; --card: #FFFAF0; --ink: #2A1A10; --ink-muted: #6B5444;
  --river: #087A72; --river-ink: #06625B; --river-tint: #BFE6E0; --river-faint: #E4F3EF; --lagoon: #5CC8B8;
  --sun: #FFC23D; --sand: #EBDDC2; --tube: #FF5E2B; --hibiscus: #EC5585;
  --weekend: #FFE6AE;
  --f-display: "Shrikhand", "Mitr", Georgia, serif;
  --f-head: "Mitr", "Sarabun", system-ui, sans-serif;
  --f-body: "Sarabun", system-ui, -apple-system, "Segoe UI", sans-serif;
  --f-data: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --shadow: 4px 4px 0 var(--ink);
  color-scheme: light;
}
* { box-sizing: border-box; }
html { background: var(--paper); }
body { background: var(--paper); color: var(--ink); font: 16px/1.55 var(--f-body); margin: 0; padding-inline: 16px; padding-block: 18px 48px; }
body.locked { overflow: hidden; }
.wrap { max-width: 1240px; margin-inline: auto; display: grid; gap: 28px; }
h1, h2, h3 { margin: 0; text-wrap: balance; line-height: 1.1; }
h2.title { font: 400 clamp(1.7rem, 6vw, 2.2rem)/1.05 var(--f-display); color: var(--river); }
h3 { font: 600 0.8rem var(--f-head); text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-muted); }
p { margin: 0; max-width: 62ch; }
b { font-weight: 600; }
.num, .data { font-family: var(--f-data); font-variant-numeric: tabular-nums; }
.muted { color: var(--ink-muted); }
.card { background: var(--card); border: 3px solid var(--ink); border-radius: 16px; box-shadow: var(--shadow); padding: 18px; display: grid; gap: 12px; min-width: 0; }
button, select { font: inherit; color: inherit; }
:focus-visible { outline: 3px solid var(--ink); outline-offset: 2px; }
.btn { font: 500 0.95rem var(--f-head); min-height: 44px; padding: 8px 18px; border: 2px solid var(--ink); border-radius: 999px; background: var(--card); color: var(--ink); cursor: pointer; display: inline-flex; align-items: center; gap: 6px; text-decoration: none; }
.btn.go { background: var(--tube); }
.btn[aria-pressed="true"] { background: var(--ink); color: var(--card); }
@media (prefers-reduced-motion: no-preference) {
  .btn { transition: transform .12s; }
  .btn:hover, .btn:active { transform: rotate(-2deg) scale(1.03); }
}

/* header + hero */
.top { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 12px; }
.mark { font: 600 0.9rem var(--f-head); letter-spacing: 0.14em; }
.top .read { margin-left: auto; font-size: 0.85rem; color: var(--ink-muted); }
.lead { display: grid; gap: 22px; }
@media (min-width: 980px) { .lead { grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); align-items: start; } }
.hero { position: relative; overflow: hidden; justify-items: center; text-align: center; padding: 22px 18px 20px; }
.hero::before { content: ""; position: absolute; left: 50%; top: 150px; width: 900px; height: 900px; translate: -50% -50%; border-radius: 50%;
  background: repeating-conic-gradient(color-mix(in srgb, var(--sun) 45%, transparent) 0 7deg, transparent 7deg 14deg); z-index: 0; }
.hero > * { position: relative; z-index: 1; }
.rat { display: block; height: auto; max-width: 100%; }
.rat.big { width: min(260px, 70vw); }
.verdict { font: 400 clamp(2.6rem, 11vw, 3.3rem)/1 var(--f-display); color: var(--tube); text-shadow: 3px 3px 0 var(--ink); }
.verdict.dry { color: var(--river); }
.hero p { font-size: 1.05rem; }
.foot-note { font-size: 0.85rem; color: var(--ink-muted); }
.gauge { width: 100%; max-width: 440px; }
.gauge svg { width: 100%; height: auto; display: block; }
.gauge text { font: 11px var(--f-data); fill: var(--ink-muted); }
@media (min-width: 980px) { .hero { grid-template-columns: auto minmax(0, 1fr); text-align: left; justify-items: start; column-gap: 22px; } .hero .rat { grid-row: span 3; } .hero .gauge, .hero .foot-note, .hero .cta { grid-column: 1 / -1; } }
```

The old `.answer`, `.panel`, `.win`, `.controls`, `.legend` and `.sw` rules are deleted as later tasks replace their markup. Delete any that no longer match markup at the end of Task 11.

- [ ] **Step 3: Replace the hero markup**

Replace the `<section class="hero">…</section>` block (old lines 134–140) with:

```html
  <header class="top">
    <span class="mark">MAE NGAT RIVER RATS</span>
    <span class="muted">เขื่อนแม่งัดสมบูรณ์ชล</span>
    <span class="read" id="read"></span>
  </header>
  <div class="lead">
    <section class="hero card" id="hero" aria-live="polite"></section>
    <aside class="side">
      <section class="floats" aria-labelledby="floats-title"><h2 class="title" id="floats-title">Next floats</h2><div class="tickets" id="tickets"></div></section>
      <section class="season card" aria-labelledby="season-title"><h3 id="season-title">Tubing season</h3><div id="season"></div></section>
    </aside>
  </div>
```

In JS, change `renderWindows` to write to `#tickets` instead of `#wins` (Task 8 rewrites it fully; for now only the id changes). Change the `init` listener `document.getElementById("wins")` to `"tickets"`.

- [ ] **Step 4: Replace `gaugeSVG` and `renderAnswer` (below `// logic:end`)**

```js
const ratImg = (mood, cls = "") => `<img class="rat ${cls}" src="img/rat-${mood}.webp" alt="${RAT_ALT[mood]}" width="520" height="520" decoding="async">`;

function gaugeSVG(value, high) {
  const W = 420, H = 70, x0 = 14, x1 = W - 14, max = 2.5, y = 26;
  const x = v => x0 + Math.min(v, max) / max * (x1 - x0);
  let g = `<rect x="${x0}" y="${y}" width="${x1 - x0}" height="20" rx="10" fill="var(--sand)" stroke="var(--ink)" stroke-width="2"/>
    <rect x="${x(T.tube)}" y="${y}" width="${x1 - x(T.tube)}" height="20" rx="10" fill="var(--river)" stroke="var(--ink)" stroke-width="2"/>
    <line x1="${x(T.tube)}" x2="${x(T.tube)}" y1="${y - 8}" y2="${y + 28}" stroke="var(--ink)" stroke-width="3"/>
    <text x="${x(T.tube)}" y="${y - 12}" text-anchor="middle" style="fill:var(--ink);font-weight:500">tube line ${T.tube}</text>`;
  if (high != null && high > value) g += `<rect x="${x(value)}" y="${y + 6}" width="${x(high) - x(value)}" height="8" rx="4" fill="var(--card)" opacity=".7"/>`;
  g += `<image href="img/tube.webp" x="${x(value) - 16}" y="${y - 6}" width="32" height="32"/>`;
  [0, 0.5, 1, 1.5, 2, 2.5].forEach(t => g += `<text x="${x(t)}" y="${H - 2}" text-anchor="middle">${t}</text>`);
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Release ${fmt(value)} million cubic metres per day${high != null ? `, up to ${fmt(high)} on the high end` : ""}; tubable from ${T.tube}">${g}</svg>`;
}

let openDay = s => select(s);   // Task 10 replaces this with the sheet-aware version

function renderHero() {
  const n = D.now, w = D.windows[0];
  document.getElementById("read").textContent = `Latest ${short(latest)}`;
  const cta = !n.tubable && w ? `<button type="button" class="btn go cta" data-d="${w.start}">${ctaText(w)} →</button>` : "";
  const pacific = D.enso_now ? ` · Pacific: ${D.enso_now.phase.replace("_", " ")} (${D.enso_now.oni > 0 ? "+" : ""}${D.enso_now.oni.toFixed(1)})` : "";
  document.getElementById("hero").innerHTML = `
    ${ratImg(n.tubable ? "tubable" : "dry", "big")}
    <h1 class="verdict ${n.tubable ? "" : "dry"}">${heroVerdict(n)}</h1>
    <p>${heroLine(n)}</p>
    <div class="gauge">${gaugeSVG(n.outflow)}</div>
    <p class="foot-note">Dam ${fmt(n.pct, 0)}% full${pacific}</p>
    ${cta}`;
}
```

In `init`, replace `renderAnswer()` with `renderHero()` and add:

```js
document.getElementById("hero").addEventListener("click", ev => { const b = ev.target.closest(".cta"); if (b) { view = "next"; openDay(b.dataset.d, b); } });
```

- [ ] **Step 5: Run the tests**

Run: `./test`
Expected: all PASS, including `contrast.test.mjs`.

- [ ] **Step 6: Check in Chrome**

Run `./calendar`, then open DevTools device mode at 390×844.
Expected:
- cream page and wordmark header
- hero card with the correct mood rat, verdict, line and gauge with the tube marker
- the CTA appears only when not tubable
- no console errors

To check the other hero state, run in the console:
`D.now.tubable = !D.now.tubable; renderHero()`.
Expected: the rat, verdict and CTA all swap.

- [ ] **Step 7: Commit**

```bash
git add app/template.html
git commit -m "River Rats: palette, base styles, header and hero

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Template — next floats tickets and season strip

**Files:**
- Modify: `app/template.html` (CSS, `renderWindows` becomes `renderFloats`, `renderSeason`)

**Interfaces:**
- Consumes: `weekendDays`, `short`, `pct`, `ratImg`, `openDay`.
- Produces: `renderFloats()`, `renderSeason()`.

- [ ] **Step 1: Add the CSS** (after the hero CSS)

```css
/* next floats + season */
.side { display: grid; gap: 22px; align-content: start; min-width: 0; }
.floats { display: grid; gap: 12px; min-width: 0; }
.tickets { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(250px, 80%); gap: 14px; overflow-x: auto; padding: 4px 6px 10px 2px; scroll-snap-type: x mandatory; }
@media (min-width: 980px) { .tickets { grid-auto-flow: row; grid-auto-columns: auto; overflow: visible; } }
.ticket { scroll-snap-align: start; position: relative; text-align: left; display: grid; gap: 4px; padding: 14px 16px 14px 22px; min-height: 44px; cursor: pointer;
  background: var(--card); border: 3px solid var(--ink); border-radius: 14px; box-shadow: var(--shadow); }
.ticket::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 8px; border-radius: 11px 0 0 11px; background: var(--river); }
.ticket.possible::before { background: repeating-linear-gradient(180deg, var(--river) 0 6px, transparent 6px 10px); }
.ticket b { font: 600 1.3rem/1.15 var(--f-head); }
.ticket small { color: var(--ink-muted); font-size: 0.85rem; }
.ticket .odds { position: absolute; right: 10px; top: -12px; width: 58px; height: 58px; display: grid; place-items: center; font: 600 1rem var(--f-head); color: var(--ink);
  background: var(--hibiscus); border: 2px solid var(--ink); clip-path: polygon(50% 0, 61% 18%, 82% 10%, 80% 32%, 100% 40%, 85% 56%, 96% 77%, 74% 79%, 68% 100%, 50% 86%, 32% 100%, 26% 79%, 4% 77%, 15% 56%, 0 40%, 20% 32%, 18% 10%, 39% 18%); }
.empty { display: grid; justify-items: center; gap: 8px; text-align: center; }
.empty .rat { width: 140px; }
.season svg { width: 100%; height: auto; display: block; }
.season text { font: 11px var(--f-head); fill: var(--ink-muted); }
.note { font-size: 0.88rem; color: var(--ink-muted); margin: 0; }
```

- [ ] **Step 2: Replace `renderWindows` with `renderFloats`**

```js
function renderFloats() {
  const host = document.getElementById("tickets");
  const list = D.windows.slice(0, 5);
  if (!list.length) { host.innerHTML = `<div class="empty">${ratImg("sleep")}<p>Nothing on the horizon for 12 months.</p></div>`; return; }
  host.innerHTML = list.map(w => `<button type="button" class="ticket ${w.band === "good" ? "good" : "possible"}" data-d="${w.start}">
      <span class="odds">${pct(w.p_avg)}%</span>
      <b>${short(w.start)}${w.end !== w.start ? " – " + short(w.end) : ""}</b>
      <small>${w.band === "good" ? "Good odds" : "Possible"} · ${w.days} days · ${weekendDays(w.start, w.end)} weekend days · peak ${pct(w.p_max)}%</small>
    </button>`).join("");
}
```

In `init`: replace `renderWindows()` with `renderFloats()`, and change the tickets listener to:

```js
document.getElementById("tickets").addEventListener("click", ev => { const b = ev.target.closest(".ticket"); if (b) { view = "next"; openDay(b.dataset.d, b); } });
```

- [ ] **Step 3: Restyle `renderSeason`**

Replace the colour expressions inside the existing `renderSeason`:
- bar fill: `peak ? "var(--river)" : "var(--lagoon)"`, without the `opacity` attribute
- add `stroke="var(--ink)" stroke-width="1.5"` to each bar `rect`
- current-month label style: `style="fill:var(--ink);font-weight:600"`, replacing `var(--tube)`

Change the caption `<p class="note">` text to: `Peak: Feb–Apr, when the dam waters the dry-season rice. Bars show % of days tubable each month, 2006–${parse(latest).y}.`

- [ ] **Step 4: Check in Chrome**

Run `./calendar` at 390px. Expected:
- tickets scroll sideways with snap, each with a pink starburst
- tapping a ticket selects that day; the sheet updates (still the old sheet until Task 10)
- the season bars are teal/lagoon with ink outlines

Check the empty state in the console:
`D.windows = []; renderFloats(); renderHero()`.
Expected: the sleeping rat with the message, and no CTA. Reload afterwards. At 1280px the tickets stack vertically beside the hero.

- [ ] **Step 5: Run the tests**

Run: `./test`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/template.html
git commit -m "River Rats: next-float tickets and season strip

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Template — Float Calendar (cells, legend, phone pager, swipe, dots)

**Files:**
- Modify: `app/template.html` (controls/legend/work markup, calendar CSS, `renderMonths`, new `renderDots`, init listeners)

**Interfaces:**
- Consumes: `classify`, `monthStats`, `monthMood`, `monthTag`, `stepMonth`, `isSwipe`, `isWeekend`, `LABEL`, `pct`, `fmt`.
- Produces: the state `mi` (index of the month shown on phone, 0–11); `monthIndexOf(s) -> number` (index in `monthsToShow()`, or −1). The month dots are rendered inside `renderMonths()`.

- [ ] **Step 1: Replace the controls/legend/work markup** (old lines 142–159)

```html
  <section class="cal" aria-labelledby="cal-title">
    <div class="cal-head">
      <h2 class="title" id="cal-title">The Float Calendar</h2>
      <div class="views" role="group" aria-label="Calendar range">
        <button type="button" class="btn" id="v-next" aria-pressed="true">Next 12 months</button>
        <select class="btn" id="y-sel" aria-label="Pick a year"></select>
      </div>
    </div>
    <details class="legend" id="legend">
      <summary class="btn">What the colours mean</summary>
      <p><b>Solid = happened, dashed = forecast. More teal = more likely.</b></p>
      <div class="legend-cells">
        <span><i class="day yes">6</i>Tubable</span>
        <span><i class="day no">5</i>Too low</span>
        <span><i class="day good">11<em>74%</em></i>Good odds</span>
        <span><i class="day maybe">14<em>41%</em></i>Possible</span>
        <span><i class="day unlikely">16<em>12%</em></i>Unlikely</span>
        <span><i class="day none">19</i>No data</span>
      </div>
    </details>
    <div class="work">
      <div class="months" id="months" aria-label="Calendar"></div>
      <div class="backdrop" id="backdrop" hidden></div>
      <aside class="sheet" id="sheet" tabindex="-1" aria-labelledby="sheet-title"></aside>
    </div>
  </section>
```

- [ ] **Step 2: Add the calendar CSS**

```css
/* calendar */
.cal { display: grid; gap: 14px; }
.cal-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px 16px; }
.views { display: flex; flex-wrap: wrap; gap: 8px; }
.legend { display: grid; gap: 10px; }
.legend summary { justify-self: start; list-style: none; }
.legend summary::-webkit-details-marker { display: none; }
.legend summary::after { content: "▾"; }
.legend[open] summary::after { content: "▴"; }
.legend-cells { display: flex; flex-wrap: wrap; gap: 10px 18px; font-size: 0.88rem; }
.legend-cells span { display: inline-flex; align-items: center; gap: 8px; }
.work { display: grid; gap: 22px; align-items: start; }
@media (min-width: 980px) { .work { grid-template-columns: minmax(0, 1fr) 380px; } }
.months { display: grid; gap: 22px 18px; }
@media (min-width: 980px) { .months { grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); } }
.month { padding: 14px; gap: 8px; }
.mhead { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 8px; }
.mhead h2 { font: 600 1.15rem var(--f-head); text-align: center; }
.mhead small { display: block; font: 400 0.8rem var(--f-body); color: var(--ink-muted); }
.mstep { width: 44px; justify-content: center; padding: 0; }
.mstep:disabled { opacity: .35; cursor: default; }
@media (min-width: 980px) { .mstep { display: none; } .mhead { grid-template-columns: minmax(0, 1fr); } .mhead h2 { text-align: left; } }
.grid7 { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px 4px; padding: 6px 4px; border-radius: 10px;
  background: linear-gradient(to right, var(--weekend) 0 calc(100% / 7), transparent calc(100% / 7) calc(600% / 7), var(--weekend) calc(600% / 7)); }
.dow { font: 600 0.75rem var(--f-head); text-align: center; color: var(--ink-muted); }
.dow.we { color: var(--ink); }
.day { aspect-ratio: 1; width: 100%; max-width: 52px; justify-self: center; border-radius: 10px; border: 2px solid transparent; background: transparent; color: var(--ink);
  display: grid; place-content: center; justify-items: center; font: 500 1rem/1.05 var(--f-head); font-style: normal; position: relative; padding: 0; cursor: pointer; }
.day em { font: 600 0.62rem/1 var(--f-head); font-style: normal; }
.day.yes { background: var(--river); color: var(--card); border-color: var(--ink); font-weight: 600; }
.day.yes::before { content: ""; position: absolute; top: -7px; right: -7px; width: 18px; height: 18px; background: url(img/tube.webp) center / contain no-repeat; }
.day.no { border-color: var(--sand); color: var(--ink-muted); }
.day.good { background: var(--river-tint); border: 2px dashed var(--river); }
.day.good em { color: var(--river-ink); }
.day.maybe { background: var(--river-faint); border: 2px dashed #9CCFC8; }
.day.maybe em, .day.unlikely em { color: var(--ink-muted); }
.day.unlikely { border: 2px dashed var(--sand); color: var(--ink-muted); }
.day.none { color: var(--sand); cursor: default; }
.day.today::after { content: "TODAY"; position: absolute; top: -9px; left: 50%; translate: -50% 0; font: 600 0.52rem/1 var(--f-head); letter-spacing: 0.08em; background: var(--ink); color: var(--card); padding: 3px 4px; border-radius: 4px; }
.day.sel { outline: 3px solid var(--ink); outline-offset: 2px; }
@media (max-width: 979px) { .months .month:not(.on) { display: none; } }
.dots { display: flex; justify-content: center; gap: 4px; flex-wrap: wrap; }
.dot { width: 44px; height: 44px; border: 0; background: transparent; display: grid; place-items: center; cursor: pointer; padding: 0; }
.dot i { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--ink); background: var(--card); }
.dot.yes i { background: var(--river); } .dot.good i { background: var(--river-tint); } .dot.maybe i { background: var(--river-faint); }
.dot.no i, .dot.unlikely i { background: var(--sand); }
.dot[aria-current="true"] i { outline: 3px solid var(--ink); outline-offset: 2px; }
@media (min-width: 980px) { .dots { display: none; } }
@media (prefers-reduced-motion: no-preference) { .day:not(.none):hover { transform: scale(1.08); } .day { transition: transform .12s; } }
```

- [ ] **Step 3: Replace `renderMonths`; add `monthIndexOf` and `dayCell`**

```js
let mi = 0;   // phone: which of the 12 shown months is visible
const monthIndexOf = s => { const p = parse(s); return monthsToShow().findIndex(x => x.y === p.y && x.m === p.m); };

function dayCell(s, d) {
  const c = classify(s);
  if (!c) return `<button type="button" class="day none" disabled aria-label="${s}: no data">${d}</button>`;
  const label = c.o ? `${s}: ${LABEL[c.kind]}, release ${fmt(c.o.out)}` : `${s}: ${LABEL[c.kind]}, ${pct(c.f.p)}% chance tubable`;
  const odds = c.f ? `<em>${pct(c.f.p)}%</em>` : "";
  return `<button type="button" class="day ${c.kind} ${s === latest ? "today" : ""} ${s === selected ? "sel" : ""}" data-d="${s}" aria-label="${label}">${d}${odds}</button>`;
}

function renderMonths() {
  const list = monthsToShow();
  mi = stepMonth(mi, 0, list.length);
  document.getElementById("months").innerHTML = list.map(({ y, m }, k) => {
    const first = new Date(Date.UTC(y, m, 1)).getUTCDay();
    const n = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
    let cells = ["S","M","T","W","T","F","S"].map((x, i) => `<div class="dow ${i === 0 || i === 6 ? "we" : ""}" aria-hidden="true">${x}</div>`).join("");
    for (let i = 0; i < first; i++) cells += "<div></div>";
    for (let d = 1; d <= n; d++) cells += dayCell(iso(y, m, d), d);
    return `<div class="month card ${k === mi ? "on" : ""}" data-k="${k}">
      <div class="mhead">
        <button type="button" class="btn mstep" data-step="-1" aria-label="Previous month" ${k === 0 ? "disabled" : ""}>◀</button>
        <h2>${MONTHS[m]} ${y}<small>${monthTag(monthStats(y, m))}</small></h2>
        <button type="button" class="btn mstep" data-step="1" aria-label="Next month" ${k === list.length - 1 ? "disabled" : ""}>▶</button>
      </div>
      <div class="grid7">${cells}</div></div>`;
  }).join("") + `<nav class="dots" aria-label="Jump to month">${list.map(({ y, m }, k) =>
    `<button type="button" class="dot ${monthMood(monthStats(y, m))}" data-k="${k}" aria-label="${MONTHS[m]} ${y}" ${k === mi ? 'aria-current="true"' : ""}><i></i></button>`).join("")}</nav>`;
}
```

The dots live inside `#months`, so one render keeps them in sync with the visible month.

- [ ] **Step 4: Wire the pager, dots and swipe in `init`**

Replace the old `#months` click listener with:

```js
const months = document.getElementById("months");
months.addEventListener("click", ev => {
  const step = ev.target.closest(".mstep"), dot = ev.target.closest(".dot"), day = ev.target.closest(".day[data-d]");
  if (step) { mi = stepMonth(mi, +step.dataset.step); renderMonths(); months.querySelector(`.month.on .mstep[data-step="${step.dataset.step}"]`)?.focus(); }
  else if (dot) { mi = +dot.dataset.k; renderMonths(); }
  else if (day) openDay(day.dataset.d, day);
});
let t0 = null;
months.addEventListener("touchstart", ev => { const t = ev.touches[0]; t0 = { x: t.clientX, y: t.clientY }; }, { passive: true });
months.addEventListener("touchend", ev => {
  if (!t0) return;
  const t = ev.changedTouches[0], dx = t.clientX - t0.x, dy = t.clientY - t0.y; t0 = null;
  if (isSwipe(dx, dy)) { mi = stepMonth(mi, dx < 0 ? 1 : -1); renderMonths(); }
}, { passive: true });
```

Set `mi` in four places:
- `select(s)`: after `if (view === "year") year = parse(s).y;` add `const k = monthIndexOf(s); if (k >= 0) mi = k;`.
- The `y-sel` change handler: set `mi = 0;` before `render()`.
- The `v-next` click handler: set `mi = Math.max(0, monthIndexOf(latest));` before `render()`.
- `init`: set `mi = Math.max(0, monthIndexOf(latest));` before the first `render()`, so the phone opens on the current month.

Delete the old scroll-to-sheet line in `select` (Task 10 owns sheet opening).

- [ ] **Step 5: Check in Chrome**

At 390px:
- one month card is visible
- ◀ ▶ move between months and are disabled at the ends
- the dots jump, and the current dot is ringed
- in touch emulation, swiping left/right changes month and a vertical drag scrolls the page
- only tubable days are solid teal with the tube badge
- forecast days show their %
- the weekend columns have a yellow band
- TODAY tab on the latest date
- the legend opens and closes

At 1280px: the 12-month grid shows, with no ◀ ▶ and no dots.

Year view: pick 2016. Expected: all observed days (solid or outline), no %.

- [ ] **Step 6: Run the tests**

Run: `./test`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add app/template.html
git commit -m "River Rats: Float Calendar with phone month pager, swipe and dots

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Template — day sheet, nerd stats, desktop panel

**Files:**
- Modify: `app/template.html` (sheet CSS, `renderSheet`, `barsSVG` colours, new `openSheet`/`closeSheet`, real `openDay`, init listeners)

**Interfaces:**
- Consumes: `dayVerdict`, `moodFor`, `thaiDate`, `reliability`, `sameDayHistory`, `readPref`, `writePref`, `ratImg`, `gaugeSVG`.
- Produces: `openDay(s, from?)` (final version), `closeSheet()`.

- [ ] **Step 1: Add the sheet CSS**

```css
/* day sheet: bottom sheet on phones, sticky panel on desktop */
.sheet { background: var(--card); border: 3px solid var(--ink); display: grid; gap: 16px; align-content: start; min-width: 0; padding: 18px; }
.sheet .grab { display: none; }
@media (max-width: 979px) {
  .sheet { position: fixed; inset: auto 0 0 0; height: 85dvh; overflow-y: auto; overscroll-behavior: contain; z-index: 20; border-radius: 24px 24px 0 0; border-bottom: 0;
    padding: 10px 16px calc(24px + env(safe-area-inset-bottom, 0px)); translate: 0 105%; visibility: hidden; }
  .sheet.open { translate: 0 0; visibility: visible; }
  .sheet .grab { display: block; justify-self: center; width: 44px; height: 5px; border-radius: 3px; background: var(--sand); }
  .backdrop { position: fixed; inset: 0; background: color-mix(in srgb, var(--ink) 50%, transparent); z-index: 19; }
}
@media (max-width: 979px) and (prefers-reduced-motion: no-preference) { .sheet { transition: translate .25s ease, visibility .25s; } }
@media (min-width: 980px) { .sheet { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 12px); border-radius: 16px; box-shadow: var(--shadow); } .sheet .x { display: none; } .backdrop { display: none; } }
.sheet-top { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 10px; align-items: start; }
.sheet-top h2 { font: 600 1.2rem var(--f-head); }
.x { width: 44px; justify-content: center; padding: 0; font-size: 1.2rem; }
.day-verdict { display: grid; justify-items: center; text-align: center; gap: 6px; }
.day-verdict .rat { width: 160px; }
.day-verdict h3 { font: 400 1.9rem/1.05 var(--f-display); color: var(--river); text-transform: none; letter-spacing: 0; }
.day-verdict.dry h3, .day-verdict.sleep h3 { color: var(--ink-muted); }
.facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin: 0; }
.facts div { background: var(--card); border: 2px solid var(--ink); border-radius: 12px; padding: 8px 10px; display: grid; gap: 2px; min-width: 0; }
.facts dt { font: 500 0.7rem var(--f-head); text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-muted); }
.facts dd { margin: 0; font: 500 1.05rem var(--f-data); font-variant-numeric: tabular-nums; }
.nerd { border-top: 2px dashed var(--sand); padding-top: 10px; display: grid; gap: 12px; }
.nerd summary { font: 600 1rem var(--f-head); min-height: 44px; display: flex; align-items: center; cursor: pointer; }
.bars svg { width: 100%; height: auto; display: block; }
.bars text { fill: var(--ink-muted); font: 10px var(--f-data); }
.tablewrap { overflow-x: auto; max-height: 320px; overflow-y: auto; border-top: 2px solid var(--sand); }
table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
th, td { text-align: right; padding: 6px; border-bottom: 1px solid var(--sand); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { font: 600 0.75rem var(--f-head); color: var(--ink-muted); position: sticky; top: 0; background: var(--card); }
td { font-family: var(--f-data); font-variant-numeric: tabular-nums; }
tr.hl td { background: var(--weekend); }
.pill { display: inline-block; padding: 0 8px; border-radius: 999px; font: 600 0.75rem var(--f-data); border: 1.5px solid var(--ink); }
.pill.yes { background: var(--river); color: var(--card); }
.pill.no { background: var(--sand); color: var(--ink); }
```

- [ ] **Step 2: Restyle `barsSVG`**

In the existing `barsSVG`:
- tube line: `stroke="var(--ink)"` with `stroke-dasharray="5 4"`, label style `fill:var(--ink)`
- bar fill: `r.out >= T.tube ? "var(--river)" : "var(--sand)"`
- selected year: `stroke="var(--ink)" stroke-width="2.5"`
- other bars: `stroke="var(--ink-muted)" stroke-width="0.75"`

- [ ] **Step 3: Replace `renderSheet`**

```js
function renderSheet() {
  const s = selected, p = parse(s), c = classify(s), v = dayVerdict(s, c), mood = moodFor(c?.kind);
  const rows = sameDayHistory(s), yesYears = rows.filter(r => r.out >= T.tube).length;
  let detail = "";
  if (c && c.o) {
    const o = c.o;
    detail = `<div class="gauge">${gaugeSVG(o.out)}</div>
      <dl class="facts">
        <div><dt>Dam release</dt><dd>${fmt(o.out)} <span class="muted">M m³</span></dd></div>
        <div><dt>Into the river</dt><dd>${o.out > T.canal ? fmt(toRiver(o.out), 1) + ' <span class="muted">m³/s</span>' : "none"}</dd></div>
        <div><dt>Dam fill</dt><dd>${fmt(o.pct, 0)}%</dd></div>
        <div><dt>Catchment rain</dt><dd>${o.rain == null ? "–" : fmt(o.rain, 1) + " mm"}</dd></div>
      </dl>`;
  } else if (c) {
    detail = `<div class="gauge">${gaugeSVG(c.f.median, c.f.q75)}</div>
      <dl class="facts">
        <div><dt>Likely release</dt><dd>${fmt(c.f.median)} <span class="muted">M m³</span></dd></div>
        <div><dt>High end (1 in 4)</dt><dd>${fmt(c.f.q75)} <span class="muted">M m³</span></dd></div>
      </dl>
      <p class="note">${reliability(s, c)}</p>`;
  }
  const table = rows.slice().reverse().map(r => `<tr class="${r.y === p.y ? "hl" : ""}"><td>${r.y}</td><td><span class="pill ${r.out >= T.tube ? "yes" : "no"}">${fmt(r.out)}</span></td><td>${fmt(r.pct, 0)}%</td><td>${r.rain == null ? "–" : fmt(r.rain, 1)}</td><td>${r.enso ? r.enso[1].replace("_", " ") : "–"}</td></tr>`).join("");
  const nerdOpen = readPref(storage(), "nerd", "closed") === "open";
  document.getElementById("sheet").innerHTML = `
    <span class="grab" aria-hidden="true"></span>
    <div class="sheet-top"><div><h2 id="sheet-title">${longDate(s)}</h2><span class="muted">${thaiDate(s)}</span></div>
      <button type="button" class="btn x" id="sheet-x" aria-label="Close">✕</button></div>
    <div class="day-verdict ${mood}">${ratImg(mood)}<h3>${v.title}</h3><p>${v.line}</p></div>
    ${detail}
    <details class="nerd" id="nerd" ${nerdOpen ? "open" : ""}><summary>🤓 Nerd stats</summary>
      <div class="bars"><h3>This date in past years</h3>
        <p class="note">Tubable in <b>${yesYears} of ${rows.length}</b> years. Dashed line: the tube line (${T.tube} M m³/day).</p>
        ${barsSVG(rows, s)}</div>
      <div class="tablewrap"><table>
        <thead><tr><th>Year</th><th>Release</th><th>Dam fill</th><th>Rain mm</th><th>Pacific</th></tr></thead>
        <tbody>${table}</tbody></table></div>
    </details>`;
}
const storage = () => { try { return window.localStorage; } catch { return undefined; } };
```

- [ ] **Step 4: Open/close, focus trap, swipe-down, and the final `openDay`**

Replace the Task 7 stub `let openDay = s => select(s);` with:

```js
const isPhone = () => window.matchMedia("(max-width: 979px)").matches;
let lastFocus = null;

function openDay(s, from) {
  select(s);
  if (!isPhone()) return;
  const sheet = document.getElementById("sheet");
  lastFocus = from || document.activeElement;
  sheet.setAttribute("role", "dialog"); sheet.setAttribute("aria-modal", "true");
  sheet.classList.add("open"); document.getElementById("backdrop").hidden = false; document.body.classList.add("locked");
  sheet.scrollTop = 0; sheet.focus();
}
function closeSheet() {
  const sheet = document.getElementById("sheet");
  if (!sheet.classList.contains("open")) return;
  sheet.classList.remove("open"); sheet.removeAttribute("role"); sheet.removeAttribute("aria-modal");
  document.getElementById("backdrop").hidden = true; document.body.classList.remove("locked");
  // the calendar re-rendered, so find the cell again by date
  const cell = lastFocus?.dataset?.d && document.querySelector(`.day[data-d="${lastFocus.dataset.d}"]`);
  (cell || lastFocus)?.focus?.();
}
```

`select(s)` already calls `render()`, which re-renders the months and the sheet. Make sure it no longer scrolls (removed in Task 9).

Add to `init`:

```js
const sheet = document.getElementById("sheet");
document.getElementById("backdrop").addEventListener("click", closeSheet);
sheet.addEventListener("click", ev => { if (ev.target.closest("#sheet-x")) closeSheet(); });
sheet.addEventListener("toggle", ev => { if (ev.target.id === "nerd") writePref(storage(), "nerd", ev.target.open ? "open" : "closed"); }, true);
document.addEventListener("keydown", ev => {
  if (!sheet.classList.contains("open")) return;
  if (ev.key === "Escape") { closeSheet(); return; }
  if (ev.key !== "Tab") return;
  const f = [...sheet.querySelectorAll('button, summary, [href], select, [tabindex]:not([tabindex="-1"])')].filter(e => !e.disabled);
  if (!f.length) return;
  const first = f[0], last = f[f.length - 1];
  if (ev.shiftKey && (document.activeElement === first || document.activeElement === sheet)) { ev.preventDefault(); last.focus(); }
  else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
});
let s0 = null;
sheet.addEventListener("touchstart", ev => { s0 = sheet.scrollTop <= 0 ? ev.touches[0].clientY : null; }, { passive: true });
sheet.addEventListener("touchend", ev => { if (s0 != null && ev.changedTouches[0].clientY - s0 > 80) closeSheet(); s0 = null; }, { passive: true });
window.matchMedia("(max-width: 979px)").addEventListener("change", () => closeSheet());
```

The default `selected` stays as it is now (`D.windows[0].start`, or `D.forecast[0].date`). On phones the sheet starts closed; on desktop the panel shows that day.

- [ ] **Step 5: Check in Chrome**

At 390px, touch emulation:
1. Tap a tubable day. The sheet slides up over a dimmed backdrop, the page behind doesn't scroll, and the sheet shows the date, Thai date, tubable rat, "It was flowing!", gauge and 4 fact tiles.
2. Tab cycles inside the sheet only. Escape closes it and focus returns to that day cell.
3. Reopen. Swipe down from the top closes it. A backdrop tap closes it. ✕ closes it.
4. Tap a forecast day. The possible/good rat shows with "{Label} · {p}%", the gauge band and the trust note.
5. Open Nerd stats, reload, and open a day: it's still open. In the console, `localStorage.clear()` then reload: it's closed again.

At 1280px: a sticky right panel, no ✕, no backdrop; clicking days updates it.

Check the throwing-storage case: in the DevTools console, run
`Object.defineProperty(window, "localStorage", { get() { throw new Error("blocked"); } }); renderSheet();`.
Expected: no error, and the sheet renders with nerd stats closed.

- [ ] **Step 6: Run the tests**

Run: `./test`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add app/template.html
git commit -m "River Rats: bottom-sheet day detail with nerd stats

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Template — footer, cleanup, publish images

**Files:**
- Modify: `app/template.html` (footer, dead CSS), `publish`

- [ ] **Step 1: Footer**

Replace `<footer id="foot"></footer>` with `<footer class="foot" id="foot"></footer>`. Change `renderFoot` so it wraps the existing three paragraphs (copy unchanged):

```js
function renderFoot() {
  document.getElementById("foot").innerHTML = `
    <details class="card how"><summary class="btn">How this works</summary>
      <p>Tubable means the dam's total release (น้ำออกเขื่อน) is at least ${T.tube} million m³ a day. The irrigation canals take the first ~${T.canal}; the rest flows down the Mae Ngat.</p>
      <p>The forecast is a model trained on every day since 2006. It starts from how full the dam is and how much it is releasing now (${fmt(D.now.pct, 0)}% full, ${fmt(D.now.outflow)} M m³/day on ${short(latest)}). Current release drives the next few weeks; fullness drives the months after. Window odds show the stretch average. Rainfall and El Niño were tested and didn't improve it, so they're shown for context only.</p>
      <p>Data: Royal Irrigation Department daily reservoir reports, Open-Meteo catchment rainfall, NOAA Oceanic Niño Index.</p>
    </details>
    <div class="sign">${ratImg("sleep")}<span>Built ${longDate(D.generated)}.</span></div>`;
}
```

CSS:

```css
.foot { display: grid; gap: 16px; justify-items: center; }
.how { width: 100%; max-width: 78ch; font-size: 0.92rem; }
.how summary { justify-self: start; list-style: none; }
.how summary::-webkit-details-marker { display: none; }
.sign { display: grid; justify-items: center; gap: 4px; color: var(--ink-muted); font-size: 0.85rem; }
.sign .rat { width: 120px; }
```

- [ ] **Step 2: Remove dead CSS**

Delete every rule left over from the old page that no longer matches markup. Check the selectors `.answer`, `.panel`, `.wins`, `.win`, `.controls`, `.legend span`, `.sw`, `.enso`, `.verdict .tag`, `.facts dd`. Keep any whose element still exists; `.facts` is redefined in Task 10, so delete only the older duplicate. Confirm no `prefers-color-scheme` and no `data-theme` remain:

Run: `grep -n "prefers-color-scheme\|data-theme\|--bg\|--yes\|--good\|--maybe\|--no:" app/template.html`
Expected: no output.

- [ ] **Step 3: Publish copies the images**

In `publish`, after the line `cp app/index.html "$SITE/index.html"`, add:

```sh
rm -rf "$SITE/img" && cp -R app/img "$SITE/img"
```

- [ ] **Step 4: Run the tests and rebuild**

Run: `./test && ./calendar`
Expected: tests PASS; the page opens.

- [ ] **Step 5: Commit**

```bash
git add app/template.html publish
git commit -m "River Rats: footer, remove old styles, publish the art

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Full verification against the Pencil frames

**Files:** none, unless a check fails (fix in `app/template.html` and commit).

- [ ] **Step 1: Compare with Pencil**

At 390×844 (DevTools device mode), screenshot the page section by section and compare with the `Phone / …` frames. At 1280 wide, compare with `Desktop / Page`. List the differences that change meaning or legibility, and fix those. Leave pixel nits.

- [ ] **Step 2: State sweep** (in the console, reloading between groups)

```js
D.now.tubable = true; D.now.outflow = 1.24; renderHero();          // Send it! + tubable rat, no CTA
D.now.tubable = false; D.now.outflow = 0.42; renderHero();         // Rat's waiting. + dry rat + CTA
D.windows = []; renderFloats(); renderHero();                      // sleeping rat, no CTA
openDay(D.forecast[D.forecast.length - 1].date);                   // last forecast day renders
openDay("1999-12-31");                                             // No data. + sleeping rat, no throw
```

Then:
- pick year 2000 and open a day in January 2000
- pick 29 Feb 2024 and check that the past-years bars include 28 Feb in non-leap years

- [ ] **Step 3: Layout and access checks**

At 320, 390 and 768 wide, run `document.documentElement.scrollWidth <= innerWidth` in the console. Expected: `true` at each width.

Keyboard only: Tab from the top through the hero CTA, the tickets, the toggles, ◀ ▶, a day, the sheet and back. Every focused element shows a visible ink outline.

Lighthouse accessibility (DevTools → Lighthouse → Accessibility, mobile). Expected: no contrast or tap-target failures.

- [ ] **Step 4: Commit any fixes**

```bash
git add app/template.html
git commit -m "River Rats: fixes from verification pass

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 5: Hand off to Jonny**

Tell him how to review the page (`./calendar` in the worktree) and how to ship it. After he approves, merge `redesign/river-rats` into `main` (fast-forward or merge commit, his choice), remove the worktree, and have him run `./publish` once. Then check that https://jonnyvector.github.io/mae-ngat-tube-calendar/ loads the rat images: open DevTools → Network, and there should be no 404s on `img/`.
