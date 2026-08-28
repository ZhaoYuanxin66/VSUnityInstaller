# -*- coding: utf-8 -*-
"""VSUnityInstaller - 核心逻辑：VS 引导程序下载、静默安装、装后核验。

仅依赖标准库，便于 PyInstaller 打包为单个 exe。
"""
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request

# ---- 版本 × 版别 -> 官方引导程序下载 URL 映射 ----
# VS2026 → /18/Stable（常青），VS2022 → /17/release，VS2019 → /16/release，
# latest → /stable（始终跟随最新稳定版）
_BOOTSTRAP_URL = {
    ("2026", "Community"):    "https://aka.ms/vs/18/Stable/vs_community.exe",
    ("2026", "Professional"): "https://aka.ms/vs/18/Stable/vs_professional.exe",
    ("2026", "Enterprise"):   "https://aka.ms/vs/18/Stable/vs_enterprise.exe",
    ("2022", "Community"):    "https://aka.ms/vs/17/release/vs_community.exe",
    ("2022", "Professional"): "https://aka.ms/vs/17/release/vs_professional.exe",
    ("2022", "Enterprise"):   "https://aka.ms/vs/17/release/vs_enterprise.exe",
    ("2019", "Community"):    "https://aka.ms/vs/16/release/vs_community.exe",
    ("2019", "Professional"): "https://aka.ms/vs/16/release/vs_professional.exe",
    ("2019", "Enterprise"):   "https://aka.ms/vs/16/release/vs_enterprise.exe",
    ("latest", "Community"):    "https://aka.ms/vs/stable/vs_community.exe",
    ("latest", "Professional"): "https://aka.ms/vs/stable/vs_professional.exe",
    ("latest", "Enterprise"):   "https://aka.ms/vs/stable/vs_enterprise.exe",
}

WORKLOAD = "Microsoft.VisualStudio.Workload.ManagedGame"  # 使用 Unity 的游戏开发
# 不装 Unity Hub / Copilot 时，显式加的核心 + 轻量推荐组件
_UNITY_CORE_COMPONENTS = [
    "Microsoft.VisualStudio.Workload.ManagedGame",
    "Microsoft.VisualStudio.Component.Unity",        # Visual Studio Tools for Unity
    "Microsoft.VisualStudio.Component.HLSL",          # HLSL 工具（shader）
    "Microsoft.VisualStudio.Component.IntelliCode",   # IntelliCode
]

# (值, 界面显示名)；'latest' 表示始终跟随最新稳定版
YEARS = [("2026", "2026"), ("2022", "2022"), ("2019", "2019"),
         ("latest", "最新(latest)")]
EDITIONS = ["Community", "Professional", "Enterprise"]


def bootstrap_url(version: str, edition: str):
    key = (version, edition)
    if key not in _BOOTSTRAP_URL:
        raise ValueError(f"不支持的组合: {version} / {edition}")
    return _BOOTSTRAP_URL[key]


def download_bootstrapper(version: str, edition: str, dest_dir: str,
                          progress_cb=None) -> str:
    """下载官方引导程序到 dest_dir，返回本地路径。"""
    url = bootstrap_url(version, edition)
    name = f"vs_bootstrapper_{version}_{edition.lower()}.exe"
    path = os.path.join(dest_dir, name)

    def _hook(blocks, block_size, total):
        if progress_cb and total > 0:
            done = blocks * block_size
            progress_cb(done * 100.0 / total, done, total)

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(path, "wb") as f:
        content_length = int(resp.headers.get("Content-Length") or 0)
        _total = content_length
        read = 0
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
            read += len(chunk)
            if progress_cb and _total:
                progress_cb(read * 100.0 / _total, read, _total)
    return path


