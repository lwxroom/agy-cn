#!/usr/bin/env python3
"""
agy-cn 启动器：以中文界面启动 Antigravity。

安全设计：
- 用 --remote-debugging-pipe（匿名管道）而不是调试端口：不开任何网络端口，
  只有本进程能控制 Antigravity，其他程序无法连接。
- 严格校验页面 URL 白名单（仅本机 Antigravity 主界面），绝不向外部网页注入脚本或暴露绑定。
- 不修改 /Applications/Antigravity.app，不联网，不下载任何东西。
- 只注入同目录下的 overlay.js + zh-CN.json（都是本地、可审查的文件）。
"""
import json
import os
import re
import select
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP_EXE = "/Applications/Antigravity.app/Contents/MacOS/Antigravity"
LOG = os.path.expanduser("~/Library/Logs/agy-cn.log")
DEBUG = os.environ.get("AGY_CN_DEBUG") == "1"

APP_URL_RE = re.compile(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?(/|$)")
DATA_URL_RE = re.compile(r"^data:image/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$")
MAX_BG_PAYLOAD = 5 * 1024 * 1024  # 5 MB 上限


def is_app_url(url):
    return bool(url and APP_URL_RE.match(url))


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + msg + "\n")


def alert(msg):
    subprocess.run(["osascript", "-e", 'display alert "Antigravity 中文" message %s' % json.dumps(msg)])


def is_running():
    return subprocess.run(["pgrep", "-f", APP_EXE], stdout=subprocess.DEVNULL).returncode == 0


def load_bg():
    p = os.path.join(HERE, "bg-config.json")
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_bg(payload):
    if not isinstance(payload, str) or len(payload) > MAX_BG_PAYLOAD:
        return False
    try:
        cfg = json.loads(payload)
        url = cfg.get("dataUrl") or ""
        if url and not DATA_URL_RE.match(url):
            return False
        clean = {
            "dataUrl": url,
            "opacity": max(0.03, min(0.8, float(cfg.get("opacity", 0.18)))),
            "blur": max(0, min(20, int(cfg.get("blur", 0)))),
            "scope": "chat" if cfg.get("scope") == "chat" else "all",
            "langMode": "en" if cfg.get("langMode") == "en" else "zh",
        }
        p = os.path.join(HERE, "bg-config.json")
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False)
        os.replace(tmp, p)
        return True
    except Exception:
        return False


def build_script():
    with open(os.path.join(HERE, "zh-CN.json"), encoding="utf-8") as f:
        d = json.load(f)
    with open(os.path.join(HERE, "overlay.js"), encoding="utf-8") as f:
        js = f.read()
    payload = {"phrases": d.get("phrases", {}), "bg": load_bg(), "debug": DEBUG}
    return js.replace("/*__DICT__*/", json.dumps(payload, ensure_ascii=False))


