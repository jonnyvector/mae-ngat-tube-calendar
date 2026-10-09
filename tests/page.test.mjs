import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const SRC = fs.readFileSync(new URL("../app/template.html", import.meta.url), "utf8");

test("page is a standards-mode document that phones lay out at device width", () => {
  assert.match(SRC, /^<!doctype html>/i, "missing <!doctype html> (quirks mode)");
  assert.match(SRC, /<meta name="viewport" content="width=device-width, initial-scale=1[^"]*">/, "missing viewport meta: phones render the desktop layout");
});
