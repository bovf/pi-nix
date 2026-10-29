// Synthetic static provider regression. Never executes the generated ELF.
// Run only in the Nix sandbox or private filesystem/network namespaces.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
const [pkg, binutils] = process.argv.slice(2);
const run = (...args) => JSON.parse(execFileSync(`${pkg}/bin/rea`, [...args, "--json"], { encoding: "utf8", timeout: 120_000 }));
writeFileSync("synthetic.s", ".global _start\n_start:\n mov $60, %rax\n xor %rdi, %rdi\n syscall\n");
execFileSync(`${binutils}/bin/as`, ["synthetic.s", "-o", "synthetic.o"]);
execFileSync(`${binutils}/bin/ld`, ["synthetic.o", "-o", "synthetic-elf"]);
const target = `${process.cwd()}/synthetic-elf`;
const digest = () => createHash("sha256").update(readFileSync(target)).digest("hex");
const before = digest();
for (const [name, args, pattern] of [
  ["objdump", ["inspect-with-objdump", target, "file_headers"], /elf64-x86-64/],
  ["rizin", ["execute-rizin-command", target, "iI"], /ELF64/],
]) {
  const result = run(...args);
  assert.equal(result.raw_result.exit_code, 0);
  assert.equal(result.raw_result.stderr, "");
  assert.equal(result.raw_result.artifact_changed, false);
  assert.equal(result.subject.digest.sha256, before);
  assert.match(result.raw_result.stdout, pattern);
  writeFileSync(`rea-${name}.json`, JSON.stringify(result, null, 2));
}
const ghidra = run("analyze", target, "--provider", "ghidra");
assert.equal(ghidra.subject.format, "elf");
assert.equal(ghidra.subject.digest.sha256, before);
const provider = ghidra.analysis_profile.parameters.upstream_analysis_profile.provider;
assert.equal(provider.id, "ghidra");
assert.equal(provider.version, "12.1.4");
assert.equal(ghidra.normalized_result.procedure_count, 1);
assert.ok(ghidra.normalized_result.segments.some(segment => segment.name === ".text"));
assert.equal(digest(), before, "static providers changed the synthetic artifact");
writeFileSync("rea-ghidra.json", JSON.stringify(ghidra, null, 2));
console.log(`PASS: synthetic ELF ${before}; Ghidra ${provider.version}, Rizin, objdump static inspection; target never executed`);
