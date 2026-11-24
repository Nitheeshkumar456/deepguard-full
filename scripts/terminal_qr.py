import qrcode
import sys

def main():
    # Direct Universal APK Download URL (Bypasses firewall / local IP issues)
    url = "https://github.com/Nitheeshkumar456/deepguard-full/releases/download/v2.4.0/DeepGuard-AI.apk"
    
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    
    print("\n" + "=" * 50)
    print("   DEEPGUARD AI — ANDROID APK DOWNLOAD BARCODE")
    print("=" * 50)
    print(f"\nAPK URL: {url}\n")
    print("Scan the QR code below with your phone camera:")
    print("-" * 50 + "\n")
    
    # Invert=False matches Expo terminal output on dark theme terminals (like in the photo)
    qr.print_ascii(invert=False)
    
    print("\n" + "-" * 50)
    print("Scan to download DeepGuard-AI.apk directly to phone")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