def main():
    if not os.path.isfile(APP_EXE):
        alert("未找到 " + APP_EXE)
        return 1
    if is_running():
        alert("Antigravity 正在运行。请先完全退出（⌘Q），再打开「Antigravity 中文」。")
        return 1

    script = build_script()

    # 匿名管道：to_app 由 Antigravity 在 fd3 读取命令；from_app 由 Antigravity 在 fd4 写出响应
    to_app_r, to_app_w = os.pipe()
    from_app_r, from_app_w = os.pipe()

    def child_fds():
        import fcntl
        a = fcntl.fcntl(to_app_r, fcntl.F_DUPFD, 10)
        b = fcntl.fcntl(from_app_w, fcntl.F_DUPFD, 10)
        os.dup2(a, 3)
        os.dup2(b, 4)
        # 清理多余 FD，防止子进程继承父进程句柄导致退出挂起
        os.closerange(5, max(a, b, to_app_r, to_app_w, from_app_r, from_app_w, 1024) + 1)
        os.setsid()

    proc = subprocess.Popen(
        [APP_EXE, "--remote-debugging-pipe", "--lang=zh-CN"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        preexec_fn=child_fds, close_fds=False,
    )
    os.close(to_app_r)
    os.close(from_app_w)
    out = os.fdopen(to_app_w, "wb", buffering=0)
    inp = os.fdopen(from_app_r, "rb", buffering=0)

    msg_id = [0]

    def send(method, params=None, session=None):
        msg_id[0] += 1
        m = {"id": msg_id[0], "method": method, "params": params or {}}
        if session:
            m["sessionId"] = session
        out.write(json.dumps(m).encode("utf-8") + b"\0")
        return msg_id[0]

    def inject(session):
        if session in injected_sessions:
            return
        injected_sessions.add(session)
        send("Runtime.enable", session=session)
        send("Runtime.addBinding", {"name": "__agyCnSaveBg"}, session)
        send("Runtime.evaluate", {"expression": script}, session)

    def on_page(session, url):
        send("Page.enable", session=session)
        if is_app_url(url):
            inject(session)
        send("Runtime.runIfWaitingForDebugger", session=session)

    send("Target.setDiscoverTargets", {"discover": True})
    send("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True})
    log("已启动 Antigravity (pid %d)，等待窗口..." % proc.pid)

    buf = b""
    got_any = False
    start = time.time()
    sessions = {}  # sid -> url
    injected_sessions = set()
    missing = set()
    diag_ids = {}
    next_diag = time.time() + 0.5
    diag_rounds = 0

    try:
        while True:
            now = time.time()
            fast_boot = (now - start) < 12.0
            if now >= next_diag:
                next_diag = now + (0.4 if fast_boot else 3.0)
                diag_rounds += 1
                if len(diag_ids) > 200:
                    diag_ids.clear()
                if DEBUG and not fast_boot and diag_rounds % 10 == 0:
                    for sid, url in list(sessions.items()):
                        if is_app_url(url):
                            diag_ids[send("Runtime.evaluate", {
                                "expression": "JSON.stringify([...(window.__agyCnMissing||[])])",
                                "returnByValue": True,
                            }, sid)] = ("M", sid)
                for sid, url in list(sessions.items()):
                    # 已知是外部网页的 session 不再定时执行 Runtime.evaluate（导航回本机时由 Page.frameNavigated 捕获）
                    if url and url.startswith(("http://", "https://")) and not is_app_url(url):
                        continue
                    diag_ids[send("Runtime.evaluate", {
                        "expression": "JSON.stringify([location.href, !!window.__agyCnInstalled])",
                        "returnByValue": True,
                    }, sid)] = ("C", sid)
            ready, _, _ = select.select([inp], [], [], 0.2 if fast_boot else 1.0)
            if not ready:
                if not got_any and time.time() - start > 15:
                    log("15 秒内未收到响应：该版本可能不支持 --remote-debugging-pipe")
                    alert("汉化未生效：当前 Antigravity 版本不支持管道调试模式。应用仍可正常使用（英文）。")
                    break
                continue
            chunk = inp.read(65536)
            if not chunk:
                break
            buf += chunk
            while b"\0" in buf:
                raw, buf = buf.split(b"\0", 1)
                got_any = True
                try:
                    m = json.loads(raw)
                except ValueError:
                    continue
                meth = m.get("method")
                p = m.get("params", {})
                if m.get("id") in diag_ids:
                    kind, sid = diag_ids.pop(m["id"])
                    if "error" in m:
                        sessions.pop(sid, None)
                        continue
                    val = m.get("result", {}).get("result", {}).get("value")
                    if kind == "M" and DEBUG and val:
                        try:
                            missing.update(json.loads(val))
                            with open(os.path.join(HERE, "missing.txt"), "w", encoding="utf-8") as f:
                                f.write("\n".join(sorted(missing)))
                        except Exception:
                            pass
                    elif kind == "C" and val:
                        try:
                            href, installed = json.loads(val)
                            sessions[sid] = href
                            if is_app_url(href):
                                if installed:
                                    injected_sessions.add(sid)
                                else:
                                    injected_sessions.discard(sid)
                                    inject(sid)
                        except Exception:
                            pass
                    continue
                if meth == "Runtime.bindingCalled" and p.get("name") == "__agyCnSaveBg":
                    sid = m.get("sessionId")
                    if sid and is_app_url(sessions.get(sid, "")) and save_bg(p.get("payload", "{}")):
                        script = build_script()
                        log("已保存自定义配置")
                    continue
                if meth == "Target.detachedFromTarget":
                    sid = p.get("sessionId")
                    sessions.pop(sid, None)
                    injected_sessions.discard(sid)
                elif meth == "Target.attachedToTarget":
                    info = p.get("targetInfo", {})
                    sid = p["sessionId"]
                    url = info.get("url", "")
                    if info.get("type") in ("page", "iframe", "webview"):
                        sessions[sid] = url
                        send("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True}, sid)
                        on_page(sid, url)
                    else:
                        send("Runtime.runIfWaitingForDebugger", session=sid)
                elif meth == "Page.frameNavigated" and m.get("sessionId") and not p.get("frame", {}).get("parentId"):
                    sid = m["sessionId"]
                    url = p.get("frame", {}).get("url", "")
                    sessions[sid] = url
                    injected_sessions.discard(sid)
                    if is_app_url(url):
                        inject(sid)
                elif meth in ("Page.domContentEventFired", "Page.loadEventFired") and m.get("sessionId"):
                    sid = m["sessionId"]
                    if is_app_url(sessions.get(sid, "")):
                        inject(sid)
    except (BrokenPipeError, OSError):
        pass
    finally:
        try:
            out.close()
        except Exception:
            pass
        try:
            inp.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
    log("Antigravity 已退出")
    return 0


if __name__ == "__main__":
    sys.exit(main())
