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
