import os
import sys
import subprocess
import signal
import time
from pathlib import Path
from typing import List, NoReturn


def get_python_executable(root_dir: Path) -> str:
    venv_python_win = root_dir / ".venv" / "Scripts" / "python.exe"
    venv_python_posix = root_dir / ".venv" / "bin" / "python"
    
    if venv_python_win.exists():
        return str(venv_python_win)
    elif venv_python_posix.exists():
        return str(venv_python_posix)
    return sys.executable


def kill_stale_ports(ports: List[int]) -> None:
    if os.name != "nt":
        return
    for port in ports:
        try:
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"'
            subprocess.run(cmd, shell=True, capture_output=True)
        except subprocess.SubprocessError:
            pass


def main() -> None:
    root_dir = Path(__file__).resolve().parent
    python_exec = get_python_executable(root_dir)
    kill_stale_ports([3000, 8000, 8001])
    
    backend_cmd: List[str] = [
        python_exec,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--reload",
        "--port",
        "8001"
    ]
    
    npm_cmd: str = "npm.cmd" if os.name == "nt" else "npm"
    frontend_cmd: List[str] = [
        npm_cmd,
        "run",
        "dev",
        "--prefix",
        "frontend"
    ]
    
    processes: List[subprocess.Popen] = []
    
    print("🚀 Starting CongApp Development Servers...")
    print(f"🔹 Backend:  http://localhost:8001 (FastAPI)")
    print(f"🔹 Frontend: http://localhost:3000 (Next.js)")
    print("Press Ctrl+C to stop all servers.\n")
    
    try:
        backend_proc = subprocess.Popen(backend_cmd, cwd=root_dir)
        processes.append(backend_proc)
        
        frontend_proc = subprocess.Popen(frontend_cmd, cwd=root_dir)
        processes.append(frontend_proc)
        
        while True:
            for proc in processes:
                poll_code = proc.poll()
                if poll_code is not None:
                    print(f"⚠️ Process {proc.pid} exited with code {poll_code}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping all servers...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        
        time.sleep(1)
        for proc in processes:
            if proc.poll() is None:
                proc.kill()
        print("✅ All servers stopped successfully.")


if __name__ == "__main__":
    main()
