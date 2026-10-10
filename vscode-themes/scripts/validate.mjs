import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const root = new URL("../", import.meta.url);
const read = path => readFileSync(new URL(path, root), "utf8");
const pkg = JSON.parse(read("package.json"));
assert.equal(pkg.version, "0.2.0");
assert.equal(pkg.contributes.themes.length, 3);
assert.equal(pkg.main, undefined);
assert.equal(pkg.browser, undefined);
assert.equal(pkg.activationEvents, undefined);

const hex = /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/;
const linear = v => {
  const c = v / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};
const luminance = hexColor => {
  const h = hexColor.slice(1, 7);
  const c = [0, 2, 4].map(p => linear(Number.parseInt(h.slice(p, p + 2), 16)));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const contrast = (a, b) => {
  const la = luminance(a), lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
};

const themes = {};
for (const entry of pkg.contributes.themes) {
  const theme = JSON.parse(read(entry.path));
  assert.equal(theme.name, entry.label);
  assert.equal(theme.type, entry.uiTheme === "vs" ? "light" : "dark");
  assert.equal(theme.semanticHighlighting, true);
  assert.ok(Object.keys(theme.colors).length >= 140);
  assert.ok(theme.tokenColors.length >= 15);
  assert.ok(Object.keys(theme.semanticTokenColors).length >= 15);
  for (const [key, value] of Object.entries(theme.colors)) {
    assert.match(value, hex, `Invalid UI color ${entry.label}: ${key}`);
  }
  assert.ok(contrast(theme.colors["editor.background"], theme.colors["editor.foreground"]) >= 7);
  for (const category of ["Comments", "Keywords", "Strings", "Numbers", "Functions", "Types"]) {
    const rule = theme.tokenColors.find(x => x.name === category);
    assert.ok(rule, `Missing token rule ${category}`);
    assert.match(rule.settings.foreground, hex);
    const ratio = contrast(theme.colors["editor.background"], rule.settings.foreground);
    assert.ok(ratio >= 4.5, `${entry.label} ${category} has low contrast: ${ratio.toFixed(2)}`);
  }
  themes[entry.label] = theme;
}

assert.equal(themes["Tokumaru Midnight"].colors["editor.background"], "#101A27");
assert.equal(themes["Tokumaru Radar Green"].colors["editor.background"], "#0A1914");
assert.equal(themes["Tokumaru Daylight"].colors["editor.background"], "#F8FAFD");
assert.equal(themes["Tokumaru Daylight"].colors["tab.activeBorderTop"], "#106B9A");
for (const name of ["Tokumaru Midnight", "Tokumaru Radar Green"]) {
  const c = themes[name].colors;
  assert.ok(c["editor.findMatchBackground"]);
  assert.ok(c["editor.findMatchHighlightBackground"]);
  assert.equal(c["editorFindMatch.background"], undefined);
  assert.equal(c["editorFindMatchHighlightBackground"], undefined);
  assert.ok(c["statusBarItem.warningBackground"]);
  assert.ok(c["terminal.findMatchBackground"]);
}
assert.notEqual(
  themes["Tokumaru Midnight"].tokenColors.find(x => x.name === "Functions").settings.foreground,
  themes["Tokumaru Radar Green"].tokenColors.find(x => x.name === "Functions").settings.foreground,
);
assert.ok(existsSync(new URL(pkg.icon, root)));
console.log("Validated 3 themes, preserved Daylight, syntax contrast, and cockpit/radar focus colors.");
