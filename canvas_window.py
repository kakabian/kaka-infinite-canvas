"""画布窗口 —— 把本地 10027 画布装进原生窗口（WebView2），不经过浏览器标签页。"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import webview
from webview.menu import Menu, MenuAction, MenuSeparator

APP_NAME = "无限画布"
HOST = "127.0.0.1"
PORT = 10027
WORKER_PORT = 8089
CREATE_NO_WINDOW = 0x08000000


def app_root() -> Path:
    """项目根：优先找含 run.py 的目录（exe 可能放在 dist 子目录里）。"""
    if getattr(sys, "frozen", False):
        here = Path(sys.executable).resolve().parent
        for depth, cand in enumerate((here, *here.parents)):
            if depth > 3:
                break
            if (cand / "run.py").is_file():
                return cand
        return here
    return Path(__file__).resolve().parent


ROOT = app_root()
DATA = ROOT / "data"
LOGS = ROOT / "logs"

SERVICES: list[subprocess.Popen] = []
OWNED = False
WINDOW = None

SPLASH = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{height:100%;margin:0;background:#0e1014;color:#e6e8ee;
font-family:"Microsoft YaHei UI","Segoe UI",sans-serif;display:flex;
align-items:center;justify-content:center}
.box{text-align:center}
.t{font-size:22px;letter-spacing:2px;margin-bottom:14px}
.s{font-size:13px;color:#8b93a7}
.bar{width:220px;height:3px;background:#1e2230;border-radius:3px;margin:22px auto 0;overflow:hidden}
.bar i{display:block;width:40%;height:100%;background:#22c55e;border-radius:3px;
animation:go 1.1s ease-in-out infinite}
@keyframes go{0%{transform:translateX(-100%)}100%{transform:translateX(320%)}}
</style></head><body><div class="box">
<div class="t">无限画布</div>
<div class="s">正在启动本地服务…</div>
<div class="bar"><i></i></div>
</div></body></html>"""


def python_exe() -> str | None:
    for cand in (ROOT / ".venv" / "Scripts" / "python.exe",
                 ROOT / "runtime" / "python312" / "python.exe"):
        if cand.is_file():
            return str(cand)
    if not getattr(sys, "frozen", False):
        return sys.executable
    return None


def port_open(port: int, timeout: float = 0.4) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((HOST, port)) == 0


def spawn(args: list[str], tag: str) -> subprocess.Popen | None:
    py = python_exe()
    if not py:
        return None
    LOGS.mkdir(parents=True, exist_ok=True)
    log = open(LOGS / f"{tag}.log", "ab", buffering=0)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.Popen(
        [py, *args], cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
        creationflags=CREATE_NO_WINDOW, env=env,
    )


def start_services() -> None:
    global OWNED
    if not port_open(WORKER_PORT):
        p = spawn(["-m", "backend.run_worker"], "worker")
        if p:
            SERVICES.append(p)
        time.sleep(1.0)
    if not port_open(PORT):
        p = spawn(["run.py"], "canvas")
        if p:
            SERVICES.append(p)
    OWNED = bool(SERVICES)


def wait_ready(seconds: float = 90.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if port_open(PORT):
            time.sleep(1.2)
            return True
        time.sleep(0.4)
    return False


def stop_services() -> None:
    for p in SERVICES:
        try:
            if p.poll() is None:
                p.terminate()
        except Exception:
            pass
    for p in SERVICES:
        try:
            p.wait(timeout=6)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    SERVICES.clear()


def open_data_dir(_=None) -> None:
    os.startfile(str(DATA))


def open_browser(_=None) -> None:
    webbrowser.open(f"http://{HOST}:{PORT}/")


def restart(_=None) -> None:
    global OWNED
    stop_services()
    OWNED = False
    start_services()
    if wait_ready() and WINDOW:
        WINDOW.load_url(f"http://{HOST}:{PORT}/")


def quit_app(_=None) -> None:
    if WINDOW:
        WINDOW.destroy()


def boot() -> None:
    if wait_ready(120) and WINDOW:
        WINDOW.load_url(f"http://{HOST}:{PORT}/")
    elif WINDOW:
        WINDOW.load_html(
            "<html><body style='background:#0e1014;color:#e6e8ee;font-family:Microsoft YaHei UI;"
            "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><div style='font-size:20px'>启动失败</div>"
            "<div style='font-size:13px;color:#8b93a7;margin-top:12px'>请双击 start.bat 查看错误信息，"
            "或检查 logs 目录</div></div></body></html>"
        )


def main() -> None:
    global WINDOW
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    start_services()

    menu = Menu("功能", [
        MenuAction("打开浏览器", open_browser),
        MenuAction("打开数据目录", open_data_dir),
        MenuSeparator(),
        MenuAction("重启服务", restart),
        MenuSeparator(),
        MenuAction("退出", quit_app),
    ])

    WINDOW = webview.create_window(
        "无限画布 - kaka",
        html=SPLASH,
        width=1560,
        height=980,
        min_size=(1080, 680),
        background_color="#0e1014",
        text_select=True,
    )
    icon = ROOT / "assets" / "canvas.ico"
    webview.start(
        boot,
        menu=[menu],
        private_mode=False,
        storage_path=str(DATA / "webview"),
        icon=str(icon) if icon.is_file() else None,
    )
    if OWNED:
        stop_services()


if __name__ == "__main__":
    main()