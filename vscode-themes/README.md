# Tokumaru Labs VS Code Themes

Three focused, readable VS Code color themes in a single extension, inspired by [Tokumaru Midnight Cockpit for Chrome](https://tokumaru-labs.github.io/midnight-cockpit/).

| Theme | Character | Editor background | Primary accent |
|---|---|---|---|
| Tokumaru Midnight | Modern cockpit: cool instruments, cyan controls, amber search and warnings | `#101A27` | `#68CDE6` |
| Tokumaru Daylight | Soft, clear daytime desk | `#F8FAFD` | `#106B9A` |
| Tokumaru Radar Green | Vintage radar station: quiet phosphor-green focus, amber detection and alerts | `#0A1914` | `#86D9A3` |

**v0.2.0 release candidate** (not yet publicly deployed): Midnight and Radar Green now have different focus treatments, search-match colors, status indicators and syntax hierarchies. **Daylight's color-theme JSON is unchanged from v0.1.0.**

## Install

For the **currently published v0.1.0**, download the signed-off VSIX from the [official Tokumaru Labs page](https://tokumaru-labs.github.io/vscode-themes/). After approval, that page will be updated with the new v0.2.0 VSIX.

1. Download the `.vsix` file.
2. In VS Code, go to **Extensions → ... → Install from VSIX...**.
3. Open **Preferences: Color Theme** (`Ctrl+K Ctrl+T`, or `Cmd+K Cmd+T` on macOS) and choose a Tokumaru theme.

CLI installation is also supported: `code --install-extension <filename>.vsix`. Direct VSIX installs do not automatically update by default.

## Design principles

- **Midnight / navigation:** a clean cyan active indicator and cool-blue function colors indicate what is controllable and in focus; amber is reserved for search hits, warnings and significant signals.
- **Radar Green / observation:** dark green surroundings stay calm, a pale phosphor-green indicates the current cursor, tab and live focus; muted greens recede and amber emphasizes detections and warnings.
- **Daylight / daylight readability:** deliberately unchanged in this release.
- Contrast comes before decorative effects. These are **color themes**, not animations or simulated CRT effects. The illustrations on the product page are mockups, not screenshots.

## Features & privacy

- Editor, tabs, sidebar, status bar, terminal and workbench colors.
- TextMate syntax and semantic highlighting, plus search-match, diff, diagnostic and terminal colors.
- No runtime scripts, permissions, forced fonts, telemetry, analytics, accounts or network requests.

## Build and validate

Run from this directory:

```sh
npm run validate
npm run package
```

Requires Node.js for development and the official `@vscode/vsce` packager. No runtime dependencies are needed for users. For a local test, open this folder in VS Code and press `F5` to launch the Extension Development Host.

## Distribution and Marketplace

The `publisher` field is provisionally `tokumarulabs` and **must be checked** against the actual Marketplace publisher ID before publishing. The official site currently distributes v0.1.0 directly; the v0.2.0 Marketplace listing has **not** been created.

Publisher creation and first upload require the owner's Microsoft account. Do not put Personal Access Tokens or credentials into this repository, CI logs, issues or chat. Use the official [VS Code publishing guide](https://code.visualstudio.com/api/working-with-extensions/publishing-extension).

## License and support

MIT © 2026 Tokumaru Labs. [Issues and feedback](https://github.com/tokumaru-labs/tokumaru-labs.github.io/issues).
