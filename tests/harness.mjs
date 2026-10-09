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
