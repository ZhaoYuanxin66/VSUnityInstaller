---
name: vsunity-installer
description: 一键安装 Visual Studio(Unity 工作负载)，可自选年份/版别/安装位置。Use when 需要装 VS 或给已有 VS 补装 Unity 工具链。
---

# VSUnityInstaller

让「装 VS + Unity 工作负载」变成点几下的事。源码在 `E:\workgroup\skills\VSUnityInstaller`，打包成品为单个 exe。

## 触发场景
- 用户要在 Windows 上装 Visual Studio 用于 Unity/C# 开发
- 已有 VS，想补装「使用 Unity 的游戏开发」工作负载
- 需要自定义安装位置（默认 `D:\tools\visualstudio2022`）

## 使用
1. 双击 `dist/VSUnityInstaller.exe`
2. 选年份（2022/2019）× 版别（Community/Professional/Enterprise）
3. 填/浏览安装位置
4. 勾「同时安装 Unity Hub」(可选)
5. 点「开始安装」→ UAC 点「是」→ 静默安装 → 自动核验输出 + `install.log`

## 技术要点（已验证的关键坑）
- **不要用 winget 在后台装**：winget 的 UWP 壳在非 tty/后台环境静默 exit 1 且无输出。改用官方引导程序 `vs_community.exe`（原生 exe，后台可跑，自动弹 UAC），本工具即基于此。
- 引导程序 URL 映射（`installer.py`）：年 2022→`aka.ms/vs/17/release`、2019→`aka.ms/vs/16/release`，版别接 `vs_community/professional/enterprise.exe`。
- Unity 工作负载 ID：`Microsoft.VisualStudio.Workload.ManagedGame`；核心组件 `Microsoft.VisualStudio.Component.Unity`（VS Tools for Unity）。
- 装后核验（`verify_install`）：`devenv.exe` 在 `Common7\IDE\`、`Visual Studio Tools for Unity` 扩展在 `Common7\IDE\Extensions\Microsoft\`，再用 vswhere（`C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe`）确认注册。
- **GUI 必须 `app.mainloop()`**：构造 `tk.Tk` 后没进 mainloop，程序会"窗闪一下即 exit 0"，务必在 main() 里调 `mainloop()`。

## 重新打包
```
cd E:\workgroup\skills\VSUnityInstaller
bash build.sh            # 或手动: python -m PyInstaller --onefile --windowed --name VSUnityInstaller main.py
# 产物: dist\VSUnityInstaller.exe (~12MB)
```

## 核验清单
- `dist/VSUnityInstaller.exe` 打开后有窗口、标题正常
- 用 `verify_install(D:\tools\visualstudio2022)` 对已装 VS 跑，三项全通过