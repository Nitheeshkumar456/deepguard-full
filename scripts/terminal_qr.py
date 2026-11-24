import qrcode
import sys

def main():
    wifi_ip = "192.168.1.8"
    alt_ip = "10.91.181.20"

    print("=" * 60)
    print(" DEEPGUARD AI - MOBILE ACCESS & APK DOWNLOAD")
    print("=" * 60)
    print(f"\n[Wi-Fi Network] (If your phone is connected to your Home Wi-Fi):")
    print(f"  👉 Web App URL:    http://{wifi_ip}:5173")
    print(f"  👉 API Gateway:    http://{wifi_ip}:5000")
    print(f"  👉 Backend Docs:   http://{wifi_ip}:8000/docs")
    print(f"  👉 Download APK:   http://{wifi_ip}:5000/download-apk")
    print("-" * 60)
    print(f"Scan QR code below for Wi-Fi Web App (http://{wifi_ip}:5173):")
    qr = qrcode.QRCode()
    qr.add_data(f"http://{wifi_ip}:5173")
    qr.print_ascii(invert=True)
    print("-" * 60)

    print(f"\n[Direct Public APK Download] (Works on Mobile Data / 4G / 5G / Any Wi-Fi):")
    print("  👉 https://github.com/Nitheeshkumar456/deepguard-full/releases/download/v2.4.0/DeepGuard-AI.apk")
    print("=" * 60)

if __name__ == "__main__":
    main()

