#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";
const require = createRequire(import.meta.url);
if (process.env.RFIG_TEST_BINARY) {
  const result = spawnSync(process.env.RFIG_TEST_BINARY, process.argv.slice(2), {stdio:"inherit"});
  process.exit(result.status ?? 5);
}
const key = `${process.platform}-${process.arch}`;
const packages = {"linux-x64":"@yhyb24p/research-figure-linux-x64"};
if (!packages[key]) { console.error(`RF1001 Unsupported platform: ${key}`); process.exit(5); }
let info;
try { info = require.resolve(`${packages[key]}/package.json`); } catch { console.error(`RF1002 Platform launcher is missing: ${packages[key]}`); process.exit(5); }
const binary = path.join(path.dirname(info), "bin", process.platform === "win32" ? "rfig.exe" : "rfig");
const result = spawnSync(binary, process.argv.slice(2), {stdio:"inherit", windowsHide:false});
if (result.error) { console.error(`RF1003 Failed to start launcher: ${result.error.message}`); process.exit(5); }
process.exit(result.status ?? 5);
