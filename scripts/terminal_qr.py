import qrcode
import sys

def main():
    # Public GitHub Release URL - guaranteed to download on any phone and any network (WiFi or Mobile Data)
    github_url = "https://github.com/Nitheeshkumar456/deepguard-full/releases/download/v2.4.0/DeepGuard-AI.apk"
    local_url = "http://10.165.240.131:5000/download/apk"

    print("=" * 60)
    print(" DEEPGUARD AI - ANDROID APK TERMINAL BARCODE / QR CODE")
    print("=" * 60)
    print("\n[RECOMMENDED] Direct Public Download (Works on 4G/5G/Any Wi-Fi):")
    print(github_url)
    print("\nScan the QR code below with your phone's camera:")
    print("-" * 60)
    
    qr = qrcode.QRCode()
    qr.add_data(github_url)
    qr.print_ascii(invert=True)
    
    print("-" * 60)
    print("Alternatively, if on the same local Wi-Fi network:")
    print(local_url)
    print("=" * 60)

if __name__ == "__main__":
    main()

