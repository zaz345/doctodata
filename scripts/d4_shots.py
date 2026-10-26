"""一次性生成 Portfolio 用的 4 张截图（桌面首页/结果页/报告页 + 手机首页）。
用法: python scripts/d4_shots.py [base_url]
产物: .shots/portfolio/*.png
说明: 直接驱动线上页面真实跑两次抽取, 报告页只用两份发票
      （不用房源, 否则 20.9 万 vs 3.4 万 同轴会把发票柱子压成一条线）。
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
PORT = 9341
OUT = r"E:\WorkBuddy_WorkSpace\remoteEarn\DocToData\.shots\portfolio"


class CDP:
    def __init__(self, ws_url):
        rest = ws_url[len("ws://"):]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.s = socket.create_connection((host, int(port)), timeout=240)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(
            (f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
             f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
             f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
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

    def eval(self, expr, await_promise=False):
        r = self.call("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": await_promise})
        return r.get("result", {}).get("result", {}).get("value")

    def shot(self, path, scale=2):
        r = self.call("Page.captureScreenshot",
                      {"format": "png", "captureBeyondViewport": False})
        data = r.get("result", {}).get("data")
        if data:
            with open(path, "wb") as f:
                f.write(base64.b64decode(data))
            kb = os.path.getsize(path) / 1024
            print(f"   -> {os.path.basename(path)}  ({kb:.0f} KB)")
            trim_bottom(path)
            return True
        print("   [!] 截图失败")
        return False


def wait_view(c, view, timeout=120):
    for _ in range(timeout):
        time.sleep(1)
        v = c.eval(f"(() => {{ const e = document.getElementById('{view}');"
                   f" return e && !e.classList.contains('hidden') ? 1 : 0; }})()")
        if v == 1:
            return True
    return False


def trim_bottom(path, pad_px=80):
    """裁掉底部多余的纯色空白，让图更饱满（Upwork 里不会显得内容少）。"""
    from PIL import Image

    im = Image.open(path).convert("RGB")
    w, h = im.size
    bg = im.getpixel((4, h - 4))

    def row_is_bg(y):
        for x in range(0, w, 32):
            px = im.getpixel((x, y))
            if sum(abs(a - b) for a, b in zip(px, bg)) > 14:
                return False
        return True

    y = h - 1
    while y > 0 and row_is_bg(y):
        y -= 1
    new_h = min(h, y + pad_px)
    if h - new_h > 40:
        im.crop((0, 0, w, new_h)).save(path)
        print(f"   ✂ 裁掉底部 {h - new_h}px -> {new_h}px 高")


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "https://doctodata.onrender.com").rstrip("/")
    os.makedirs(OUT, exist_ok=True)

    proc = subprocess.Popen(
        [EDGE, "--remote-debugging-port=%d" % PORT,
         "--user-data-dir=E:\\tmp\\edge_d4shots_headful",
         "--no-first-run", "--no-default-browser-check",
         "--window-position=0,0", "--window-size=1460,1200",
         "--hide-scrollbars", "--disable-features=CalculateNativeWinOcclusion",
         "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        page = None
        for _ in range(60):
            try:
                lst = json.loads(urllib.request.urlopen(
                    f"http://127.0.0.1:{PORT}/json/list", timeout=2).read().decode())
                page = next((t for t in lst if t.get("type") == "page"), None)
                if page:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if not page:
            print("[!] 连不上 DevTools")
            return 1

        c = CDP(page["webSocketDebuggerUrl"])
        c.call("Page.enable")
        c.call("Runtime.enable")

        # ---------- 1. 桌面首页 ----------
        print("[1/4] 首页")
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 1440, "height": 900, "deviceScaleFactor": 2, "mobile": False})
        c.call("Page.navigate", {"url": base + "/ui/"})
        time.sleep(6)  # 等 samples 列表加载完
        c.shot(os.path.join(OUT, "1-home.png"))

        # ---------- 2. 结果页（第一份发票）----------
        print("[2/4] 结果页")
        c.eval("runSample('invoice_01.pdf')", await_promise=True)
        if not wait_view(c, "view-result"):
            print("   [!] 结果页没出现")
        time.sleep(1.5)
        # PDF 预览要 view=Fit 才显示整页；只改 hash 不会重载，必须换 URL 强制刷新
        c.eval("(()=>{const f=document.querySelector('#preview iframe');"
               " if(!f) return; const b=f.src.split('#')[0];"
               " if(f.src.includes('view=Fit\"')||f.src.includes('view=Fit&')) return;"
               " f.src = b + '?r=' + Date.now() + '#toolbar=0&view=Fit';})()")
        time.sleep(4)
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 1440, "height": 1000, "deviceScaleFactor": 2, "mobile": False})
        time.sleep(1)
        c.shot(os.path.join(OUT, "2-result.png"))

        # ---------- 3. 报告页（两份发票，图表比例才好看）----------
        print("[3/4] 报告页（第二份 + 出图）")
        c.eval("runSample('invoice_02.pdf')", await_promise=True)
        time.sleep(1.5)
        c.eval("renderReport(); show('view-report');")
        if not wait_view(c, "view-report"):
            print("   [!] 报告页没出现")
        time.sleep(2.5)  # 等 Chart.js 动画结束
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 1440, "height": 1150, "deviceScaleFactor": 2, "mobile": False})
        time.sleep(1)
        c.shot(os.path.join(OUT, "3-report.png"))

        # ---------- 4. 手机首页 ----------
        print("[4/4] 手机端首页")
        c.call("Emulation.setDeviceMetricsOverride",
               {"width": 390, "height": 844, "deviceScaleFactor": 3, "mobile": True})
        c.call("Page.navigate", {"url": base + "/ui/"})
        time.sleep(6)
        c.shot(os.path.join(OUT, "4-mobile.png"))
        return 0
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
