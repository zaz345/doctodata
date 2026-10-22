"""测页面在指定视口宽度下是否横向溢出。
用法: python scripts/check_overflow.py <url> [宽度列表]
原理: 用 Edge/Chrome 的 DevTools 协议开启远程调试, 通过 CDP 设置设备指标后
      读取 document.documentElement.scrollWidth 与 innerWidth 比较。
"""
import json
import subprocess
import sys
import time
import urllib.request

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9333


def http_get(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_devtools(deadline=20):
    t0 = time.time()
    while time.time() - t0 < deadline:
        try:
            return http_get(f"http://127.0.0.1:{PORT}/json/version", timeout=2)
        except Exception:
            time.sleep(0.4)
    return None


def ws_connect(ws_url):
    """极简 websocket 客户端（只处理 text frame，不依赖第三方库）。"""
    import base64
    import os
    import socket
    import struct

    assert ws_url.startswith("ws://")
    rest = ws_url[len("ws://"):]
    hostport, path = rest.split("/", 1)
    path = "/" + path
    host, port = hostport.split(":")
    s = socket.create_connection((host, int(port)), timeout=15)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += s.recv(4096)
    return s


def ws_send(s, obj):
    import os
    import struct

    data = json.dumps(obj).encode()
    header = bytearray([0x81])
    n = len(data)
    mask = os.urandom(4)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", n)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", n)
    header += mask
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    s.sendall(bytes(header) + masked)


def ws_recv(s):
    def read_exact(n):
        out = b""
        while len(out) < n:
            chunk = s.recv(n - len(out))
            if not chunk:
                raise ConnectionError("closed")
            out += chunk
        return out

    while True:
        b1, b2 = read_exact(2)
        opcode = b1 & 0x0F
        ln = b2 & 0x7F
        if ln == 126:
            ln = struct_unpack(">H", read_exact(2))
        elif ln == 127:
            ln = struct_unpack(">Q", read_exact(8))
        payload = read_exact(ln)
        if opcode == 0x1:
            return json.loads(payload.decode("utf-8"))
        # 忽略 ping/pong/close


def struct_unpack(fmt, data):
    import struct

    return struct.unpack(fmt, data)[0]


def main():
    url = sys.argv[1]
    widths = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["320", "360", "390", "430", "768"])]

    proc = subprocess.Popen(
        [EDGE, "--headless=new", "--disable-gpu", f"--remote-debugging-port={PORT}",
         "--user-data-dir=E:\\tmp\\edgecdp", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_devtools():
            print("[!] DevTools 未就绪")
            return 1
        info = http_get(f"http://127.0.0.1:{PORT}/json/list")
        page = next((t for t in info if t.get("type") == "page"), None)
        if not page:
            print("[!] 找不到页面 target")
            return 1
        ws = ws_connect(page["webSocketDebuggerUrl"])

        def call(mid, method, params=None):
            ws_send(ws, {"id": mid, "method": method, "params": params or {}})
            while True:
                msg = ws_recv(ws)
                if msg.get("id") == mid:
                    return msg

        mid = 0
        call(++mid, "Page.enable")
        results = []
        for w in widths:
            call(++mid, "Emulation.setDeviceMetricsOverride", {
                "width": w, "height": 844, "deviceScaleFactor": 1, "mobile": True,
            })
            mid_nav = mid = mid + 1
            call(mid_nav, "Page.navigate", {"url": url})
            time.sleep(2.5)
            expr = (
                "JSON.stringify({inner: window.innerWidth,"
                " scroll: document.documentElement.scrollWidth,"
                " bodyScroll: document.body.scrollWidth,"
                " offenders: [...document.querySelectorAll('*')]"
                "   .filter(e => e.getBoundingClientRect().right > window.innerWidth + 1)"
                "   .slice(0,6)"
                "   .map(e => (e.tagName.toLowerCase() + (e.id ? '#' + e.id : '')"
                "     + (e.className && typeof e.className === 'string' ? '.' + e.className.split(' ').slice(0,3).join('.') : ''))"
                "     + ' right=' + Math.round(e.getBoundingClientRect().right))"
                "})"
            )
            r = call(++mid, "Runtime.evaluate", {"expression": expr, "returnByValue": True})
            val = r.get("result", {}).get("result", {}).get("value")
            if val:
                d = json.loads(val)
                over = d["scroll"] > d["inner"] + 1
                results.append((w, d, over))
                print(f"宽度 {w}: innerWidth={d['inner']} scrollWidth={d['scroll']} "
                      f"{'❌ 横向溢出' if over else '✅ 无溢出'}")
                if d["offenders"]:
                    for o in d["offenders"]:
                        print(f"    溢出元素: {o}")
        return 0
    finally:
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
