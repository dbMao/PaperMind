# -*- coding: utf-8 -*-
import subprocess, sys, time, webbrowser, platform
from urllib.request import Request, urlopen
from pathlib import Path

ROOT = Path(__file__).parent

def wait_for(url, timeout=60):
    start = time.time()
    delay = 0.5          # 初始间隔 0.5 秒
    while time.time() - start < timeout:
        try:
            urlopen(Request(url), timeout=2)
            return True
        except Exception:
            time.sleep(min(delay, 2))   # 最大不超过 2 秒
            delay *= 1.5                # 指数退避
    return False

def kill_port(port):
    """Kill processes on given port"""
    try:
        if platform.system() == "Windows":
            for line in subprocess.run(
                f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True
            ).stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[-1].isdigit():
                    subprocess.run(f"taskkill /F /PID {parts[-1]}", shell=True,
                                   capture_output=True)
        else:
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True,
                           capture_output=True)
    except Exception:
        pass

def main():
    print("PaperMind starting...")
    print("Cleaning up old processes...")
    kill_port(8000)
    kill_port(3000)

    backend = subprocess.Popen(
        f'cmd /c "cd /d {ROOT / "backend"} && venv\\Scripts\\activate && uvicorn app.main:app --port 8000"',
        shell=True, creationflags=0,
    )

    print("Waiting for backend...")
    if not wait_for("http://127.0.0.1:8000/"):
        print("Backend timeout!")
        backend.terminate()
        sys.exit(1)
    print("Backend ready")

    frontend = subprocess.Popen(
        f'cmd /c "cd /d {ROOT / "frontend"} && npm run dev"',
        shell=True, creationflags=0,
    )

    print("Waiting for frontend...")
    if not wait_for("http://localhost:3000/"):
        print("Frontend timeout!")
        frontend.terminate(); backend.terminate()
        sys.exit(1)
    print("Frontend ready")

    webbrowser.open("http://localhost:3000")
    print("PaperMind running. Ctrl+C to stop.")

    try:
        backend.wait(); frontend.wait()
    except KeyboardInterrupt:
        print("Stopping...")
        frontend.terminate(); backend.terminate()
        print("Stopped.")

if __name__ == "__main__":
    main()
