"""用 CDP 打开 ?autodemo=1 / ?autodemo=report, 等目标视图出现后测溢出并截图。
用法: python scripts/cdp_shot.py <base_url> <mode:result|report> <宽度,宽度...>
"""
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9337
SHOTS = r"E:\WorkBuddy_WorkSpace\remoteEarn\DocToData\.shots"


class CDP:
    def __init__(self, ws_url):
        rest = ws_url[len("ws://"):]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.s = socket.create_connection((host, int(port)), timeout=180)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(
            (f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
             f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
             f"Sec-WebSocket-Version: 13\r\n\r\n").encode()
        )
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.mid = 0

    def _send(self, obj):
        data = json.dumps(obj).encode()
        h = bytearray([0x81])
        n = len(data)
        mask = os.urandom(4)
        if n < 126:
            h.append(0x80 | n)
        elif n < 65536:
            h.append(0x80 | 126)
            h += struct.pack(">H", n)
        else:
            h.append(0x80 | 127)
            h += struct.pack(">Q", n)
        h += mask
        self.s.sendall(bytes(h) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _recv(self):
        def exact(n):
            out = b""
            while len(out) < n:
                c = self.s.recv(n - len(out))
                if not c:
                    raise ConnectionError("ws closed")
                out += c
            return out

        while True:
            b1, b2 = exact(2)
            op = b1 & 0x0F
            ln = b2 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", exact(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", exact(8))[0]
            payload = exact(ln)
            if op == 0x1:
                return json.loads(payload.decode())

    def call(self, method, params=None):
        self.mid += 1
        mid = self.mid
        self._send({"id": mid, "method": method, "params": params or {}})
        while True:
            m = self._recv()
            if m.get("id") == mid:
                return m

    def eval(self, expr):
        r = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("result", {}).get("value")


def main():
    base = sys.argv[1].rstrip("/")
    mode = sys.argv[2]
    widths = [int(x) for x in sys.argv[3].split(",")]
    url = f"{base}/ui/?autodemo={'report' if mode == 'report' else '1'}"
    target_view = "view-report" if mode == "report" else "view-result"

    proc = subprocess.Popen(
        [EDGE, "--headless=new", "--disable-gpu", f"--remote-debugging-port={PORT}",
         f"--user-data-dir=E:\\tmp\\edgecdp_{mode}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # 等 devtools
        page = None
        for _ in range(50):
            try:
                lst = json.loads(urllib.request.urlopen(
                    f"http://127.0.0.1:{PORT}/json/list", timeout=2).read().decode())
                page = next((t for t in lst if t.get("type") == "page"), None)
                if page:
                    break
            except Exception:
                pass
            time.sleep(0.4)
        if not page:
            print("[!] 拿不到页面 target")
            return 1
        c = CDP(page["webSocketDebuggerUrl"])
        c.call("Page.enable")
        c.call("Runtime.enable")

        for w in widths:
            c.call("Emulation.setDeviceMetricsOverride",
                   {"width": w, "height": 900, "deviceScaleFactor": 2, "mobile": True})
            c.call("Page.navigate", {"url": url})

            visible = False
            for _ in range(120):  # 最多 120 秒，容忍冷启动 + 真实抽取
                time.sleep(1)
                v = c.eval(
                    f"(() => {{ const e = document.getElementById('{target_view}');"
                    f" return e && !e.classList.contains('hidden') ? 'YES' : 'NO'; }})()")
                if v == "YES":
                    visible = True
                    break
            if not visible:
                print(f"[{w}px] ❌ {target_view} 未出现（超时）")
                continue
            time.sleep(2)

            data = c.eval(
                "JSON.stringify({inner: window.innerWidth,"
                " scroll: document.documentElement.scrollWidth,"
                " off: [...document.querySelectorAll('*')]"
                "  .filter(e => e.getBoundingClientRect().right > window.innerWidth + 1)"
                "  .slice(0,8)"
                "  .map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '')"
                "    + ' right=' + Math.round(e.getBoundingClientRect().right))})")
            d = json.loads(data)
            over = d["scroll"] > d["inner"] + 1
            print(f"[{w}px] inner={d['inner']} scroll={d['scroll']} "
                  f"{'❌ 横向溢出' if over else '✅ 无溢出'}")
            for o in d["off"]:
                print("      ", o)

            shot = c.call("Page.captureScreenshot",
                          {"format": "png", "captureBeyondViewport": True})
            b64 = shot.get("result", {}).get("data")
            if b64:
                p = os.path.join(SHOTS, f"{mode}_{w}.png")
                with open(p, "wb") as f:
                    f.write(base64.b64decode(b64))
                print(f"       截图 -> {p}")
        return 0
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
