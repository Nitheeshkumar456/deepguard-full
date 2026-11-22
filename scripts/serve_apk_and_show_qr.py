#!/usr/bin/env python3
"""
serve_apk_and_show_qr.py — DeepGuard AI Android APK Server and Terminal QR Code Generator.

Generates:
1. High-contrast terminal ASCII/Unicode QR codes.
2. PNG QR code images for UI display and embedding.
3. Diagnostic checks for local Wi-Fi vs Mobile Data.
"""

import os
import shutil
import socket
import qrcode

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(ROOT_DIR, "dist-apk")
os.makedirs(DIST_DIR, exist_ok=True)

SOURCE_APK = os.path.join(ROOT_DIR, "android", "app", "build", "outputs", "apk", "debug", "app-debug.apk")
TARGET_APK = os.path.join(DIST_DIR, "DeepGuard-AI.apk")

if os.path.exists(SOURCE_APK):
    shutil.copy2(SOURCE_APK, TARGET_APK)
    print(f"[+] Synced latest Android APK: {TARGET_APK} ({os.path.getsize(TARGET_APK):,} bytes)")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "10.165.240.131"

LOCAL_IP = get_local_ip()
LOCAL_DOWNLOAD_URL = f"http://{LOCAL_IP}:5000/download-apk"
GITHUB_RELEASE_URL = "https://github.com/Nitheeshkumar456/deepguard-full/releases/tag/v2.4.0"

# Generate PNGs
qr_global = qrcode.QRCode(box_size=10, border=2)
qr_global.add_data(GITHUB_RELEASE_URL)
qr_global.make(fit=True)
img_global = qr_global.make_image(fill_color="black", back_color="white")
img_global_path = os.path.join(DIST_DIR, "qr_github_release.png")
img_global.save(img_global_path)

qr_local = qrcode.QRCode(box_size=10, border=2)
qr_local.add_data(LOCAL_DOWNLOAD_URL)
qr_local.make(fit=True)
img_local = qr_local.make_image(fill_color="black", back_color="white")
img_local_path = os.path.join(DIST_DIR, "qr_local_wifi.png")
img_local.save(img_local_path)

# Also copy to artifact dir if exists
ARTIFACT_DIR = r"C:\Users\nithe\.gemini\antigravity\brain\abbcdc35-328c-42fb-af3f-a89535b48c8d"
if os.path.exists(ARTIFACT_DIR):
    shutil.copy2(img_global_path, os.path.join(ARTIFACT_DIR, "qr_github_release.png"))
    shutil.copy2(img_local_path, os.path.join(ARTIFACT_DIR, "qr_local_wifi.png"))

print("\n" + "=" * 76)
print("       DEEPGUARD AI — ANDROID APP DOWNLOAD QR CODES & SERVER")
print("=" * 76)

print("\n[OPTION 1: RECOMMENDED] — GLOBAL GITHUB RELEASE DIRECT DOWNLOAD QR CODE")
print("Works on Mobile Data (4G/5G), College Wi-Fi, Office Network, or Home Wi-Fi")
print("Direct Link: " + GITHUB_RELEASE_URL)
print("-" * 76)
qr_term_global = qrcode.QRCode(border=1)
qr_term_global.add_data(GITHUB_RELEASE_URL)
qr_term_global.make(fit=True)
qr_term_global.print_ascii(invert=True)

print("\n" + "=" * 76)
print("[OPTION 2] — LOCAL WI-FI DIRECT DOWNLOAD QR CODE")
print(f"Local Link: {LOCAL_DOWNLOAD_URL}")
print("Requirement: Your mobile phone MUST be connected to the SAME Wi-Fi network as this PC.")
print("-" * 76)
qr_term_local = qrcode.QRCode(border=1)
qr_term_local.add_data(LOCAL_DOWNLOAD_URL)
qr_term_local.make(fit=True)
qr_term_local.print_ascii(invert=True)

print("\n" + "=" * 76)
print(" DIAGNOSTIC NOTES ON 'COULDN'T CONNECT' ERROR:")
print("=" * 76)
print("1. If your phone is on Mobile Data (Airtel/Jio/etc.), it CANNOT connect to 10.165.x.x.")
print("   -> Solution: Scan [OPTION 1] QR Code above to download over Mobile Data via GitHub.")
print("2. If your phone is on the same Wi-Fi, ensure Windows Firewall allows Port 5000.")
print("   -> Solution: Scan [OPTION 2] QR Code above, or open: " + LOCAL_DOWNLOAD_URL)
print("=" * 76 + "\n")
