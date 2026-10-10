import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
const root = new URL("../", import.meta.url);
const read = path => readFileSync(new URL(path, root), "utf8");
const pkg = JSON.parse(read("package.json"));
assert.equal(pkg.contributes.themes.length,3);
assert.equal(pkg.main,undefined);
assert.equal(pkg.activationEvents,undefined);
for(const x of pkg.contributes.themes){const t=JSON.parse(read(x.path));assert.equal(t.name,x.label);assert.equal(t.type,x.uiTheme==="vs"?"light":"dark");assert.equal(t.semanticHighlighting,true);assert.ok(Object.keys(t.colors).length>=100);assert.ok(t.tokenColors.length>=15);assert.ok(Object.keys(t.semanticTokenColors).length>=15);for(const [k,v] of Object.entries(t.colors))assert.match(v,/^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/,`Bad ${x.label}: ${k}`)}
if(pkg.icon)assert.ok(existsSync(new URL(pkg.icon,root)));
console.log("3 VS Code themes validated.");
