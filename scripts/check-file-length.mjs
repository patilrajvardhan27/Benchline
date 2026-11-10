// Fails when a source file is longer than MAX_LINES, so files stay small and focused.
// Generated code, lockfiles, data snapshots and dependencies are skipped.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const MAX_LINES = 250;
const ROOT = new URL("..", import.meta.url).pathname;
const SOURCE = /\.(java|kts|ts|tsx|js|mjs|py|sql|ya?ml|css|tf|tpl|json)$/;
const SKIP_DIR = new Set([
  "node_modules", "build", "dist", "target", ".git", ".gradle", ".venv", "__pycache__",
  ".pytest_cache", ".mypy_cache", ".ruff_cache", "generated", "data", "demo",
  "test-results", "playwright-report", "coverage",
]);
const SKIP_FILE = /(^|\/)(pnpm-lock\.yaml|uv\.lock|package-lock\.json)$/;

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      if (!SKIP_DIR.has(name)) yield* walk(path);
    } else if (SOURCE.test(name) && !SKIP_FILE.test(path)) {
      yield path;
    }
  }
}

const tooLong = [];
for (const file of walk(ROOT)) {
  const lines = readFileSync(file, "utf8").split("\n").length;
  if (lines > MAX_LINES) tooLong.push(`${relative(ROOT, file)} has ${lines} lines, limit is ${MAX_LINES}`);
}

if (tooLong.length > 0) {
  console.error(tooLong.join("\n"));
  process.exit(1);
}
console.log(`All source files are within ${MAX_LINES} lines.`);
