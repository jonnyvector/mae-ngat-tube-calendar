# Mae Ngat River Rats — UI/UX redesign

Date: 2026-10-09 · Status: approved in brainstorming, awaiting spec review

## Goal

Make the tube calendar fun and easier to read. Same answers as today (is it tubable, when is the next chance, what happened on a date), presented as a bright 70s river-trip poster with a river rat mascot whose mood matches the day.

**Audience:** Jonny and friends planning trips. English. Inside-joke tone is fine.
**Device:** phone first (link shared in a group chat); desktop is a wider layout of the same page.
**Success:** a friend opening the link on a phone knows within 3 seconds whether to go today and when the next good window is, without reading numbers; the full data is still one tap away.

## Constraints

- Page stays a single static `app/template.html` (plain HTML/CSS/JS, no framework), built by `scripts/build_app.py`.
- The data contract does not change: `const D = /*__DATA__*/null;` marker and every `D` field (`latest`, `generated`, `now`, `enso_now`, `thresholds`, `month_odds`, `windows`, `forecast`, `history`, `backtest`). `build_app.py` is untouched.
- Every current feature survives; detail moves behind collapsible sections, nothing is cut.
- Light theme only. The current dark-mode CSS is removed.
- No CI. All verification is local.
- Work happens on branch `redesign/river-rats` in the worktree `../mae-gnat-river-rats`, so the launchd publish job (which commits data in the main checkout) is never affected.

## 1. Visual system

**Mood:** 70s river-trip screen print on warm cream paper. Thick ink outlines, hard offset shadows (no blur), subtle paper grain, sunburst rays behind the hero.

**Palette (CSS tokens on `:root`):**

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#FFF3DC` | page background |
| `--card` | `#FFFAF0` | cards, sheet |
| `--ink` | `#2A1A10` | text, outlines, shadows |
| `--ink-muted` | `#6B5444` | secondary text (must pass AA on `--paper`) |
| `--river` | `#0B8A80` | Tubable (the only solid day fill); cream text on top |
| `--river-tint` | `#BFE6E0` | Good-odds forecast day |
| `--river-faint` | `#E4F3EF` | Possible forecast day |
| `--lagoon` | `#5CC8B8` | accent (season strip, stickers); never a day state |
| `--sun` | `#FFC23D` | sunburst; weekend column band at 28% |
| `--sand` | `#EBDDC2` | outline for too-low / unlikely days |
| `--tube` | `#FF5E2B` | buttons and calls to action only; never marks a day |
| `--hibiscus` | `#E8457A` | sparing accent: odds badges, stickers |

`--ink-muted` is a starting value; adjust during implementation until it measures ≥ 4.5:1 on `--paper` and `--card`.

**Calendar reads yes-or-no first:** only tubable days get a solid fill (`--river`) and the tube badge. Solid edge = happened, dashed edge = forecast; more teal = more likely. Forecast cells print their odds. This replaces today's dashed borders and stripes. (Revised 2026-10-09 after review: the first version's lagoon/sun/sand + halftone states were hard to tell apart.)

**Type (Google Fonts):**
- Shrikhand: the big verdict and section titles only.
- Mitr: headings, buttons, day numbers, wordmark (covers Thai and Latin).
- Sarabun: body text (kept).
- IBM Plex Mono: tabular numbers inside nerd stats only.

**Shapes:** cards have a 3px `--ink` border, 16px radius and a `4px 4px 0 var(--ink)` shadow. Buttons and pills are sticker-style and tilt slightly on hover/press (only under `prefers-reduced-motion: no-preference`). Minimum tap target 44px.

## 2. Top of page

**Header bar:** wordmark "MAE NGAT RIVER RATS" (Mitr), muted Thai dam name `เขื่อนแม่งัดสมบูรณ์ชล`, latest-reading date right-aligned.