def build_install_args(install_path: str, hub: bool):
    """组装引导程序命令行参数（核心：Unity 工作负载 + 自定义路径）。"""
    args = [
        "--installPath", f'"{install_path}"',
        "--add", WORKLOAD,
        "--quiet",
        "--norestart",
        "--wait",
    ]
    if hub:
        # 默认：连同推荐组件（含 Unity Hub）
        args.append("--includeRecommended")
    else:
        # 不装 Unity Hub：显式点选核心 + 轻量组件
        for comp in _UNITY_CORE_COMPONENTS[1:]:
            args.extend(["--add", comp])
    return args


def _find_vswhere():
    cands = [
        r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe",
        r"C:\Program Files\Microsoft Visual Studio\Installer\vswhere.exe",
    ]
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def query_installed(querypath=None):
    """用 vswhere 列出已注册的 VS 产品；可选按安装路径过滤。"""
    vswhere = _find_vswhere()
    if not vswhere:
        return []
    cmd = [vswhere, "-all", "-products", "*", "-format", "json"]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=90).stdout
    except Exception:
        return []
    try:
        import json
        data = json.loads(out.decode("utf-8", "replace"))
    except Exception:
        return []
    if querypath is None:
        return data
    target = os.path.normcase(os.path.normpath(querypath))
    return [p for p in data
            if os.path.normcase(os.path.normpath(
               p.get("installationPath", ""))) == target]


def verify_install(install_path: str):
    """装后核验：返回 (ok, results) 结果字典。"""
    results = {}
    ide = os.path.join(install_path, "Common7", "IDE")
    devenv = os.path.join(ide, "devenv.exe")
    results["devenv"] = os.path.isfile(devenv)

    unity_dirs = [
        os.path.join(ide, "Extensions", "Microsoft", "Visual Studio Tools for Unity"),
        os.path.join(ide, "CommonExtensions", "Microsoft", "VisualStudio"),
    ]
    results["unity_tools"] = False
    for ud in unity_dirs:
        if os.path.isdir(ud):
            for _, _, files in os.walk(ud):
                if any("unity" in f.lower() and f.lower().endswith((".pkgdef", ".dll"))
                       for f in files):
                    results["unity_tools"] = True
                    break

    products = query_installed(install_path)
    results["vswhere_registered"] = bool(products)

    ok = all([results["devenv"], results["unity_tools"]])
    return ok, results


def _setup_running():
    """是否仍有 VS 安装进程在跑。"""
    try:
        out = subprocess.run(["tasklist"], capture_output=True, timeout=30).stdout
        txt = out.decode("utf-8", "replace")
    except Exception:
        txt = ""
    low = txt.lower()
    return ("setup.exe" in low or "installershell.exe" in low)


def run_install(boot_exe: str, install_path: str, hub: bool, log_cb=None):
    """同步跑引导程序，流式输出到 log_cb；装完等待稳定。"""
    args = build_install_args(install_path, hub)
    cmd = [f'"{boot_exe}"'] + args
    display = " ".join(cmd)
    if log_cb:
        log_cb("=> 命令: " + display + "\n")

    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         universal_newlines=True, errors="ignore")
    for line in p.stdout:
        if log_cb:
            log_cb(line.rstrip("\r\n") + "\n")
    p.wait()
    # 引导程序可能先返回、真实安装仍在后台：等待其稳定
    deadline = time.time() + 240
    while time.time() < deadline:
        if not _setup_running():
            # 再确认 2 秒内无安装进程且目录已有 devenv
            time.sleep(3)
            if not _setup_running():
                break
        time.sleep(5)
    return p.returncode


def ensure_clean_temp(dirpath):
    if os.path.isdir(dirpath):
        shutil.rmtree(dirpath, ignore_errors=True)
    os.makedirs(dirpath, exist_ok=True)


if __name__ == "__main__":
    # 冒烟测试
    print("URL 2022/Community:", bootstrap_url("2022", "Community"))
    args = build_install_args(r"D:\tools\visualstudio2022", hub=True)
    print("install args:", args)