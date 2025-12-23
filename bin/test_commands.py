import hid
import time

VENDOR_ID = 0x5500
PRODUCT_ID = 0x1001
PREFIX = b"CRT\x00\x00"
CMD_CLE = b"CLE\x00\x00\x00"
REPORT_SIZE = 512

def send_report(device, payload):
    if len(payload) > REPORT_SIZE:
        payload = payload[:REPORT_SIZE]
    elif len(payload) < REPORT_SIZE:
        payload = payload.ljust(REPORT_SIZE, b"\x00")
    device.write(b"\x00" + payload)

def main():
    device = hid.device()
    try:
        device.open(VENDOR_ID, PRODUCT_ID)
        print("Device opened.")
        
        print("Sending CMD_CLE...")
        send_report(device, PREFIX + CMD_CLE)
        time.sleep(1)
        
        # Also try STP just in case it needs a commit
        print("Sending CMD_STP...")
        send_report(device, PREFIX + b"STP\x00\x00")
        
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        device.close()

if __name__ == "__main__":
    main()
