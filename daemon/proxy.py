#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.proxy
~~~~~~~~~~~~~~~~~

Module này hiện thực proxy server đơn giản bằng socket và threading.
Proxy nhận request từ browser/client, xác định backend đích dựa theo hostname,
chuyển tiếp request đến backend tương ứng và trả kết quả về cho client.
Load balancing theo cơ chế Round-Robin khi có nhiều backend cho cùng 1 hostname.

Thư viện sử dụng:
-----------------
- socket    : giao tiếp mạng TCP/IP
- threading : xử lý nhiều client song song
- response  : xây dựng HTTP response
- httpadapter: lớp xử lý HTTP request
- CaseInsensitiveDict: dict không phân biệt hoa thường
"""

import socket
import threading
from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict

# Bảng ánh xạ hostname → backend (IP, port).
# Proxy dựa vào bảng này để quyết định chuyển tiếp request đến đâu.
PROXY_PASS = {
    "192.168.56.103:8080": ("192.168.56.103", 9000),
    "app1.local": ("127.0.0.1", 9001),
    "app2.local": [("127.0.0.1", 9002), ("127.0.0.1", 9003)],  # ví dụ load balancing
}

# Bộ đếm Round-Robin cho từng hostname (dùng khi có nhiều backend)
rr_counter = {}
rr_lock = threading.Lock()  # Khóa để bảo đảm thread-safe khi cập nhật bộ đếm


# Vận hành chuyển tiếp nguyên bản Request tới máy chủ đích và tiếp nhận Response trả về
def forward_request(host, port, request):
    """
    Chuyển tiếp một HTTP request đến backend server và nhận phản hồi.

    :params host    (str)  : địa chỉ IP của backend.
    :params port    (int)  : cổng của backend.
    :params request (str)  : chuỗi HTTP request cần chuyển tiếp.

    :rtype bytes: raw HTTP response từ backend. Nếu kết nối thất bại, trả về 404 Not Found.
    """

    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        backend.connect((host, port))  # Kết nối đến backend
        backend.sendall(request.encode())  # Gửi toàn bộ request
        response = b""
        while True:
            chunk = backend.recv(4096)  # Đọc response từng mảnh 4KB
            if not chunk:
                break
            response += chunk
        return response
    except socket.error as e:
        print("Socket error: {}".format(e))
        # Backend không phản hồi → trả về 404
        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode("utf-8")
    finally:
        backend.close()  # Luôn đóng socket dù thành công hay thất bại


# Giải mã và thực thi chính sách định tuyến (Routing) sang cụm máy chủ Backend khả dụng
def resolve_routing_policy(hostname, routes):
    """
    Xử lý chính sách định tuyến – xác định backend đích để chuyển tiếp request.

    Hỗ trợ cả backend đơn lẻ lẫn load balancing Round-Robin khi có nhiều backend.

    :params hostname (str) : hostname lấy từ Host header của request.
    :params routes   (dict): bảng cấu hình proxy, ánh xạ hostname → (backend_list, policy).
    """

    proxy_map, policy = routes.get(
        hostname.split(":")[0], ("127.0.0.1:9000", "round-robin")
    )

    proxy_host = ""
    proxy_port = "9000"
    if isinstance(proxy_map, list):
        if len(proxy_map) == 0:
            # Danh sách backend rỗng – dùng host mặc định
            print("[Proxy] Emtpy resolved routing of hostname {}".format(hostname))
            print("Empty proxy_map result")
            proxy_host = "127.0.0.1"
            proxy_port = "9000"
        elif len(proxy_map) == 1:
            # Chỉ có 1 backend – chọn trực tiếp
            proxy_host, proxy_port = proxy_map[0].split(":", 2)
        elif len(proxy_map) > 1:
            # Nhiều backend – áp dụng chính sách Round-Robin
            if policy == "round-robin":
                with rr_lock:  # Khóa để tránh race condition giữa các thread
                    index = rr_counter.get(hostname, 0)
                    rr_counter[hostname] = (index + 1) % len(proxy_map)
                    backend = proxy_map[index]
                proxy_host, proxy_port = backend.split(":", 2)
    else:
        # Backend là đơn lẻ (không phải list)
        print("[Proxy] resolve route of hostname {} is a singulair to".format(hostname))
        proxy_host, proxy_port = proxy_map.split(":", 2)

    return proxy_host, proxy_port


# Tiếp nhận luồng xử lý đơn lẻ, điều hướng theo vòng lặp và kết chuyển phản hồi tới Client
def handle_client(ip, port, conn, addr, routes):
    """
    Xử lý một kết nối client:
    - Đọc request từ client
    - Xác định backend đích dựa trên Host header
    - Chuyển tiếp request đến backend tương ứng
    - Gửi response từ backend về cho client

    :params ip     (str)          : địa chỉ IP của proxy server.
    :params port   (int)          : cổng của proxy server.
    :params conn   (socket.socket): socket kết nối với client.
    :params addr   (tuple)        : địa chỉ client (IP, port).
    :params routes (dict)         : bảng cấu hình proxy.
    """

    request = conn.recv(1024).decode()

    # Lấy giá trị Host header từ request
    for line in request.splitlines():
        if line.lower().startswith("host:"):
            hostname = line.split(":", 1)[1].strip()

    print("[Proxy] {} at Host: {}".format(addr, hostname))

    # Xác định backend đích và chuyển port sang kiểu int
    resolved_host, resolved_port = resolve_routing_policy(hostname, routes)
    try:
        resolved_port = int(resolved_port)
    except ValueError:
        print("Not a valid integer")

    if resolved_host:
        # Tìm thấy backend → chuyển tiếp request
        print(
            "[Proxy] Host name {} is forwarded to {}:{}".format(
                hostname, resolved_host, resolved_port
            )
        )
        response = forward_request(resolved_host, resolved_port, request)
    else:
        # Không tìm thấy backend → trả 404
        response = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode("utf-8")
    conn.sendall(response)
    conn.close()


# Khởi chạy vòng lặp Socket, phân bổ đa luồng độc lập tiếp đón từng phiên Client truy xuất
def run_proxy(ip, port, routes):
    """
    Khởi động proxy server và lắng nghe kết nối từ client.
    Mỗi client được xử lý trong 1 thread riêng (non-blocking).

    :params ip     (str) : địa chỉ IP để bind proxy.
    :params port   (int) : cổng lắng nghe.
    :params routes (dict): bảng cấu hình proxy (hostname → backend).
    """

    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        proxy.bind((ip, port))
        proxy.listen(50)  # Tối đa 50 kết nối chờ
        print("[Proxy] Listening on IP {} port {}".format(ip, port))
        while True:
            conn, addr = proxy.accept()  # Chặn đợi client

            # NON-BLOCKING: Tạo thread riêng cho mỗi client
            # Main thread tiếp tục nhận kết nối mới không bị block
            client_thread = threading.Thread(
                target=handle_client, args=(ip, port, conn, addr, routes)
            )
            client_thread.start()
    except socket.error as e:
        print("Socket error: {}".format(e))


# Phương thức cửa ngõ thiết lập tham số khởi chạy hệ thống luân chuyển tải (Reverse Proxy)
def create_proxy(ip, port, routes):
    """
    Điểm vào để khởi động proxy server.

    :params ip     (str) : địa chỉ IP để bind proxy.
    :params port   (int) : cổng lắng nghe.
    :params routes (dict): bảng cấu hình proxy.
    """

    run_proxy(ip, port, routes)
