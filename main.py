# -*- coding: utf-8 -*-
"""VSUnityInstaller - GUI 入口（Tkinter，PyInstaller 打包为单 exe）。"""
import hashlib
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from installer import (
    download_bootstrapper, run_install, verify_install,
    query_installed, EDITIONS, YEARS,
)

APP_NAME = "VSUnityInstaller"
LOG_FILENAME = "install.log"
DEFAULT_PATH = r"D:\tools\visualstudio2022"
CONFIG_FILE = "config.txt"


def _exe_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE = _exe_dir()


def _log_path():
    # 尽量写到可写目录；当前目录不可写则退回临时目录
    try:
        p = os.path.join(BASE, LOG_FILENAME)
        with open(p, "a"):  # noqa: SIM115 - probe writability
            pass
        return p
    except OSError:
        return os.path.join(os.path.expanduser("~"), LOG_FILENAME)


def _load_cfg():
    try:
        with open(os.path.join(BASE, CONFIG_FILE), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("path="):
                    return line.split("=", 1)[1]
    except OSError:
        pass
    return None


def _save_cfg(path):
    try:
        with open(os.path.join(BASE, CONFIG_FILE), "w", encoding="utf-8") as f:
            f.write("path=" + path + "\n")
    except OSError:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VSUnityInstaller —— 一键安装 Visual Studio(Unity 工作负载)")
        self.geometry("680x560")
        self._busy = False

        self._year = tk.StringVar(value="2026")
        self._edition = tk.StringVar(value="Community")
        self._path = tk.StringVar(value=_load_cfg() or DEFAULT_PATH)
        self._hub = tk.BooleanVar(value=True)

        fr = ttk.Frame(self, padding=14)
        fr.pack(fill="both", expand=True)

        # --- 版本选择 ---
        ttk.Label(fr, text="Visual Studio 版本").grid(row=0, column=0, sticky="w")
        for i, (yval, ylabel) in enumerate(YEARS):
            ttk.Radiobutton(fr, text=ylabel, variable=self._year, value=yval)\
                .grid(row=1, column=i, sticky="w")
        for i, e in enumerate(EDITIONS):
            ttk.Radiobutton(fr, text=e, variable=self._edition, value=e)\
                .grid(row=2, column=i, sticky="w")

        # --- 安装路径 ---
        ttk.Label(fr, text="安装位置").grid(row=3, column=0, sticky="w", pady=(16, 2))
        ttk.Entry(fr, textvariable=self._path, width=60).grid(row=4, column=0,
                                                              columnspan=3,
                                                              sticky="ew", padx=(0, 6))
        ttk.Button(fr, text="浏览…", command=self._browse)\
            .grid(row=4, column=3, sticky="w")

        # --- Unity Hub 开关 ---
        ttk.Checkbutton(fr, text="同时安装 Unity Hub(推荐)",
                        variable=self._hub,
                        onvalue=True, offvalue=False)\
            .grid(row=5, column=0, sticky="w", pady=(16, 2))

        # --- 操作按钮 ---
        self._btn = ttk.Button(fr, text="开始安装", command=self._start)
        self._btn.grid(row=6, column=0, sticky="w", pady=(10, 6))

        # --- 输出区 ---
        self._out = tk.Text(fr, height=18, wrap="none",
                            bg="#0e1116", fg="#c9d1d9",
                            insertbackground="#c9d1d9")
        sout = ttk.Scrollbar(fr, command=self._out.yview)
        self._out.configure(yscrollcommand=sout.set)
        self._out.grid(row=7, column=0, columnspan=4, sticky="nsew")
        sout.grid(row=7, column=4, sticky="ns")

        fr.columnconfigure(1, weight=1)
        fr.rowconfigure(7, weight=1)
        self._logf = _log_path()
        self._log("== %s 启动于 %s ==" % (APP_NAME, __import__("datetime").datetime.now()))
        self._log("日志: " + self._logf)
        self._log("安装程序仅调用官方引导程序，建议先关闭其它安装器。")

    def _log(self, msg):
        stamp = __import__("datetime").datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {msg}"
        self._out.insert("end", line + "\n")
        self._out.see("end")
        self.update_idletasks()
        try:
            with open(self._logf, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def _browse(self):
        d = filedialog.askdirectory(title="选择 Visual Studio 安装目录")
        if d:
            self._path.set(d)

    def _set_busy(self, busy):
        self._busy = busy
        self._btn.configure(state="disabled" if busy else "normal")

    def _preflight(self):
        p = self._path.get().strip()
        if not p:
            messagebox.showwarning(APP_NAME, "请填写安装位置。")
            return None
        if os.path.exists(p) and not os.path.isdir(p):
            messagebox.showwarning(APP_NAME, "目标路径已存在但不是目录。")
            return None
        found = query_installed(p)
        if found:
            prod = found[0].get("displayName") or found[0].get("productId")
            if not messagebox.askyesno(
                    APP_NAME,
                    f"检测到 {os.path.normpath(p)} 已安装: {prod}\n\n"
                    "继续可能重复安装或需走修改流程。仍要继续吗？"):
                return None
        return p

    def _start(self):
        if self._busy:
            return
        path = self._preflight()
        if path is None:
            return
        self._set_busy(True)
        self._log("==============================")
        self._log(f"版本: {self._year.get()}  {self._edition.get()}")
        self._log(f"路径: {path}   Unity Hub: {'是' if self._hub.get() else '否'}")
        _save_cfg(path)
        t = threading.Thread(target=self._worker, args=(path,), daemon=True)
        t.start()

    def _worker(self, path):
        try:
            tmp = os.path.join(os.environ.get("TEMP")
                               or os.path.expanduser("~"), APP_NAME + "_tmp")
            try:
                os.makedirs(tmp, exist_ok=True)
            except OSError:
                tmp = os.path.join(os.path.expanduser("~"), APP_NAME + "_tmp")
                os.makedirs(tmp, exist_ok=True)

            self._log(f"[1/3] 下载引导程序: {self._year.get()} {self._edition.get()} ...")
            boot = download_bootstrapper(self._year.get(), self._edition.get(),
                                         tmp, progress_cb=self._progress)
            self._log(f"      引导程序就绪: {os.path.basename(boot)}")

            self._log("[2/3] 开始静默安装(若弹出 UAC 请点「是」) ...")
            rc = run_install(boot, path, self._hub.get(), log_cb=self._log)
            self._log(f"      安装进程退出码: {rc}")

            self._log("[3/3] 自动核验 ...")
            ok, results = verify_install(path)
            for k, v in results.items():
                self._log(f"      核验 {k}: {'通过 ✓' if v else '未通过 ✗'}")
            if ok:
                self._log("✔ 安装完成，Unity 工作负载已就绪。")
                self._after_ui(lambda: messagebox.showinfo(
                    APP_NAME, "安装完成 ✓\n\ndevenv 与 VS Tools for Unity 均就位。\n"
                              "到 Unity 的 Edit > Preferences > External Tools "
                              "把脚本编辑器设为 Visual Studio 即可。"))
            else:
                self._log("✘ 核验未能全部通过，详见上方清单。")
                self._after_ui(lambda: messagebox.showwarning(
                    APP_NAME, "安装可能有未完成项，请查看核验结果。"))
        except Exception as e:  # noqa: BLE001
            self._log(f"! 错误: {e}")
            self._after_ui(lambda: messagebox.showerror(APP_NAME, f"安装出错:\n{e}"))
        finally:
            self._after_ui(lambda: self._set_busy(False))

    def _progress(self, pct, done, total):
        self._log(f"      下载 {pct:.0f}%  ({done//(1024*1024)}/{total//(1024*1024)} MB)")

    def _after_ui(self, fn):
        self.after(0, fn)


def main():
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())