"""本地硬件中继：长轮询服务器命令队列 → pyserial → Arduino 灯板。

用法（本地 Windows 终端）：
    cd web_1\scripts\hardware
    ..\..\..\.venv\Scripts\python relay.py

默认连接 analysis.magic-cloak.com，可通过环境变量覆盖：
    set HARDWARE_RELAY_HOST=http://127.0.0.1:5000
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import serial
import serial.tools.list_ports

HOST = os.environ.get("HARDWARE_RELAY_HOST", "https://analysis.magic-cloak.com")
POLL_PATH = "/api/hardware/pending?timeout=30"
BAUD_RATE = 9600
BEEP_DURATION = 3000  # ms


def find_arduino_port():
    """自动扫描串口，查找 Arduino（VID 通常是 2341 或 2A03）。"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        vid = getattr(port, 'vid', None)
        pid = getattr(port, 'pid', None)
        desc = (port.description or "").lower()
        manufacturer = (port.manufacturer or "").lower()
        # Arduino 常见 VID
        if vid in (0x2341, 0x2A03, 0x1A86):
            return port.device
        if "arduino" in desc or "arduino" in manufacturer:
            return port.device
        if "ch340" in desc.lower() or "ch340" in manufacturer:
            return port.device
    # fallback: 第一个可用串口
    if ports:
        return ports[0].device
    return None


def list_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        return "无可用串口"
    lines = []
    for p in ports:
        lines.append(f"  {p.device} — {p.description} (VID:{p.vid:04X} PID:{p.pid:04X})")
    return "\n".join(lines)


def send_to_arduino(port_name):
    """发送开始信号：红灯+蜂鸣→等待→全部关闭。"""
    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=2)
        ser.write(bytes.fromhex("A00701A8"))
        print(f"[{time.strftime('%H:%M:%S')}] → {port_name} 开始信号已发送")
        time.sleep(BEEP_DURATION / 1000)
        ser.write(bytes.fromhex("A00000A0"))
        print(f"[{time.strftime('%H:%M:%S')}] → {port_name} 关闭信号已发送")
        ser.close()
        return True
    except Exception as e:
        print(f"[ERROR] 串口通讯失败: {e}")
        return False


def poll_loop():
    print(f"硬件中继已启动 → {HOST}")
    print(f"可用串口:\n{list_ports()}")
    print("等待服务器指令...\n")

    while True:
        try:
            req = urllib.request.Request(f"{HOST}{POLL_PATH}", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read())
            cmd = data.get("command") if data.get("ok") else None
        except urllib.error.URLError as e:
            print(f"[WARN] 网络错误: {e}，5秒后重试...")
            time.sleep(5)
            continue
        except Exception as e:
            print(f"[ERROR] {e}，3秒后重试...")
            time.sleep(3)
            continue

        if not cmd:
            continue

        cmd_type = cmd.get("type")
        print(f"[{time.strftime('%H:%M:%S')}] 收到命令: {cmd_type}")

        if cmd_type == "hardware_start":
            port = find_arduino_port()
            if not port:
                print("[ERROR] 未找到 Arduino 串口！请检查设备连接。")
                print(f"当前串口:\n{list_ports()}")
                continue
            send_to_arduino(port)


if __name__ == "__main__":
    try:
        poll_loop()
    except KeyboardInterrupt:
        print("\n中继已停止。")
        sys.exit(0)
