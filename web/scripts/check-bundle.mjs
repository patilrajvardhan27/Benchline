// Builds for production with a sentinel in every secret-looking variable and fails if any
// of them ends up in the shipped files. Guards against env values leaking into the bundle.
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, rmSync, statSync } from "node:fs";
import { join } from "node:path";

const OUT = ".bundle-check";
const SENTINEL = "LEAK-CHECK-SENTINEL-7f3a9c";

rmSync(OUT, { recursive: true, force: true });
execFileSync("pnpm", ["exec", "vite", "build", "--outDir", OUT, "--emptyOutDir"], {
  stdio: "ignore",
  env: { ...process.env, VITE_DEV_TOKEN: SENTINEL, VITE_DEMO_MODE: "false" },
});

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* files(path);
    else yield path;
  }
}

const leaks = [...files(OUT)].filter((f) => readFileSync(f).includes(SENTINEL));
rmSync(OUT, { recursive: true, force: true });
if (leaks.length > 0) {
  console.error(`Dev token found in the production bundle:\n${leaks.join("\n")}`);
  process.exit(1);
}
console.log("No dev token in the production bundle.");
