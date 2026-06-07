import serial
import time

# 这里的 'COM3' 需要根据你电脑实际显示的端口号修改 (Windows通常是COMx, Linux/Mac是/dev/ttyUSBx)
SERIAL_PORT = 'COM6' 
BAUD_RATE = 9600

def run_feedback():
    ser = None
    try:
        # 初始化串口
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        
        # 1. 发送：红灯+蜂鸣器 打开 (操作码: A0 07 01 A8)
        # bytes.fromhex 将字符串转为硬件识别的十六进制字节
        start_cmd = bytes.fromhex('A00701A8')
        ser.write(start_cmd)
        print(f"[Hardware] 已发送开始信号: {start_cmd.hex()}")

        # 2. 等待3秒（蜂鸣+红灯）
        time.sleep(3)

        # 3. 发送：全部关闭 (操作码: A0 00 00 A0)
        stop_cmd = bytes.fromhex('A00000A0')
        ser.write(stop_cmd)
        print(f"[Hardware] 已发送关闭信号: {stop_cmd.hex()}")

        return True
    except Exception as e:
        print(f"硬件通讯失败: {e}")
        return False
    finally:
        if ser and ser.is_open:
            ser.close() # 记得关闭串口连接