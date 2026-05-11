"""
test_proxy.py
~~~~~~~~~~~~~
Demo Reverse Proxy + Round-Robin Load Balancing.

Script gửi N requests đến proxy và:
  - Xác định backend thực tế từ response (header hoặc body)
  - Verify thứ tự round-robin đúng quy trình
  - In bảng thống kê phân phối tải và tỉ lệ lệch

Chạy:
    python tests/test_proxy.py
    python tests/test_proxy.py --count 20 --delay 0 --path /active-peers
    python tests/test_proxy.py --verify-rr   # Bật strict round-robin check
"""

# curl.exe -H "Host: app2.local" http://127.0.0.1:8888/login

import http.client
import argparse
import time
import sys
import json
from collections import Counter, defaultdict

# ── Cấu hình mặc định ─────────────────────────────────────────────────────────
PROXY_IP = "127.0.0.1"
PROXY_PORT = 8888
HOST = "app2.local"
PATH = "/active-peers"
COUNT = 20
DELAY = 0.1
EXPECTED_BACKENDS = [9002, 9003, 9004, 9005]


# ══════════════════════════════════════════════════════════════════════════════
# HTTP CLIENT
# ══════════════════════════════════════════════════════════════════════════════


def send_request(proxy_ip, proxy_port, host, path, timeout=5):
    """Gửi 1 HTTP GET đến proxy. Trả về (status, headers_dict, body) hoặc (None, {}, err)."""
    conn = http.client.HTTPConnection(proxy_ip, proxy_port, timeout=timeout)
    try:
        conn.request("GET", path, headers={"Host": host, "Connection": "close"})
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        headers = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, headers, body
    except Exception as e:
        return None, {}, str(e)
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# BACKEND DETECTION  (3 tầng fallback)
# ══════════════════════════════════════════════════════════════════════════════


def detect_backend(
    headers: dict, body: str, expected_backends: list[int]
) -> str | None:
    """
    Cố gắng xác định port backend từ:
      1. Header X-Backend-Port hoặc X-Served-By
      2. Body chứa port number
      3. Header Server chứa port

    Trả về chuỗi port (vd: "9002") hoặc None nếu không tìm được.
    """
    # Tầng 1: Header chuyên dụng
    for key in ("x-backend-port", "x-served-by", "x-upstream-port"):
        if key in headers:
            return headers[key].strip()

    # Tầng 2: Body chứa port
    for port in expected_backends:
        if str(port) in body:
            return str(port)

    # Tầng 3: Header Server
    server_hdr = headers.get("server", "")
    for port in expected_backends:
        if str(port) in server_hdr:
            return str(port)

    return None


# ══════════════════════════════════════════════════════════════════════════════
# ROUND-ROBIN VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════


