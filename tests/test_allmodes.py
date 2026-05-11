"""
test_3modes.py
--------------
Demo Non-blocking Benchmark: So sánh 3 server mode (threading / callback / coroutine).

Script tự động:
  1. Đổi mode_async trong daemon/backend.py
  2. Khởi động lại server
  3. Bắn N requests đồng thời (asyncio client — chỉ server thay đổi)
  4. In bảng tổng kết so sánh + xuất JSON để dashboard đọc

Chạy: python tests/test_3modes.py [--scales 100 500 1000] [--port 9000] [--json result.json]
"""

import asyncio
import time
import socket
import subprocess
import re
import sys
import os
import argparse
import json

# ── Cấu hình mặc định ─────────────────────────────────────────────────────────
TARGET_IP = "127.0.0.1"
TARGET_PORT = 9000
SCALES = [100, 500, 1000, 2000]
MODES = ["threading", "callback", "coroutine"]
TIMEOUT = 8.0
CONCURRENCY = 500  # Semaphore — tránh lỗi "Too many open files"

BACKEND_FILE = os.path.join(os.path.dirname(__file__), "..", "daemon", "backend.py")
SERVER_CMD = [
    sys.executable,
    "start_tracker.py",
    "--server-ip",
    TARGET_IP,
    "--server-port",
    str(TARGET_PORT),
]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def set_mode(mode: str) -> bool:
    """Ghi mode_async vào daemon/backend.py bằng regex. Trả về True nếu thành công."""
    path = os.path.abspath(BACKEND_FILE)
    if not os.path.exists(path):
        print(f"  [!] Không tìm thấy {path} — bỏ qua bước đổi mode.")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content, count = re.subn(
        r'^(mode_async\s*=\s*)["\'].*?["\']',
        rf'\g<1>"{mode}"',
        content,
        flags=re.MULTILINE,
    )

    if count == 0:
        print(f"  [!] Không tìm thấy dòng 'mode_async = ...' trong {path}.")
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    # Xác nhận đã ghi đúng
    with open(path, "r", encoding="utf-8") as f:
        verify = f.read()
    if f'mode_async = "{mode}"' in verify:
        print(f"  [✓] mode_async = '{mode}' đã được ghi vào backend.py")
        return True
    else:
        print(f"  [!] Ghi file thất bại!")
        return False


