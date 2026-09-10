import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, chmodSync } from "node:fs";
import os from "node:os"; import path from "node:path";
const temp=mkdtempSync(path.join(os.tmpdir(),"rfig-npm-")); const fake=path.join(temp,"fake");
writeFileSync(fake,"#!/bin/sh\necho forwarded:$*\nexit 7\n"); chmodSync(fake,0o755);
const result=spawnSync("node",["bin/rfig.mjs","doctor"],{cwd:new URL("..",import.meta.url),env:{...process.env,RFIG_TEST_BINARY:fake},encoding:"utf8"});
assert.equal(result.status,7); assert.match(result.stdout,/forwarded:doctor/); console.log("PASS npm wrapper forwarding");
