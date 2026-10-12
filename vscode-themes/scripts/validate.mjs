import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const root = new URL("../", import.meta.url);
const read = path => readFileSync(new URL(path, root), "utf8");
const pkg = JSON.parse(read("package.json"));
assert.equal(pkg.version, "0.2.1");
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
  for (const rule of theme.tokenColors) {
    const color = rule.settings?.foreground;
    if (!color) continue;
    assert.match(color, hex);
    const ratio = contrast(theme.colors["editor.background"], color);
    assert.ok(ratio >= 4.5, `${entry.label} TextMate ${rule.name} has low contrast: ${ratio.toFixed(2)}`);
  }
  for (const [selector, style] of Object.entries(theme.semanticTokenColors)) {
    const color = typeof style === "string" ? style : style.foreground;
    if (!color) continue;
    assert.match(color, hex);
    const ratio = contrast(theme.colors["editor.background"], color);
    assert.ok(ratio >= 4.5, `${entry.label} semantic ${selector} has low contrast: ${ratio.toFixed(2)}`);
  }
  for (const [foreground, background] of [
    ["titleBar.activeForeground", "titleBar.activeBackground"],
    ["tab.activeForeground", "tab.activeBackground"],
    ["sideBar.foreground", "sideBar.background"],
    ["statusBar.foreground", "statusBar.background"],
  ]) {
    assert.ok(contrast(theme.colors[foreground], theme.colors[background]) >= 4.5,
      `${entry.label} workbench contrast is too low: ${foreground}/${background}`);
  }
  themes[entry.label] = theme;
}

assert.equal(themes["Tokumaru Midnight"].colors["editor.background"], "#141B2E");
assert.equal(themes["Tokumaru Radar Green"].colors["editor.background"], "#08120E");
assert.equal(themes["Tokumaru Daylight"].colors["editor.background"], "#E8EDF5");
assert.equal(themes["Tokumaru Daylight"].colors["tab.activeBorderTop"], "#3F72A7");
for (const [name, theme] of Object.entries(themes)) {
  const c = theme.colors;
  assert.ok(c["editor.findMatchBackground"], `${name} is missing search match colors`);
  assert.ok(c["editor.findMatchHighlightBackground"]);
  assert.equal(c["editorFindMatch.background"], undefined);
  assert.equal(c["editorFindMatchHighlightBackground"], undefined);
}
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
console.log("Validated 3 approved palettes, all TextMate/semantic contrast, workbench contrast, search keys, and focus colors.");
