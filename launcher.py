#!/usr/bin/env python3
"""
agy-cn 启动器：以中文界面启动 Antigravity。

安全设计：
- 用 --remote-debugging-pipe（管道）而不是调试端口：不开任何网络端口，
  只有本进程能控制 Antigravity，其他程序无法连接。
- 不修改 /Applications/Antigravity.app，不联网，不下载任何东西。
- 只注入同目录下的 overlay.js + zh-CN.json（都是本地、可审查的文件）。
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
APP_EXE = "/Applications/Antigravity.app/Contents/MacOS/Antigravity"
LOG = os.path.expanduser("~/Library/Logs/agy-cn.log")


def log(msg):
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
    try:
        cfg = json.loads(payload)
        url = cfg.get("dataUrl") or ""
        if url and not url.startswith("data:image/"):
            return False
        clean = {
            "dataUrl": url,
            "opacity": max(0.03, min(0.8, float(cfg.get("opacity", 0.18)))),
            "blur": max(0, min(20, int(cfg.get("blur", 0)))),
            "scope": "chat" if cfg.get("scope") == "chat" else "all",
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
    payload = {"phrases": d.get("phrases", {}), "bg": load_bg()}
    return js.replace("/*__DICT__*/", json.dumps(payload, ensure_ascii=False))


def main():
    if not os.path.isfile(APP_EXE):
        alert("未找到 " + APP_EXE)
        return 1
    if is_running():
        alert("Antigravity 正在运行。请先完全退出（⌘Q），再打开「Antigravity 中文」。")
        return 1

    script = build_script()

    # 管道：to_app 由 Antigravity 在 fd3 读取命令；from_app 由 Antigravity 在 fd4 写出响应
    to_app_r, to_app_w = os.pipe()
    from_app_r, from_app_w = os.pipe()

    def child_fds():
        # 先挪到高位，避免与 3/4 冲突，再 dup 到 3/4
        import fcntl
        a = fcntl.fcntl(to_app_r, fcntl.F_DUPFD, 10)
        b = fcntl.fcntl(from_app_w, fcntl.F_DUPFD, 10)
        os.dup2(a, 3); os.dup2(b, 4)
        os.setsid()

    proc = subprocess.Popen(
        [APP_EXE, "--remote-debugging-pipe", "--lang=zh-CN"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        preexec_fn=child_fds, close_fds=False,
    )
    os.close(to_app_r); os.close(from_app_w)
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

    def on_page(session):
        send("Page.enable", session=session)
        send("Runtime.enable", session=session)
        send("Runtime.addBinding", {"name": "__agyCnSaveBg"}, session)
        send("Page.addScriptToEvaluateOnNewDocument", {"source": script}, session)
        send("Runtime.evaluate", {"expression": script}, session)
        send("Runtime.runIfWaitingForDebugger", session=session)

    send("Target.setDiscoverTargets", {"discover": True})
    send("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True})
    log("已启动 Antigravity (pid %d)，等待窗口..." % proc.pid)

    buf = b""
    got_any = False
    start = time.time()
    attached = set()
    sessions = {}
    missing = set()
    diag_ids = {}
    next_diag = time.time() + 0.5
    diag_rounds = 0
    import select
    while True:
        now = time.time()
        fast_boot = (now - start) < 12.0
        if now >= next_diag:
            # 启动前 12 秒每 0.4 秒快速检查，之后每 3 秒检查（几乎不占 CPU）
            next_diag = now + (0.4 if fast_boot else 3.0)
            diag_rounds += 1
            if not fast_boot and diag_rounds % 10 == 0:  # 每 30 秒导出一次未翻译短语
                for sid in list(sessions):
                    diag_ids[send("Runtime.evaluate", {"expression": "JSON.stringify([...(window.__agyCnMissing||[])])", "returnByValue": True}, sid)] = ("M", sid)
            for sid in list(sessions):
                diag_ids[send("Runtime.evaluate", {"expression": "!!window.__agyCnInstalled", "returnByValue": True}, sid)] = sid
        ready, _, _ = select.select([inp], [], [], 0.2 if fast_boot else 1.0)
        if not ready:
            if not got_any and time.time() - start > 15:
                log("15 秒内未收到响应：该版本可能不支持 --remote-debugging-pipe")
                alert("汉化未生效：当前 Antigravity 版本不支持管道调试模式。应用仍可正常使用（英文）。")
                break
            continue
        chunk = inp.read(65536)
        if not chunk:
            break  # Antigravity 已退出
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
                sid = diag_ids.pop(m["id"])
                if isinstance(sid, tuple):
                    try:
                        missing.update(json.loads(m["result"]["result"]["value"]))
                        with open(os.path.join(HERE, "missing.txt"), "w", encoding="utf-8") as f:
                            f.write("\n".join(sorted(missing)))
                    except Exception:
                        pass
                    continue
                if "error" in m:
                    sessions.pop(sid, None)
                elif m.get("result", {}).get("result", {}).get("value") is False:
                    send("Runtime.enable", session=sid)
                    send("Runtime.addBinding", {"name": "__agyCnSaveBg"}, sid)
                    send("Runtime.evaluate", {"expression": script}, sid)
                continue
            if meth == "Runtime.bindingCalled" and p.get("name") == "__agyCnSaveBg":
                if save_bg(p.get("payload", "{}")):
                    script = build_script()
                    log("已保存自定义背景配置")
                continue
            if meth == "Target.detachedFromTarget":
                sessions.pop(p.get("sessionId"), None)
            if meth == "Target.targetCreated":
                info = p.get("targetInfo", {})
                pass  # 由 setAutoAttach 自动附着，避免重复会话
            elif meth == "Target.attachedToTarget":
                info = p.get("targetInfo", {})
                attached.add(info.get("targetId"))
                sid = p["sessionId"]
                if info.get("type") in ("page", "iframe", "webview"):
                    sessions[sid] = info.get("type")
                    # 让子框架 / webview 也自动附着并注入
                    send("Target.setAutoAttach", {"autoAttach": True, "waitForDebuggerOnStart": True, "flatten": True}, sid)
                    on_page(sid)
                else:
                    send("Runtime.runIfWaitingForDebugger", session=sid)
            elif meth in ("Page.frameNavigated", "Page.domContentEventFired", "Page.loadEventFired") and m.get("sessionId"):
                if meth != "Page.frameNavigated" or not p.get("frame", {}).get("parentId"):
                    send("Runtime.enable", session=m["sessionId"])
                    send("Runtime.addBinding", {"name": "__agyCnSaveBg"}, m["sessionId"])
                    send("Runtime.evaluate", {"expression": script}, m["sessionId"])
    log("Antigravity 已退出")
    return 0


if __name__ == "__main__":
    sys.exit(main())
