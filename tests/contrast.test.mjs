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
