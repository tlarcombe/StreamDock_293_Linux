import hid
import time
import os
from PIL import Image

VENDOR_ID = 0x5500
PRODUCT_ID = 0x1001
PREFIX = b"CRT\x00\x00"
REPORT_SIZE = 512

def send_report(device, payload):
    if len(payload) > REPORT_SIZE:
        payload = payload[:REPORT_SIZE]
    elif len(payload) < REPORT_SIZE:
        payload = payload.ljust(REPORT_SIZE, b"\x00")
    device.write(b"\x00" + payload)

def send_image(device, cmd, index, image_path):
    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found")
        return
        
    with open(image_path, "rb") as f:
        img_data = f.read()
        
    size = len(img_data)
    print(f"Sending image to {cmd.decode()} index {index} ({size} bytes)")
    
    # Header
    header = PREFIX + cmd + size.to_bytes(4, "big") + bytes([index])
    send_report(device, header)
    
    # Data
    for i in range(0, size, REPORT_SIZE):
        chunk = img_data[i : i + REPORT_SIZE]
        send_report(device, chunk)
        
    # STP
    send_report(device, PREFIX + b"STP\x00\x00")

def main():
    # Create a small red test image (100x100) and a larger blue one (480x272)
    red_path = "/tmp/test_red.jpg"
    blue_path = "/tmp/test_blue.jpg"
    
    Image.new('RGB', (100, 100), color='red').save(red_path, 'JPEG', quality=90, subsampling=0)
    Image.new('RGB', (480, 272), color='blue').save(blue_path, 'JPEG', quality=90, subsampling=0)
    
    device = hid.device()
    try:
        device.open(VENDOR_ID, PRODUCT_ID)
        print("Device opened.")
        
        # Try BAT index 0 (current approach)
        print("\nTest 1: BAT index 0 (Blue 480x272)")
        send_image(device, b"BAT", 0, blue_path)
        time.sleep(2)
        
        # Try WPA index 0
        print("\nTest 2: WPA index 0 (Red 100x100 - see if any change)")
        send_image(device, b"WPA", 0, red_path)
        time.sleep(2)
        
        # Try WPA (no index/index 0 but larger blue)
        print("\nTest 3: WPA index 0 (Blue 480x272)")
        send_image(device, b"WPA", 0, blue_path)
        time.sleep(2)
        
        # Try WAV index 0
        print("\nTest 5: WAV index 0 (Blue 480x272)")
        send_image(device, b"WAV", 0, blue_path)
        time.sleep(2)
        
        # Try BAT index 17
        print("\nTest 7: BAT index 17 (Blue 480x272)")
        send_image(device, b"BAT", 17, blue_path)
        time.sleep(2)
        
        # Try WPA index 17
        print("\nTest 8: WPA index 17 (Blue 480x272)")
        send_image(device, b"WPA", 17, blue_path)
        time.sleep(2)
        
        print("\nDone.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        device.close()

if __name__ == "__main__":
    main()
