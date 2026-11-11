"""
Wait until both Backend (port 8000) and Frontend (port 4200) are fully running.
"""
import sys
import time
import urllib.request

def check_url(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NovelTL-HealthChecker/1.0"})
        with urllib.request.urlopen(req, timeout=1) as resp:
            return resp.status in (200, 304)
    except Exception:
        return False

def main():
    be_url = "http://localhost:8000/api/health"
    fe_url = "http://localhost:4200"

    be_ready = False
    fe_ready = False
    max_wait_seconds = 60

    print("Menunggu Backend & Frontend selesai inisialisasi...")

    for elapsed in range(1, max_wait_seconds + 1):
        if not be_ready and check_url(be_url):
            be_ready = True
            print("  [OK] Backend (FastAPI - Port 8000) SIAP!")

        if not fe_ready and check_url(fe_url):
            fe_ready = True
            print("  [OK] Frontend (Angular - Port 4200) SIAP!")

        if be_ready and fe_ready:
            print("  >> Keduanya sudah AKTIF! Membuka browser...")
            sys.exit(0)

        time.sleep(1)

    print("\n[PERINGATAN] Timeout 60 detik tercapai, mencoba membuka browser...")
    sys.exit(0)

if __name__ == "__main__":
    main()

