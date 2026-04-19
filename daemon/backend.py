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
daemon.backend
~~~~~~~~~~~~~~~~~

Module này cung cấp backend server để xử lý các kết nối HTTP từ client.
Sử dụng socket và threading để xử lý nhiều kết nối cùng lúc (non-blocking).
Mỗi kết nối được giao cho HttpAdapter để xử lý request và trả về response.

Thư viện sử dụng:
-----------------
- socket   : giao tiếp mạng TCP/IP
- threading: xử lý nhiều kết nối song song (mỗi client một thread riêng)
- response : xây dựng HTTP response
- httpadapter: lớp xử lý HTTP request
- CaseInsensitiveDict: dict không phân biệt hoa thường cho headers/routes

Lưu ý:
------
- Mỗi client kết nối vào sẽ được tạo một thread daemon riêng.
- Lỗi socket được in ra console, chưa có cơ chế retry.
- Toàn bộ logic xử lý request được ủy quyền cho lớp HttpAdapter.

Ví dụ sử dụng:
--------------
>>> create_backend("127.0.0.1", 9000, routes={})
"""

import socket
import threading
import argparse

from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict


# Phân luồng xử lý kết nối HTTP độc lập bằng cách ủy quyền cho bộ chuyển đổi (Adapter) trung gian
def handle_client(ip, port, conn, addr, routes):
    """
    Xử lý một kết nối client cụ thể.
    Tạo một đối tượng HttpAdapter và giao toàn bộ việc
    đọc request / xử lý / gửi response cho nó.

    :param ip    (str)           : địa chỉ IP của server.
    :param port  (int)           : cổng server đang lắng nghe.
    :param conn  (socket.socket) : socket kết nối với client.
    :param addr  (tuple)         : địa chỉ client (IP, port).
    :param routes (dict)         : dict ánh xạ (method, path) → hàm xử lý.
    """
    daemon = HttpAdapter(ip, port, conn, addr, routes)

    # Giao việc xử lý kết nối cho HttpAdapter
    daemon.handle_client(conn, addr, routes)


# Vận hành Socket liên tục lắng nghe và điều phối đa luồng (Multi-threading) để phục vụ đồng thời các kết nối
def run_backend(ip, port, routes):
    """
    Khởi động backend server, lắng nghe kết nối đến từ client.
    Mỗi kết nối được xử lý trong một thread riêng (multi-threading).
    Đây là cơ chế Non-blocking chính của hệ thống.

    :param ip     (str) : địa chỉ IP để bind server.
    :param port   (int) : cổng để lắng nghe.
    :param routes (dict): dict ánh xạ (method, path) → hàm xử lý.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server.bind((ip, port))
        server.listen(50)  # Tối đa 50 kết nối chờ trong hàng đợi
        print("[Backend] Listening on port {}".format(port))
        if routes != {}:
            print("[Backend] route settings {}".format(routes))

        while True:
            conn, addr = server.accept()  # Chặn đợi client kết nối

            # NON-BLOCKING: Tạo thread mới cho mỗi client.
            # Main thread KHÔNG bị block, tiếp tục nhận client kế tiếp.
            client_thread = threading.Thread(
                target=handle_client, args=(ip, port, conn, addr, routes)
            )
            client_thread.start()
    except socket.error as e:
        print("Socket error: {}".format(e))


# Cửa ngõ trung gian (Entry point) khởi tạo trực tiếp và truyền tham số cấu hình xuống máy chủ nền (Backend)
def create_backend(ip, port, routes={}):
    """
    Điểm vào (entry point) để tạo và chạy backend server.
    Được gọi từ WeApRous.run() hoặc từ start_backend.py.

    :param ip     (str)           : địa chỉ IP để bind server.
    :param port   (int)           : cổng lắng nghe.
    :param routes (dict, optional): dict route handlers. Mặc định là dict rỗng.
    """

    run_backend(ip, port, routes)
