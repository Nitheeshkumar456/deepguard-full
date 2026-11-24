import qrcode
import sys

def main():
    # Direct Universal Download URL — Works on ANY phone, Mobile Data, 4G, 5G, or Wi-Fi (No "couldn't connect" error!)
    universal_apk_url = "https://github.com/Nitheeshkumar456/deepguard-full/releases/download/v2.4.0/DeepGuard-AI.apk"
    local_apk_url = "http://192.168.137.253:5000/download-apk"

    print("\n" + "=" * 55)
    print("      DEEPGUARD AI — ANDROID APK DOWNLOAD BARCODE")
    print("=" * 55)
    print("\n[RECOMMENDED] Direct Download (4G / 5G / Any Wi-Fi):")
    print(f"{universal_apk_url}\n")

    qr1 = qrcode.QRCode(border=2)
    qr1.add_data(universal_apk_url)
    qr1.print_ascii(invert=True)

    print("\n" + "-" * 55)
    print("[LOCAL WI-FI] Hotspot / LAN Download:")
    print(f"{local_apk_url}\n")

    qr2 = qrcode.QRCode(border=2)
    qr2.add_data(local_apk_url)
    qr2.print_ascii(invert=True)

    print("=" * 55 + "\n")

if __name__ == "__main__":
    main()