**Hero poster card** (full width, sunburst background):
- Mood rat image, about 260px tall on phone, chosen from today's verdict (`D.now.tubable`).
- Verdict in Shrikhand, 44–52px: "Send it!" when tubable, "Rat's waiting." when not.
- One plain sentence: "Dam's letting out **{outflow}** million m³/day. Tubing starts at **{T.tube}**." When tubable, append the m³/s into the river (existing `toRiver`).
- Chunky river-level gauge: sand below `T.tube`, teal above, a tube icon as the marker, the `T.tube` tick labelled "tube line". Scale 0–2.5 as today.
- Small footnote row: dam fill %, Pacific ENSO phase and ONI.
- When not tubable and a window exists: a ticket-style CTA "Next float: {start}–{end} · {p_avg}%". Tapping it opens that day (see section 4).

**"Next floats":** up to 5 entries from `D.windows`, as horizontally scrolling ticket stubs on phone. Each stub shows:
- the date range, big, in Mitr
- `p_avg` in a hibiscus starburst badge
- "{days} days · {weekend days} weekend days · peak {p_max}%"
- a teal edge: solid `--river` for good, dashed for possible

Tapping a stub switches to the next-12-months view, shows that month, and opens the day. With no windows: the sleeping rat and "Nothing on the horizon for 12 months."

**"Tubing season" strip:** 12 rounded bars from `D.month_odds` (% of days tubable since 2006). Months with odds ≥ 40% are `--river`; the rest are `--lagoon`. The current month's label is bold ink. Caption: "Peak: Feb–Apr, when the dam waters the dry-season rice."

**Desktop (≥ 980px):** the hero takes about 60% of the width on the left; the ticket stubs stack vertically on the right with the season strip below.

## 3. Calendar ("The Float Calendar")

**Header:** title in Shrikhand. Two sticker toggles: "Next 12 months" and "Pick a year ▾" (select, 2000 through the last forecast year). Same view state as today (`view`, `year`).

**Phone (< 980px):** one month visible at a time.
- The month card title shows "February 2027" with a summary ("11 tubable · 6 good · 3 maybe").
- ◀ ▶ buttons sit beside the title. Horizontal swipe on the card moves one month; vertical scroll must keep working.
- A row of 12 month dots underneath, each tinted by that month's dominant state; tap a dot to jump.
- Day cells are about 52px with day numbers in Mitr.

**Desktop (≥ 980px):** all 12 months shown as a grid of cards (3–4 per row), as today.

**Day cell states:**

| State | Look |
|---|---|
| Tubable (observed) | solid `--river`, cream bold number, ink border, tube badge on the top-right corner. Nothing else gets the badge |
| Too low (observed) | no fill, faded number, thin solid `--sand` outline |
| Good odds (forecast, p ≥ `T.good`) | `--river-tint` fill, dashed `--river` edge, odds printed under the number ("74%") |
| Possible (forecast, p ≥ `T.possible`) | `--river-faint` fill, soft dashed teal edge, odds printed in muted ink |
| Unlikely (forecast) | no fill, faded number, dashed `--sand` edge, odds printed faint |
| No data | faint number only, disabled |
| Weekend | pale `--sun` band (28%) behind the Saturday and Sunday columns; S headers in full ink |
| Today | small ink "TODAY" tab on top of the cell |
| Selected | 3px `--ink` outline with 2px offset |

Every cell keeps its current `aria-label` text ("2027-02-14: Good odds, 72% chance tubable").

**Legend:** a collapsible "What the colours mean" row of sample cells, with the one-line rule "Solid = happened, dashed = forecast. More teal = more likely."

## 4. Day detail

**Phone:** tapping a day opens a bottom sheet (about 85% of the viewport height) with a drag handle. It closes on swipe down, the X button, a backdrop tap or Escape. Focus is trapped while it is open and returns to the tapped cell on close. The page behind does not scroll while it is open.

**Desktop:** the same content in a sticky right-hand panel. No backdrop; it always shows the selected day. The default selection is the first window's start, or the first forecast day, as today.

**Contents, top to bottom:**
1. Long date in Mitr, with the Thai date (`{d} {THAI_M} {y+543}`) muted underneath.
2. Mood rat (about 160px) and a verdict line in Shrikhand:
   - Tubable (observed): "It was flowing!", plus the release and m³/s into the river.
   - Too low (observed): "Dry rocks.", plus the release.
   - Forecast: "{Label} · {p}%" with "chance it's tubable" (and "on a weekend day" when relevant).
   - If the release was estimated from the change in storage (`derived`), say so.
