import qrcode
import sys

def main():
    # Direct Universal Download URL — Works on ANY phone, Mobile Data, 4G, 5G, or Wi-Fi (No "couldn't connect" error!)
    universal_apk_url = "https://github.com/Nitheeshkumar456/deepguard-full/releases/download/v2.4.0/DeepGuard-AI.apk"
    local_apk_url = "http://192.168.137.253:5000/download-apk"

    print("\n" + "=" * 65)
    print("      DEEPGUARD AI — ANDROID APK DIRECT DOWNLOAD BARCODE")
    print("=" * 65)
    print("\n[RECOMMENDED] Universal Download (Works on 4G, 5G & Any Wi-Fi):")
    print(f"URL: {universal_apk_url}")
    print("\nScan the QR code below with your phone's camera / Google Lens:")
    print("-" * 65)

    qr1 = qrcode.QRCode(border=2)
    qr1.add_data(universal_apk_url)
    qr1.print_ascii(invert=True)

    print("-" * 65)
    print("\n[LOCAL WI-FI] Download over Hotspot/LAN (Requires same Wi-Fi):")
    print(f"URL: {local_apk_url}")
    print("\nScan for Local Wi-Fi Download:")
    print("-" * 65)

    qr2 = qrcode.QRCode(border=2)
    qr2.add_data(local_apk_url)
    qr2.print_ascii(invert=True)

    print("-" * 65)
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

