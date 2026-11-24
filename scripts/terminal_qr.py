import qrcode
import sys

def main():
    # Direct Universal APK Download URL for v2.5.0 (Pre-configured with current IP 172.23.19.26 + runtime server changer)
    url = "https://github.com/Nitheeshkumar456/deepguard-full/releases/download/v2.5.0/DeepGuard-AI.apk"
    
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    
    print("\n" + "=" * 54)
    print("   DEEPGUARD AI v2.5.0 — ANDROID APK DOWNLOAD BARCODE")
    print("=" * 54)
    print(f"\nAPK URL: {url}\n")
    print("Configured for Server IP: 172.23.19.26:8000")
    print("Scan the QR code below with your phone camera:")
    print("-" * 54 + "\n")
    
    # Invert=False matches Expo terminal output on dark theme terminals
    qr.print_ascii(invert=False)
    
    print("\n" + "-" * 54)
    print("Scan to download DeepGuard-AI v2.5.0 (Updated IP: 172.23.19.26)")
    print("=" * 54 + "\n")

if __name__ == "__main__":
    main()
