r"""本地硬件中继：长轮询服务器命令队列 → pyserial → Arduino 灯板。

用法（本地 Windows 终端）：
    cd web_1\scripts\hardware
    python relay.py

依赖：pyserial（项目 venv 中已安装）。建议先激活 venv 再运行。

默认连接 analysis.magic-cloak.com，可通过环境变量覆盖：
    set HARDWARE_RELAY_HOST=http://127.0.0.1:5000
"""

import os
import sys
import time
import json
import platform
import urllib.request
import urllib.error

from protocol import (
    DEFAULT_BEEP_DURATION_MS,
    find_arduino_port,
    list_ports,
    send_arduino_signal,
)

HOST = os.environ.get("HARDWARE_RELAY_HOST", "https://analysis.magic-cloak.com")

# POLL_PATH 中的 timeout 参数控制服务端长轮询等待时长（服务端限制 5-60s）。
# 下面 urlopen(timeout=35) 必须 > POLL_PATH timeout，否则 HTTP 客户端会先于
# 服务端返回而超时断连。当前 margin: 35 - 20 = 15s。
POLL_PATH = "/api/hardware/pending?timeout=20"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": f"HardwareRelay/1.0 ({platform.system()} {platform.machine()})",
}


def _post_ack(status):
    """向服务端确认命令执行结果（fire-and-forget）。"""
    try:
        data = json.dumps({"status": status}).encode("utf-8")
        req = urllib.request.Request(
            f"{HOST}/api/hardware/ack", data=data, headers=HEADERS
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # ack 失败不影响主循环


def poll_loop():
    print(f"硬件中继已启动 → {HOST}")
    print(f"可用串口:\n{list_ports()}")
    print("等待服务器指令...\n")

    while True:
        try:
            req = urllib.request.Request(f"{HOST}{POLL_PATH}", headers=HEADERS)
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read())
        except urllib.error.URLError as e:
            print(f"[WARN] 网络错误: {e}，5秒后重试...")
            time.sleep(5)
            continue
        except Exception as e:
            print(f"[ERROR] {e}，3秒后重试...")
            time.sleep(3)
            continue

        if not data.get("ok"):
            err = data.get("error", "未知错误")
            print(f"[WARN] 服务端返回错误: {err}")
            continue

        cmd = data.get("command")
        if cmd is None:
            continue

        cmd_type = cmd.get("type")
        print(f"[{time.strftime('%H:%M:%S')}] 收到命令: {cmd_type}")

        if cmd_type == "hardware_start":
            port = find_arduino_port()
            if not port:
                print("[ERROR] 未找到 Arduino 串口！请检查设备连接。")
                print(f"当前串口:\n{list_ports()}")
                _post_ack("fail")
                continue

            beep_ms = cmd.get("beepDuration", DEFAULT_BEEP_DURATION_MS)
            success = send_arduino_signal(port, beep_duration_ms=beep_ms)
            _post_ack("ok" if success else "fail")


if __name__ == "__main__":
    try:
        poll_loop()
    except KeyboardInterrupt:
        print("\n中继已停止。")
        sys.exit(0)
