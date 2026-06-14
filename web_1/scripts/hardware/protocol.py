"""Arduino 灯板共享协议：常量、串口扫描、信号发送。

relay.py 和 start_signal.py 的公共依赖，避免协议逻辑重复。
"""

import time
import serial
import serial.tools.list_ports

BAUD_RATE = 9600
START_CMD = bytes.fromhex("A00701A8")  # 红灯+蜂鸣器开
STOP_CMD = bytes.fromhex("A00000A0")   # 全部关闭
DEFAULT_BEEP_DURATION_MS = 3000

# Arduino 常见 USB Vendor ID
_ARDUINO_VIDS = (0x2341, 0x2A03, 0x1A86)


def find_arduino_port():
    """自动扫描串口，查找 Arduino 设备。返回设备名或 None。"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        vid = getattr(port, "vid", None)
        desc = (port.description or "").lower()
        manufacturer = (port.manufacturer or "").lower()

        if vid in _ARDUINO_VIDS:
            return port.device
        if "arduino" in desc or "arduino" in manufacturer:
            return port.device
        if "ch340" in desc or "ch340" in manufacturer:
            return port.device

    # fallback: 第一个可用串口
    if ports:
        return ports[0].device
    return None


def list_ports():
    """列出所有可用串口（含 VID/PID），格式化后返回字符串。"""
    ports = serial.tools.list_ports.comports()
    if not ports:
        return "无可用串口"

    lines = []
    for p in ports:
        vid_str = f"{p.vid:04X}" if p.vid is not None else "----"
        pid_str = f"{p.pid:04X}" if p.pid is not None else "----"
        lines.append(f"  {p.device} — {p.description} (VID:{vid_str} PID:{pid_str})")
    return "\n".join(lines)


def send_arduino_signal(port_name, beep_duration_ms=DEFAULT_BEEP_DURATION_MS):
    """向指定串口发送 开始→等待→关闭 信号序列。

    返回 True 表示完整序列成功发送；False 表示过程中发生可恢复错误。
    KeyboardInterrupt 会被捕获以发送紧急关闭信号，然后重新抛出。
    """
    ser = None
    start_sent = False
    try:
        ser = serial.Serial(port_name, BAUD_RATE, timeout=2)
        ser.write(START_CMD)
        start_sent = True
        print(
            f"[{time.strftime('%H:%M:%S')}] → {port_name} "
            f"开始信号已发送 (beep={beep_duration_ms}ms)"
        )
        time.sleep(beep_duration_ms / 1000)
        ser.write(STOP_CMD)
        print(f"[{time.strftime('%H:%M:%S')}] → {port_name} 关闭信号已发送")
        return True
    except KeyboardInterrupt:
        if start_sent and ser and ser.is_open:
            try:
                ser.write(STOP_CMD)
                print(
                    f"[{time.strftime('%H:%M:%S')}] → {port_name} "
                    "紧急关闭信号已发送"
                )
            except Exception:
                pass
        raise
    except Exception as e:
        print(f"[ERROR] 串口通讯失败: {e}")
        return False
    finally:
        if ser and ser.is_open:
            ser.close()