def wait_for_server(ip: str, port: int, timeout: float = 12.0) -> bool:
    """Chờ đến khi server chấp nhận kết nối TCP."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection((ip, port), timeout=1)
            s.close()
            return True
        except OSError:
            time.sleep(0.3)
    return False


# ══════════════════════════════════════════════════════════════════════════════
# ASYNC CLIENT  (client luôn dùng asyncio — chỉ server mode thay đổi)
# ══════════════════════════════════════════════════════════════════════════════


async def send_one(
    client_id: int, n: int, sem: asyncio.Semaphore, ip: str, port: int
) -> bool:
    """Gửi 1 HTTP GET /login, trả về True nếu server phản hồi (bất kỳ HTTP status)."""
    async with sem:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=TIMEOUT
            )
            writer.write(
                f"GET /login HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n".encode(
                    "utf-8"
                )
            )
            await writer.drain()
            response = await asyncio.wait_for(reader.read(512), timeout=TIMEOUT)
            writer.close()
            await writer.wait_closed()

            # "Thành công" = server TRẢ LỜI bất kỳ HTTP response hợp lệ
            # (200, 302, 404 đều OK — chứng tỏ server không bị treo)
            got_response = response.startswith(b"HTTP/")
            if n <= 100:
                status_line = response.decode("utf-8", errors="replace").splitlines()[0]
                icon = "✓" if got_response else "✗"
                print(f"    [{icon}] client {client_id:04d} → {status_line}")
            return got_response

        except asyncio.TimeoutError:
            if n <= 100:
                print(f"    [✗] client {client_id:04d} → TIMEOUT ({TIMEOUT}s)")
            return False
        except Exception as e:
            if n <= 100:
                print(f"    [✗] client {client_id:04d} → LỖI: {e}")
            return False


async def run_benchmark(n: int, ip: str, port: int) -> tuple[int, float]:
    """Bắn n requests đồng thời. Trả về (số thành công, thời gian)."""
    sem = asyncio.Semaphore(CONCURRENCY)
    t0 = time.perf_counter()
    results = await asyncio.gather(*[send_one(i, n, sem, ip, port) for i in range(n)])
    elapsed = time.perf_counter() - t0
    return sum(results), elapsed


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════


def main(args):
    ip = args.ip
    port = args.port
    scales = args.scales

    print("\n" + "═" * 66)
    print("  NON-BLOCKING BENCHMARK  ·  AsynapRous Chat")
    print(f"  Target  : {ip}:{port}")
    print(f"  Modes   : {MODES}")
    print(f"  Scales  : {scales} concurrent requests")
    print(f"  Client  : asyncio (non-blocking) — chỉ server mode thay đổi")
    print("═" * 66)

    all_results: list[dict] = []
    proc = None

    for mode in MODES:
        print(f"\n{'═'*66}")
        print(f"  ▶  SERVER MODE: {mode.upper()}")
        print(f"{'═'*66}")

        # 1. Đổi mode trong backend.py
        ok = set_mode(mode)
        if not ok and os.path.exists(os.path.abspath(BACKEND_FILE)):
            print("  [!] Không đổi được mode — kết quả có thể không chính xác.")

        # 2. Restart server
        if proc:
            proc.terminate()
            proc.wait(timeout=3)
            time.sleep(0.5)

        cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cmd = [
            sys.executable,
            "start_tracker.py",
            "--server-ip",
            ip,
            "--server-port",
            str(port),
        ]

        print(f"  [*] Khởi động server ({mode})...")
        proc = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        if not wait_for_server(ip, port, timeout=12):
            print(f"  [!] Server không phản hồi sau 12s — bỏ qua mode '{mode}'.")
            continue

        print(f"  [✓] Server sẵn sàng!\n")
        time.sleep(0.3)  # buffer nhỏ cho server ổn định hoàn toàn

        # 3. Benchmark từng mức tải
        mode_rows = []
        for n in scales:
            print(f"  → Bắn {n} requests đồng thời...", end="", flush=True)
            ok_count, elapsed = asyncio.run(run_benchmark(n, ip, port))
            drop = n - ok_count
            rate = ok_count / elapsed if elapsed > 0 else 0
            drop_pct = drop / n * 100

            row = dict(
                mode=mode,
                n=n,
                ok=ok_count,
                drop=drop,
                elapsed=round(elapsed, 3),
                rate=round(rate, 1),
            )
            mode_rows.append(row)
            all_results.append(row)

            status_icon = "✓" if drop == 0 else "⚠"
            print(
                f"\r  {status_icon} N={n:>5} | OK={ok_count:>5}/{n:<5} "
                f"| Drop={drop:>4} ({drop_pct:.0f}%) "
                f"| {elapsed:.2f}s | {rate:.1f} req/s"
            )

        time.sleep(0.3)

    if proc:
        proc.terminate()
        print("\n  [*] Đã dừng server.")

    # ── Bảng tổng kết ─────────────────────────────────────────────────────────
    print("\n" + "═" * 66)
    print("  TỔNG KẾT: SO SÁNH 3 SERVER MODE (client: asyncio)")
    print("═" * 66)
    print(
        f"  {'Mode':<12} | {'N':>5} | {'OK':>11} | {'Drop%':>6} | {'Time':>7} | {'req/s':>8}"
    )
    print(f"  {'-'*12}-+-{'-'*5}-+-{'-'*11}-+-{'-'*6}-+-{'-'*7}-+-{'-'*8}")

    prev_mode = None
    for r in all_results:
        if prev_mode and prev_mode != r["mode"]:
            print(f"  {'-'*12}-+-{'-'*5}-+-{'-'*11}-+-{'-'*6}-+-{'-'*7}-+-{'-'*8}")
        drop_pct = r["drop"] / r["n"] * 100
        print(
            f"  {r['mode']:<12} | {r['n']:>5} | "
            f"{r['ok']:>5}/{r['n']:<5} | {drop_pct:>5.1f}% "
            f"| {r['elapsed']:>5.2f}s | {r['rate']:>7.1f}"
        )
        prev_mode = r["mode"]

    print("═" * 66)

    # Tìm mode tốt nhất (tổng req/s cao nhất)
    from collections import defaultdict

    mode_total_rate = defaultdict(float)
    mode_total_drop = defaultdict(int)
    for r in all_results:
        mode_total_rate[r["mode"]] += r["rate"]
        mode_total_drop[r["mode"]] += r["drop"]

    best_mode = max(mode_total_rate, key=mode_total_rate.get)
    total_drop = sum(r["drop"] for r in all_results)
    total_req = sum(r["n"] for r in all_results)

    print(f"\n  Mode hiệu năng cao nhất : {best_mode.upper()}")
    print(
        f"  Tổng drop rate          : {total_drop}/{total_req} "
        f"({total_drop/total_req*100:.1f}%)"
    )

    if total_drop == 0:
        print("\n  [RESULT] SUCCESS — Server xử lý hoàn toàn NON-BLOCKING!")
        print("           Hệ thống duy trì kết nối ổn định dưới áp lực cao.")
    else:
        print(f"\n  [RESULT] WARNING — {total_drop} request thất bại.")
        print("           Kiểm tra giới hạn OS (ulimit) hoặc Backend bottleneck.")

    # ── Xuất JSON (cho dashboard) ──────────────────────────────────────────────
    if args.json:
        out = {
            "meta": {
                "target": f"{ip}:{port}",
                "modes": MODES,
                "scales": scales,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "results": all_results,
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"\n  [JSON] Kết quả đã lưu → {args.json}")

    print()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Non-blocking benchmark — 3 server modes"
    )
    parser.add_argument("--ip", default=TARGET_IP, help="Server IP")
    parser.add_argument("--port", default=TARGET_PORT, type=int, help="Server port")
    parser.add_argument(
        "--scales",
        default=SCALES,
        nargs="+",
        type=int,
        help="Danh sách mức tải, vd: --scales 100 500 1000",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Xuất kết quả JSON cho dashboard, vd: --json result.json",
    )
    main(parser.parse_args())
