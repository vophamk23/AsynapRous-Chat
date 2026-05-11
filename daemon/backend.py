#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.backend
~~~~~~~~~~~~~~~~~

Module này là "trái tim" của máy chủ, đóng vai trò quản lý vòng lặp mạng liên tục (backend daemon).
Nó triển khai một máy chủ TCP đa năng sử dụng thư viện `socket` của Python.
Đặc biệt, hệ thống hỗ trợ xử lý hàng ngàn kết nối cùng lúc thông qua ba cơ chế non-blocking:
Đa luồng (Threading), Hướng sự kiện (Callback/Selector) và Bất đồng bộ (Coroutine).

Nhiệm vụ chính: Mở cổng mạng -> Đón Client -> Giao nhiệm vụ xử lý cho `HttpAdapter`.
"""

from http import server
import socket
import threading
import argparse

import asyncio
import inspect

from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict

import selectors
# Khởi tạo bộ chọn sự kiện (Selector) - Dùng như một "tổng đài viên" cho chế độ Callback
sel = selectors.DefaultSelector()

# --- BẢNG ĐIỀU KHIỂN CHẾ ĐỘ CHẠY ĐỒNG THỜI (NON-BLOCKING) ---
# Tùy thuộc vào yêu cầu của hệ thống, bạn có thể linh hoạt chọn 1 trong 3 "động cơ":
# 1. "callback" : Hướng sự kiện, tiết kiệm RAM, phù hợp hệ thống I/O liên tục.
# 2. "coroutine": Hiện đại nhất (async/await), tối ưu cao, không kẹt luồng (block).
# 3. "threading": Đa luồng truyền thống, dễ dùng, tương thích hoàn hảo với logic Chat P2P.
mode_async = "coroutine"

def handle_client(ip, port, conn, addr, routes):
    """
    Quy trình tiếp đón Client dành cho mô hình Đa luồng (Threading).
    
    Tưởng tượng đây là một nhân viên phục vụ bàn. Khi khách (Client) vào, 
    nhân viên này sẽ ghi nhận thông tin và giao phó toàn bộ việc "phục vụ món ăn" 
    (phân tích HTTP Request) cho đầu bếp `HttpAdapter`.

    :param ip (str): Địa chỉ IP máy chủ.
    :param port (int): Cổng kết nối.
    :param conn (socket.socket): Đường ống mạng (socket) nối thẳng tới client.
    :param addr (tuple): Tọa độ mạng của client (IP, port).
    :param routes (dict): Bản đồ định tuyến để HttpAdapter biết cách xử lý.
    """
    print("[Backend] Đa luồng (Threading) - Đang phục vụ client tại {}".format(addr))
    daemon = HttpAdapter(ip, port, conn, addr, routes)
    daemon.handle_client(conn, addr, routes)


def handle_client_callback(server, ip, port, conn, addr, routes):
    """
    Quy trình tiếp đón Client dành cho mô hình Hướng sự kiện (Callback).
    
    Ở chế độ này, "tổng đài viên" (Selector) sẽ gọi hàm này BẤT CỨ KHI NÀO
    đường ống mạng (socket) có dữ liệu bay tới, giúp máy chủ không bao giờ 
    bị đứng chờ (non-blocking).

    :param server, ip, port, conn, addr, routes: Các tham số mạng cơ bản.
    """
    print("[Backend] Sự kiện (Callback) - Đang xử lý tín hiệu từ {}".format(addr))
    daemon = HttpAdapter(ip, port, conn, addr, routes)
    daemon.handle_client(conn, addr, routes)

async def async_server(ip="0.0.0.0", port=7000, routes={}):
    """
    Máy chủ chuyên dụng cho mô hình Coroutine (Asyncio).
    Xây dựng hoàn toàn trên nền tảng asyncio của Python.
    """
    print("[Backend] Máy chủ Async đang chạy trên cổng {}".format(port))
    if routes != {}:
        print("[Backend] Danh sách định tuyến đang hoạt động:")
        for key, value in routes.items():
            isCoFunc = "**ASYNC** " if inspect.iscoroutinefunction(value) else ""
            print("   + ('{}', '{}'): {}{}".format(key[0], key[1], isCoFunc, str(value)))

    # Tạo một hàm bọc (wrapper) ở bên trong để "nhốt" được biến routes
    async def client_handler(reader, writer):
        addr = writer.get_extra_info("peername")
        print("[Backend] Bất đồng bộ (Coroutine) - Đang phục vụ luồng từ {}".format(addr))
        try:
            # TRUYỀN ĐẦY ĐỦ ROUTES VÀO ĐÂY ĐỂ SERVER BIẾT ĐƯỜNG ĐI
            daemon = HttpAdapter(ip, port, None, addr, routes)
            await daemon.handle_client_coroutine(reader, writer)
        except Exception as e:
            print(f"[Backend] Lỗi xử lý luồng Coroutine: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    # Khởi động máy chủ với hàm bọc vừa tạo
    async_server_instance = await asyncio.start_server(client_handler, ip, port)
    async with async_server_instance:
        await async_server_instance.serve_forever()


def run_backend(ip, port, routes):
    """
    Khởi động trái tim của hệ thống mạng.
    
    Hàm này mở cổng máy chủ, liên tục đón lõng các yêu cầu truy cập và 
    quyết định cách thức xử lý (Thread, Callback hay Coroutine) dựa trên cấu hình.
    """
    global mode_async
    print("[Backend] Đánh thức Backend với chế độ '{}'".format(mode_async))
    
    # ---------------------------------------------------------
    # KỊCH BẢN 1: Máy chủ Bất đồng bộ (Async/Await)
    # ---------------------------------------------------------
    if mode_async == "coroutine":
       asyncio.run(async_server(ip, port, routes))
       return

    # ---------------------------------------------------------
    # KỊCH BẢN 2 & 3: Máy chủ Đa luồng (Threading) & Sự kiện (Callback)
    # ---------------------------------------------------------
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server.bind((ip, port))
        # Tăng hàng đợi (backlog) lên mức tối đa để đón 1000 khách ập vào cùng lúc
        server.listen(socket.SOMAXCONN if hasattr(socket, 'SOMAXCONN') else 2000)
        print("[Backend] Cổng {} đã sẵn sàng...".format(port))

        if routes != {}:
            print("[Backend] Danh sách định tuyến đang hoạt động:")
            for key, value in routes.items():
               isCoFunc = "**ASYNC** " if inspect.iscoroutinefunction(value) else ""
               print("   + ('{}', '{}'): {}{}".format(key[0], key[1], isCoFunc, str(value)))

        # Nếu dùng Callback, đăng ký máy chủ vào Tổng đài sự kiện (Selector)
        if mode_async == "callback":
            server.setblocking(False)  # Selector yêu cầu socket phải non-blocking
            sel.register(server, selectors.EVENT_READ, (ip, port, routes))
            # Chỉ register MỘT LẦN ngoài vòng lặp — register 2 lần = FileExistsError

        while True:
            if mode_async == "callback":
                # timeout=1: không block mãi mãi nếu không có client
                events = sel.select(timeout=1)
                
                for key, mask in events:
                    if key.fileobj is server:
                        try:
                            conn, addr = server.accept()
                            
                            # Socket con cần blocking — HttpAdapter không hỗ trợ non-blocking
                            conn.setblocking(True)
                            
                            # Đẩy vào thread riêng để vòng lặp không bị treo
                            # daemon=True: thread tự tắt khi server tắt
                            t = threading.Thread(
                                target=handle_client_callback,
                                args=(server, ip, port, conn, addr, routes),
                                daemon=True
                            )
                            t.start()
                            
                        except Exception as e:
                            print(f"[Backend] Callback accept lỗi: {e}")
            else:
                # Threading: block chờ client, mỗi client 1 thread riêng
                try:
                    conn, addr = server.accept()
                    client_thread = threading.Thread(
                        target=handle_client,
                        args=(ip, port, conn, addr, routes),
                        daemon=True
                    )
                    client_thread.start()
                except Exception as e:
                    print(f"[Backend] Threading accept lỗi: {e}")

    except socket.error as e:
        print("[Backend] LỖI MẠNG LÕI: {}".format(e))

def create_backend(ip, port, routes={}):
    """Điểm kích nổ (Entry point) để chạy máy chủ."""
    run_backend(ip, port, routes)