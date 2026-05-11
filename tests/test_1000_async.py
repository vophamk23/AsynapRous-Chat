"""
test_1000_async.py
------------------
Stress Test (Non-blocking): Bắn đồng thời hàng ngàn requests lên Server.

Mục tiêu:
  - Chứng minh server không bị "treo" (block) khi có nhiều kết nối.
  - Đo thông lượng (req/s) và drop rate ở nhiều mức tải khác nhau.

Chú ý:
  - "Thành công" = server TRẢ LỜI bất kỳ HTTP response hợp lệ (bất kể status code).
  - 404 / 302 đều tính là server phản hồi — KHÔNG phải lỗi tải.
  - Lỗi thật sự: Timeout, Connection refused, hoặc không nhận được HTTP response.

Chạy:
  python tests/test_1000_async.py
  python tests/test_1000_async.py --scales 100 500 1000 3000 5000 --port 9000
  python tests/test_1000_async.py --json stress_result.json
"""

import asyncio
import time
import sys
import argparse
import json

# ── Cấu hình mặc định ─────────────────────────────────────────────────────────
TARGET_IP = "127.0.0.1"
TARGET_PORT = 9000
SCALES = [100, 500, 1000, 2000, 3000, 5000]
TIMEOUT = 5.0
CONCURRENCY = 1000  # Semaphore — tránh lỗi OS "Too many open files"


# ══════════════════════════════════════════════════════════════════════════════
# ASYNC CLIENT
# ══════════════════════════════════════════════════════════════════════════════


async def send_request(
    client_id: int, total_n: int, sem: asyncio.Semaphore, ip: str, port: int
) -> bool:
    """
    Gửi 1 HTTP GET /login.
    Trả về True nếu server phản hồi bất kỳ HTTP response hợp lệ.
    Trả về False nếu timeout, connection refused, hoặc không có HTTP response.
    """
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

            # Thành công = nhận được HTTP response hợp lệ (bất kể 200/302/404/500)
            is_http_response = response.startswith(b"HTTP/")

            if total_n <= 100:
                if response:
                    status_line = response.decode(
                        "utf-8", errors="replace"
                    ).splitlines()[0]
                    icon = "✓" if is_http_response else "?"
                    print(f"  [{icon}] Client {client_id:04d} → {status_line}")
                else:
                    print(f"  [?] Client {client_id:04d} → (empty response)")

            return is_http_response

        except asyncio.TimeoutError:
            if total_n <= 100:
                print(f"  [✗] Client {client_id:04d} → TIMEOUT ({TIMEOUT}s)")
            return False
        except ConnectionRefusedError:
            if total_n <= 100:
                print(f"  [✗] Client {client_id:04d} → Connection refused")
            return False
        except Exception as e:
            if total_n <= 100:
                print(f"  [✗] Client {client_id:04d} → LỖI: {type(e).__name__}: {e}")
            return False


async def run_benchmark(n: int, ip: str, port: int) -> tuple[int, float]:
    """Bắn n requests đồng thời. Trả về (số thành công, thời gian)."""
    sem = asyncio.Semaphore(CONCURRENCY)
    t0 = time.perf_counter()
    results = await asyncio.gather(
        *[send_request(i, n, sem, ip, port) for i in range(n)]
    )
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
    print("  STRESS TEST  ·  NON-BLOCKING ASYNC CLIENT")
    print(f"  Target  : http://{ip}:{port}/login")
    print(f"  Scales  : {scales} concurrent requests")
    print(f"  Limit   : {CONCURRENCY} concurrent sockets (Semaphore)")
    print(f"  Timeout : {TIMEOUT}s per request")
    print("═" * 66 + "\n")

    summary = []

    for n in scales:
        print(f"  → Bắn {n} requests đồng thời...", end="", flush=True)
        ok, elapsed = asyncio.run(run_benchmark(n, ip, port))

        drop = n - ok
        rate = ok / elapsed if elapsed > 0 else 0
        drop_pct = drop / n * 100

        summary.append(
            dict(n=n, ok=ok, drop=drop, elapsed=round(elapsed, 3), rate=round(rate, 1))
        )

        status_icon = "✓" if drop == 0 else ("⚠" if drop_pct < 5 else "✗")
        print(
            f"\r  {status_icon} N={n:>5}  |  OK={ok:>5}/{n:<5}  "
            f"|  Drop={drop:>4} ({drop_pct:.1f}%)  "
            f"|  {elapsed:.2f}s  |  {rate:.1f} req/s"
        )

    # ── Bảng tổng kết ─────────────────────────────────────────────────────────
    print("\n" + "═" * 66)
    print("  BẢNG THỐNG KÊ CHI TIẾT")
    print("═" * 66)
    print(
        f"  {'N Requests':>10} | {'Thành công':>11} | {'Drop':>10} | {'Thời gian':>10} | {'req/s':>8}"
    )
    print(f"  {'-'*10}-+-{'-'*11}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}")

    for r in summary:
        drop_pct = r["drop"] / r["n"] * 100
        print(
            f"  {r['n']:>10} | {r['ok']:>5}/{r['n']:<5} "
            f"| {r['drop']:>4} ({drop_pct:.1f}%)  "
            f"| {r['elapsed']:>8.2f}s | {r['rate']:>7.1f}"
        )

    print("═" * 66)

    total_req = sum(r["n"] for r in summary)
    total_ok = sum(r["ok"] for r in summary)
    total_drop = sum(r["drop"] for r in summary)

    print(f"\n  TỔNG CỘNG  : {total_ok}/{total_req} requests thành công")
    print(f"  DROP RATE  : {total_drop/total_req*100:.1f}%")

    if total_drop == 0:
        print("\n  [RESULT] SUCCESS — Server xử lý hoàn toàn NON-BLOCKING!")
        print("           Hệ thống duy trì kết nối ổn định dưới áp lực cao.")
    elif total_drop / total_req < 0.05:
        print(f"\n  [RESULT] NEAR-SUCCESS — Drop rate < 5%, hệ thống ổn định.")
    else:
        print(f"\n  [RESULT] WARNING — Drop rate {total_drop/total_req*100:.1f}%.")
        print("           Kiểm tra ulimit (file descriptors) hoặc Backend bottleneck.")

    # ── Xuất JSON ─────────────────────────────────────────────────────────────
    if args.json:
        output = {
            "meta": {
                "target": f"{ip}:{port}",
                "scales": scales,
                "concurrency_limit": CONCURRENCY,
                "timeout_s": TIMEOUT,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "results": summary,
            "totals": {
                "total_req": total_req,
                "total_ok": total_ok,
                "total_drop": total_drop,
                "drop_rate_pct": round(total_drop / total_req * 100, 2),
            },
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n  [JSON] Kết quả đã lưu → {args.json}")

    print()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stress Test — Non-blocking async client"
    )
    parser.add_argument("--ip", default=TARGET_IP, help="Server IP")
    parser.add_argument("--port", default=TARGET_PORT, type=int, help="Server port")
    parser.add_argument(
        "--scales",
        default=SCALES,
        nargs="+",
        type=int,
        help="Danh sách mức tải, vd: --scales 100 500 1000 5000",
    )
    parser.add_argument(
        "--json", default=None, help="Xuất kết quả JSON, vd: --json result.json"
    )
    main(parser.parse_args())