3. Gauge: for observed days, the actual release; for forecast days, the median, with a faint band up to `q75`.
4. Quick facts as 2×2 sticker tiles:
   - Observed: release, into river, dam fill, rain.
   - Forecast: likely release, high end (1 in 4).
5. Trust note, forecast days only. It uses the existing `reliability()` wording, rewritten plainly: "{lead} days out. Days we called '{label}' this far ahead were tubable {r}% of the time." Beyond 45 days, append the "check back closer to the day" sentence.
6. "🤓 Nerd stats" (`<details>`, closed by default) containing:
   - "This date in past years" bar chart (tube line dashed, selected year outlined in ink)
   - "Tubable in {n} of {total} years"
   - the year table: year, release pill, dam fill, rain, ENSO
   - the selected year is outlined in ink

   The open/closed state is stored in `localStorage` (inside try/catch; the page works without it).

## 5. Footer

A `<details>` "How this works" holds the current footer text (tube-line definition, canal share, model description, data sources). Below it: a small sleeping rat and "Built {D.generated}."

## Mascot art

**Style:** retro screen-print river rat in an inner tube, limited palette matching section 1, grain texture, transparent background.

| File (`app/img/`) | Used for | Scene |
|---|---|---|
| `rat-tubable.webp` | tubable verdict, tubable day | stoked rat floating in a tube with a drink |
| `rat-good.webp` | good-odds day | rat pumping up the tube |
| `rat-possible.webp` | possible day | rat squinting at the sky |
| `rat-dry.webp` | not tubable, too-low or unlikely day | rat on dry rocks with a deflated tube |
| `rat-sleep.webp` | no windows, no data, footer | rat asleep in a hammock |
| `tube.svg` or `.webp` | calendar badge, gauge marker | small inner-tube icon |

**Process:**
1. Generate one character reference sheet first.
2. Generate each mood from that reference so the rat stays consistent.
3. Jonny picks the final set.
4. Export at 2× display size, WebP, target ≤ 100KB each.

Every `<img>` has alt text describing the mood ("River rat floating happily in a tube").

## Design file

`design/river-rats.pen` (committed) contains:
- **Style guide:** palette, type, card/button/sticker components, every day-cell state.
- **Phone frames (390px):**
  - top of page, tubable
  - top of page, not tubable, with the CTA
  - calendar month
  - day sheet, observed
  - day sheet, forecast, with nerd stats open
  - footer
- **Desktop frame (1280px):** the full page.

The frames use realistic numbers taken from the current data. The Pencil frames are the visual reference for implementation.

## Implementation scope

- **`app/template.html`:**
  - rewrite the markup and CSS
  - keep the logic: `parse/utc/iso/idx`, `observed`, `classify`, `LABEL`, `weekendDays`, `sameDayHistory`, `reliability`, `toRiver`, and the gauge and bars maths (restyled)
  - add: month pager with swipe, bottom sheet with focus trap, `<details>` accordions, a mood→image mapping function
- **`app/img/`:** the new art files.
- **`publish`:** add `cp -R app/img "$SITE/"` before the gh-pages commit; it only copies `index.html` today.
- **`calendar`:** no change. `app/index.html` opens from `app/`, so relative `img/` paths resolve locally and on Pages.
- **Unchanged:** `build_app.py` and all data scripts.

## Verification (local)

1. `./calendar` builds and opens the page.
2. Chrome at 390px and 1280px: no horizontal scroll at 390px, and every section matches its Pencil frame.
3. Check every verdict and day state by overriding `D.now` / picking dates in the console. Today's data shows only one hero state.
4. Keyboard: the sheet opens with Enter on a day, Escape closes it, and focus returns to the cell. Swipe the month pager and the sheet on a touch emulator.
5. Text contrast is AA on paper and card for all text tokens.
6. After merging, run `./publish` once by hand and confirm the images load on https://jonnyvector.github.io/mae-ngat-tube-calendar/.

## Out of scope

Dark mode, Thai-language UI, model or threshold changes, new data fields, multi-page routing.
