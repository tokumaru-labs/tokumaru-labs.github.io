# Tokumaru Labs VS Code Themes

Three focused color themes in a single VS Code extension, inspired by [Tokumaru Midnight Cockpit for Chrome](https://tokumaru-labs.github.io/midnight-cockpit/).

| Theme | Color feel | Editor background | Accent |
|---|---|---|---|
| Tokumaru Midnight | Deep navy cockpit | `#101A27` | `#68CDE6` |
| Tokumaru Daylight | Clear, soft daylight | `#F8FAFD` | `#106B9A` |
| Tokumaru Radar Green | Quiet green radar room | `#0A1914` | `#86D9A3` |

Preview all three and obtain the VSIX from the [Tokumaru Labs product page](https://tokumaru-labs.github.io/vscode-themes/).

## Install

1. Download `tokumaru-vscode-themes-0.1.0.vsix`.
2. In VS Code: **Extensions → ... → Install from VSIX...**.
3. Open **Preferences: Color Theme** (`Ctrl+K Ctrl+T`, or `Cmd+K Cmd+T` on macOS) and select a Tokumaru theme.

Or use `code --install-extension tokumaru-vscode-themes-0.1.0.vsix`. VSIX installs do not automatically update by default.

## Features & privacy

- Workbench, sidebar, tabs, status bar, editor, terminal, and syntax highlighting, including semantic tokens.
- Dark Midnight / light Daylight / dark Radar Green.
- No runtime code, permissions, network access, analytics, telemetry, forced font changes, or account required.

## Develop

Open the `vscode-themes` directory as an Extension Development Host (F5). For checking and packaging, run `npm run validate` and `npm run package` (Node.js is only required for development; uses official `@vscode/vsce`).

**Marketplace:** The package uses the provisional publisher ID `tokumarulabs`; its availability has not been verified. Currently distributed directly as a VSIX, not claimed to be published to Marketplace.

**License:** MIT © 2026 Tokumaru Labs. [Feedback](https://github.com/tokumaru-labs/tokumaru-labs.github.io/issues).
