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
        return
        
    with open(image_path, "rb") as f:
        img_data = f.read()
        
    size = len(img_data)
    header = PREFIX + cmd + size.to_bytes(4, "big") + bytes([index])
    send_report(device, header)
    for i in range(0, size, REPORT_SIZE):
        chunk = img_data[i : i + REPORT_SIZE]
        send_report(device, chunk)
    send_report(device, PREFIX + b"STP\x00\x00")

def main():
    blue_path = "/tmp/test_blue.jpg"
    Image.new('RGB', (480, 272), color='blue').save(blue_path, 'JPEG', quality=95)
    
    device = hid.device()
    try:
        device.open(VENDOR_ID, PRODUCT_ID)
        print("Starting timed tests. Please watch the device.")
        
        tests = [
            (b"BAT", 0, "Test 1: BAT index 0"),
            (b"WPA", 0, "Test 2: WPA index 0"),
            (b"WAV", 0, "Test 3: WAV index 0"),
            (b"BAT", 16, "Test 4: BAT index 16"),
            (b"BAT", 17, "Test 5: BAT index 17"),
            (b"WPA", 17, "Test 6: WPA index 17"),
        ]
        
        for cmd, index, desc in tests:
            print(f"\n{desc}...")
            send_image(device, cmd, index, blue_path)
            # Send a refresh call explicitly
            send_report(device, PREFIX + b"STP\x00\x00") 
            time.sleep(5)
            
        print("\nAll tests complete.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        device.close()

if __name__ == "__main__":
    main()