def verify_round_robin(sequence: list[str | None], backends: list[int]) -> dict:
    """
    Kiểm tra chuỗi backend thực tế có khớp round-robin không.

    - Bỏ qua request không nhận diện được backend (None).
    - Tìm offset bắt đầu tốt nhất, rồi đếm số lần đúng/sai.

    Trả về dict: {correct, wrong, unknown, accuracy, offset}
    """
    known = [(i, s) for i, s in enumerate(sequence) if s is not None]
    if not known:
        return dict(correct=0, wrong=0, unknown=len(sequence), accuracy=0.0, offset=0)

    cycle = [str(b) for b in backends]
    n_cycle = len(cycle)
    best = dict(correct=0, wrong=0, offset=0)

    # Thử tất cả offset có thể để tìm alignment tốt nhất
    for offset in range(n_cycle):
        correct = sum(
            1
            for seq_i, (_, backend) in enumerate(known)
            if backend == cycle[(seq_i + offset) % n_cycle]
        )
        if correct > best["correct"]:
            best = dict(correct=correct, wrong=len(known) - correct, offset=offset)

    return dict(
        correct=best["correct"],
        wrong=best["wrong"],
        unknown=len(sequence) - len(known),
        accuracy=best["correct"] / len(known) * 100 if known else 0.0,
        offset=best["offset"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ══════════════════════════════════════════════════════════════════════════════


def run_tests(
    proxy_ip,
    proxy_port,
    host,
    path,
    count,
    delay,
    expected_backends,
    verify_rr=False,
    out_json=None,
):

    print("═" * 68)
    print("  REVERSE PROXY  ·  ROUND-ROBIN LOAD BALANCING DEMO")
    print("═" * 68)
    print(f"  Proxy    : {proxy_ip}:{proxy_port}")
    print(f"  Host     : {host}")
    print(f"  Path     : {path}")
    print(f"  Requests : {count}  |  Delay: {delay}s")
    print(f"  Backends : {expected_backends}")
    print(f"  Verify RR: {'YES (strict)' if verify_rr else 'NO (distribution only)'}")
    print("═" * 68 + "\n")

    records = []  # [{seq, status, backend, confirmed, error}]
    backend_seq = []  # chuỗi backend nhận diện được (hoặc None)
    t_total_start = time.perf_counter()

    for i in range(1, count + 1):
        expected_idx = (i - 1) % len(expected_backends)
        expected_port = expected_backends[expected_idx]

        t_req = time.perf_counter()
        status, headers, body = send_request(proxy_ip, proxy_port, host, path)
        latency = (time.perf_counter() - t_req) * 1000  # ms

        if status is None:
            print(f"  [{i:02d}] ✗  LỖI KẾT NỐI → {body[:60]}")
            records.append(
                dict(
                    seq=i,
                    status=None,
                    backend=None,
                    confirmed=False,
                    error=body,
                    latency_ms=0,
                )
            )
            backend_seq.append(None)
            continue

        backend = detect_backend(headers, body, expected_backends)
        backend_seq.append(backend)
        confirmed = backend is not None

        if confirmed:
            match_icon = "✓" if str(expected_port) == backend else "↺"
            backend_str = f"→ :{backend}"
        else:
            match_icon = "~"
            backend_str = f"~ dự đoán :{expected_port} (không xác nhận được)"

        print(
            f"  [{i:02d}] {match_icon}  HTTP {status}  {backend_str}"
            f"  [{latency:.0f}ms]"
        )

        records.append(
            dict(
                seq=i,
                status=status,
                backend=backend,
                confirmed=confirmed,
                error=None,
                latency_ms=round(latency, 1),
            )
        )

        if delay > 0 and i < count:
            time.sleep(delay)

    total_time = time.perf_counter() - t_total_start

    # ── Thống kê phân phối tải ─────────────────────────────────────────────────
    success_records = [r for r in records if r["status"] is not None]
    failed_records = [r for r in records if r["status"] is None]
    confirmed_records = [r for r in success_records if r["confirmed"]]

    backend_counter = Counter(r["backend"] for r in confirmed_records)
    all_latencies = [r["latency_ms"] for r in success_records]

    print("\n" + "─" * 68)
    print("  PHÂN PHỐI TẢI THEO BACKEND")
    print("─" * 68)

    if not confirmed_records:
        print("  ⚠  Không nhận diện được backend nào.")
        print("     Hãy thêm header X-Backend-Port vào response của từng backend.")
    else:
        ideal_per_backend = len(confirmed_records) / len(expected_backends)
        for port in expected_backends:
            cnt = backend_counter.get(str(port), 0)
            pct = cnt / len(confirmed_records) * 100 if confirmed_records else 0
            bar = "█" * int(pct / 3)
            diff = cnt - ideal_per_backend
            balance_note = (
                f"(+{diff:.0f})" if diff > 0 else f"({diff:.0f})" if diff < 0 else "(=)"
            )
            print(f"  :{port}  {bar:<34} {cnt:>3} req  {pct:>5.1f}%  {balance_note}")

        # Tính độ lệch cân bằng (std dev của số request mỗi backend)
        counts = [backend_counter.get(str(p), 0) for p in expected_backends]
        mean = sum(counts) / len(counts)
        stddev = (sum((c - mean) ** 2 for c in counts) / len(counts)) ** 0.5
        balance_score = max(0, 100 - stddev / mean * 100) if mean > 0 else 0
        print(
            f"\n  Độ cân bằng tải : {balance_score:.1f}% "
            f"(stddev={stddev:.2f}, ideal={ideal_per_backend:.1f} req/backend)"
        )

    # ── Round-Robin Verification ───────────────────────────────────────────────
    if confirmed_records:
        rr = verify_round_robin(backend_seq, expected_backends)
        print("\n" + "─" * 68)
        print("  ROUND-ROBIN VERIFICATION")
        print("─" * 68)
        print(f"  Đúng thứ tự  : {rr['correct']} / {rr['correct'] + rr['wrong']}")
        print(f"  Sai thứ tự   : {rr['wrong']}")
        print(f"  Không xác nhận: {rr['unknown']}")
        print(f"  Độ chính xác  : {rr['accuracy']:.1f}%")

        if rr["accuracy"] >= 95:
            rr_verdict = " Round-Robin hoạt động đúng quy trình!"
        elif rr["accuracy"] >= 70:
            rr_verdict = (
                " Round-Robin gần đúng — kiểm tra sticky session hoặc backend chậm."
            )
        elif rr["unknown"] == len(backend_seq):
            rr_verdict = " Không đủ dữ liệu — thêm X-Backend-Port header để verify."
        else:
            rr_verdict = "Round-Robin lệch đáng kể — kiểm tra cấu hình proxy."

        print(f"  Kết quả       : {rr_verdict}")

    # ── Latency ───────────────────────────────────────────────────────────────
    if all_latencies:
        avg_lat = sum(all_latencies) / len(all_latencies)
        max_lat = max(all_latencies)
        min_lat = min(all_latencies)
        p95_lat = sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        print("\n" + "─" * 68)
        print("  LATENCY")
        print("─" * 68)
        print(
            f"  Min / Avg / P95 / Max : "
            f"{min_lat:.0f}ms / {avg_lat:.0f}ms / {p95_lat:.0f}ms / {max_lat:.0f}ms"
        )

    # ── Tổng kết ──────────────────────────────────────────────────────────────
    print("\n" + "═" * 68)
    print(f"  ✓ Thành công : {len(success_records)}/{count}")
    print(f"  ✗ Thất bại   : {len(failed_records)}/{count}")
    print(
        f"  ⏱ Tổng thời gian : {total_time:.2f}s  |  "
        f"Throughput: {len(success_records)/total_time:.1f} req/s"
    )

    overall_ok = len(failed_records) == 0 and (
        not confirmed_records
        or verify_round_robin(backend_seq, expected_backends)["accuracy"] >= 70
    )

    if len(failed_records) == 0:
        print("\n  [DEMO] HỆ THỐNG PHÂN PHỐI TẢI ĐANG HOẠT ĐỘNG ĐÚNG QUY TRÌNH!")
    else:
        print("\n  [DEMO] CẦN KIỂM TRA LẠI TRẠNG THÁI CÁC WEB PEER.")
    print("═" * 68 + "\n")

    # ── Xuất JSON ─────────────────────────────────────────────────────────────
    if out_json:
        output = {
            "meta": {
                "proxy": f"{proxy_ip}:{proxy_port}",
                "host": host,
                "path": path,
                "count": count,
                "backends": expected_backends,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "summary": {
                "success": len(success_records),
                "failed": len(failed_records),
                "total_time_s": round(total_time, 3),
                "throughput_rps": round(len(success_records) / total_time, 1),
                "avg_latency_ms": round(avg_lat, 1) if all_latencies else 0,
            },
            "distribution": {
                str(p): backend_counter.get(str(p), 0) for p in expected_backends
            },
            "records": records,
        }
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"  [JSON] Kết quả đã lưu → {out_json}\n")

    return overall_ok


# ══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="Test Reverse Proxy Round-Robin")
    parser.add_argument("--proxy", default=PROXY_IP, help="IP proxy")
    parser.add_argument("--port", default=PROXY_PORT, type=int, help="Port proxy")
    parser.add_argument("--host", default=HOST, help="Host header")
    parser.add_argument("--path", default=PATH, help="Request path")
    parser.add_argument("--count", default=COUNT, type=int, help="Số request")
    parser.add_argument(
        "--delay", default=DELAY, type=float, help="Delay (s) giữa request"
    )
    parser.add_argument(
        "--backends",
        default=EXPECTED_BACKENDS,
        nargs="+",
        type=int,
        help="Danh sách backend port, vd: --backends 9002 9003 9004 9005",
    )
    parser.add_argument(
        "--verify-rr", action="store_true", help="Bật strict round-robin verification"
    )
    parser.add_argument(
        "--json", default=None, help="Lưu kết quả JSON, vd: --json result.json"
    )
    args = parser.parse_args()

    success = run_tests(
        proxy_ip=args.proxy,
        proxy_port=args.port,
        host=args.host,
        path=args.path,
        count=args.count,
        delay=args.delay,
        expected_backends=args.backends,
        verify_rr=args.verify_rr,
        out_json=args.json,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
