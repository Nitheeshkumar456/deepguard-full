import qrcode
import sys

def main():
    # Direct Universal APK Download URL for v2.6.0 (Pre-configured with Permanent Static Domain https://shove-siren-unreal.ngrok-free.dev)
    url = "https://github.com/Nitheeshkumar456/deepguard-full/releases/download/v2.6.0/DeepGuard-AI.apk"
    
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    
    print("\n" + "=" * 56)
    print("   DEEPGUARD AI v2.6.0 — PERMANENT DOMAIN APK BARCODE")
    print("=" * 56)
    print(f"\nAPK URL: {url}\n")
    print("Permanent Server: https://shove-siren-unreal.ngrok-free.dev")
    print("Works on: ANY Wi-Fi, Hotspot, 4G, 5G (No IP issues!)")
    print("Scan the QR code below with your phone camera:")
    print("-" * 56 + "\n")
    
    # Invert=False matches Expo terminal output on dark theme terminals
    qr.print_ascii(invert=False)
    
    print("\n" + "-" * 56)
    print("Scan to download DeepGuard-AI v2.6.0")
    print("=" * 56 + "\n")

if __name__ == "__main__":
    main()
