"""
NutriRisk AI — Native Desktop App Launcher
Launches the Flask application inside a standalone, borderless native application window.
"""
import os
import sys
import time
import socket
import subprocess
import webbrowser

PORT = 5000
URL = f"http://127.0.0.1:{PORT}"

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_backend():
    if is_port_in_use(PORT):
        print(f"[*] NutriRisk AI server is already running on port {PORT}.")
        return None
    
    print("[*] Starting NutriRisk AI backend server...")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Wait for server to bind
    for _ in range(15):
        time.sleep(0.5)
        if is_port_in_use(PORT):
            print("[OK] Server started and listening.")
            return proc
    return proc

def launch_app_window():
    print(f"[*] Opening NutriRisk AI in native App Mode window: {URL}")
    
    # Check for Edge (standard on Windows)
    edge_paths = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        "msedge"
    ]
    for p in edge_paths:
        try:
            subprocess.Popen([p, f"--app={URL}", "--window-size=1280,820"])
            print("[OK] Native Edge App Window launched.")
            return
        except Exception:
            continue

    # Check for Chrome
    chrome_paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        "chrome"
    ]
    for p in chrome_paths:
        try:
            subprocess.Popen([p, f"--app={URL}", "--window-size=1280,820"])
            print("[OK] Native Chrome App Window launched.")
            return
        except Exception:
            continue

    # Fallback to default browser
    webbrowser.open(URL)
    print("[OK] Opened in default web browser.")

if __name__ == "__main__":
    print("=" * 65)
    print("NutriRisk AI — Launching Native Desktop App")
    print("=" * 65)
    server_proc = start_backend()
    launch_app_window()
    print("[✓] App launched. Close the window when finished.")
