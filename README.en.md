# VSUnityInstaller

> A desktop tool to install Visual Studio **with the "Game development with Unity" workload** — choose your **year / edition / install location**. Once installed, you can write C# scripts and set breakpoints directly in Unity.
>
> **English | [中文](README.md)**

![v1.0](https://img.shields.io/badge/release-v1.0.0-blue) ![Platform](https://img.shields.io/badge/platform-Windows-informational) ![License](https://img.shields.io/badge/license-MIT-green) [![GitHub Releases](https://img.shields.io/badge/download-Releases-orange)](https://github.com/ZhaoYuanxin66/VSUnityInstaller/releases)

---

## What it does

To use Visual Studio with Unity, you must select the **"Game development with Unity"** workload during install — otherwise there's no **VS Tools for Unity**, and you can't write scripts or debug with breakpoints in VS.

This tool wraps that whole process into a few clicks: pick a year → pick an edition → set the install location → click **Install**. It downloads Microsoft's official bootstrapper, runs a silent install, then runs three automated verification checks and reports the result.

## Preview

![VSUnityInstaller UI](assets/screenshot.png)

## Features

- 🎯 **Selectable year**: 2019 / 2022 / 2026 / **latest** — covers mainstream and evergreen releases
- 🎓 **Selectable edition**: Community (free) / Professional / Enterprise
- 📁 **Custom install path**: type it or use "Browse…"; defaults to `D:\tools\visualstudio2022` and remembers the last one used
- ✅ **Unity Hub toggle**: checked = install with recommended components (incl. Unity Hub); unchecked = core + lightweight components only, skipping Hub and the heavier Copilot component
- 🧪 **Auto-verification**: checks `devenv.exe`, `VS Tools for Unity`, and vswhere registration after install — output to the UI and to `install.log`
- 🔔 **Existing-install detection**: warns with a dialog if the target path already has Visual Studio

## Supported versions × bootstrapper channel

| UI option | Visual Studio | Bootstrapper URL | Notes |
| --- | --- | --- | --- |
| **2026** | VS 2026 (18.x) | `aka.ms/vs/18/Stable/vs_{edition}.exe` | Current mainstream, evergreen |
| **2022** | VS 2022 (17.x) | `aka.ms/vs/17/release/vs_{edition}.exe` | Previous generation (LTS-style) |
| **2019** | VS 2019 (16.x) | `aka.ms/vs/16/release/vs_{edition}.exe` | Legacy projects |
| **latest** | Always-current stable | `aka.ms/vs/stable/vs_{edition}.exe` | Follows Microsoft's evergreen model |

Where `{edition}` = `community` / `professional` / `enterprise`. All versions use the Unity workload `Microsoft.VisualStudio.Workload.ManagedGame`.

## Quick start

1. Download `VSUnityInstaller.exe` from [Releases](https://github.com/ZhaoYuanxin66/VSUnityInstaller/releases) (single file, no installer, Windows includes the runtime)
2. Double-click to run (if a SmartScreen prompt appears, click **More info → Run anyway**)
3. Choose year & edition, enter or browse an install path, toggle Unity Hub as desired
4. Click **Install** → if a UAC prompt appears, click **Yes** → silent install runs
5. Automatic verification reports the result when done

> ⚠️ Administrator rights are required; the UAC prompt is spawned by the installer itself.

### Configure Unity afterwards

In the Unity Editor: `Edit → Preferences → External Tools`, set **External Script Editor** to Visual Studio. You can then write C# scripts and set breakpoints in VS.

## Install & verification flow

1. Download the official bootstrapper (`vs_community.exe` etc.) into a temp dir
2. Invoke it: `--installPath <path> --add Microsoft.VisualStudio.Workload.ManagedGame --quiet --norestart --wait`; appends `--includeRecommended` when Unity Hub is checked
3. Post-install checks:
   - `devenv.exe` present in `Common7\IDE\`
   - `Visual Studio Tools for Unity` extension under `Common7\IDE\Extensions\Microsoft\`
   - vswhere registers the product and its install path

Results are printed to the UI and written to `install.log` next to the exe.

## Source structure & development

```
├── main.py          # Tkinter GUI entry
├── installer.py     # Core: version map / download / argument building / silent install / verification
├── build.sh         # One-click build script
├── assets/          # README screenshot
└── dist/            # Build output (VSUnityInstaller.exe)
```

| File | Responsibility |
| --- | --- |
| `main.py` | UI, interaction, progress & result output |
| `installer.py` | Version×edition→URL map, download, `build_install_args()`, `verify_install()` |
| `build.sh` | PyInstaller packaging |

### Rebuild

```bash
pip install pyinstaller          # first time only
bash build.sh                    # or:
# python -m PyInstaller --onefile --windowed --name VSUnityInstaller main.py
```

Output is a single `dist/VSUnityInstaller.exe` (~12 MB).

### Adding a new version

Just add one line `("year", "edition") -> "URL"` in `installer.py`'s `_BOOTSTRAP_URL` and add the year to the `YEARS` list — no UI or packaging changes needed.

## FAQ

**Q: "Not a tty / can't launch winget"?** — This tool does **not** use winget. It calls the official bootstrapper directly (a native exe that runs reliably in background/automation), sidestepping winget's silent-exit issue in non-interactive shells.

**Q: No script editor in Unity after install?** — In Unity's `Edit → Preferences → External Tools`, set the script editor to Visual Studio; `VS Tools for Unity` connects automatically once the workload is present.

**Q: Target path already has VS installed?** — The tool detects it and asks you whether to continue (useful for adding the Unity workload to an existing install).

## License

[MIT](LICENSE) © ZhaoYuanxin66