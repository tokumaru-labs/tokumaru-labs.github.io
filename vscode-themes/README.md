# Tokumaru Labs VS Code Themes

## Tokumaru Daylight

**A quiet summer afternoon for your editor.**

Soft blue-gray backgrounds, ocean-teal details and lavender tones bring a little summer light to your workspace. Muted gold and rose accents give code a clear, calm rhythm.

![Tokumaru Daylight: rendered theme preview with blue-gray surroundings and readable TypeScript syntax.](https://tokumaru-labs.github.io/vscode-themes/images/daylight-hero.png)

Daylight is one of three color themes in Tokumaru Labs VS Code Themes, alongside Midnight and Radar Green.

*The images on this page are rendered previews of the theme definitions, rather than native VS Code screenshots. Syntax colors can vary with the language, semantic highlighting and installed extensions.*

## Three worlds, one extension

| Theme | Character | Editor background | Primary accent |
|---|---|---|---|
| Tokumaru Daylight | Soft summer sky, ocean teal, lavender clouds and small gold and rose accents | `#E8EDF5` | Sky blue `#3F72A7` |
| Tokumaru Midnight | Ink-blue night, dusty pink neon, cyan windows and warm amber lights | `#141B2E` | Cyan `#75CBD7` / pink `#D796BA` |
| Tokumaru Radar Green | A near-black hacker terminal with layered phosphor greens and quiet amber signals | `#08120E` | Phosphor green `#8CCF9C` |

### Daylight / summer afternoon

![Tokumaru Daylight syntax preview.](https://tokumaru-labs.github.io/vscode-themes/images/daylight.png)

### Midnight / Citypop night

![Tokumaru Midnight syntax preview.](https://tokumaru-labs.github.io/vscode-themes/images/midnight.png)

### Radar Green / hacker terminal

![Tokumaru Radar Green syntax preview.](https://tokumaru-labs.github.io/vscode-themes/images/radar-green.png)

Code colors stay subdued while search matches, focus indicators and diagnostics remain easy to identify. The Midnight theme grew from [Tokumaru Midnight Cockpit for Chrome](https://tokumaru-labs.github.io/midnight-cockpit/).

## Install

1. Open **Extensions** in VS Code (`Ctrl+Shift+X`, or `Cmd+Shift+X` on macOS).
2. Search for **Tokumaru Labs VS Code Themes**, published by **Tokumaru Labs**, and select **Install**.
3. Open **Preferences: Color Theme** (`Ctrl+K Ctrl+T`, or `Cmd+K Cmd+T` on macOS) and choose a Tokumaru theme.

You can also install from the command line:

```sh
code --install-extension tokumarulabs.tokumaru-vscode-themes
```

For a downloaded `.vsix` file, use **Extensions → ... → Install from VSIX...**, or `code --install-extension <filename>.vsix`. Direct VSIX installs do not automatically update by default.

## Design principles

- **Midnight / Citypop night:** dusty pink keywords and active-tab accents sit against an ink-blue city night. Cyan and cool-blue functions add the feel of neon windows, with warm amber strings, search matches and warnings.
- **Daylight / dreamy afternoon:** gray-lavender clouds soften the background. Sky-blue keywords, ocean-teal parameters, violet types and small sun-gold and rose accents suggest a quiet summer afternoon. Letterforms stay sharp and readable.
- **Radar Green / hacker terminal:** layered mint and phosphor-green code rests on a near-black green background. Types stay in the green family, while pale yellow-green strings and quiet amber numbers keep their own roles.
- Readable contrast comes before decorative effects. These themes change colors without animations, blur or simulated CRT effects. The illustrations on the product page are mockups, not screenshots.

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

## License and support

MIT © 2026 Tokumaru Labs. [Issues and feedback](https://github.com/tokumaru-labs/tokumaru-labs.github.io/issues).
