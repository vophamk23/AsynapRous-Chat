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
daemon.httpadapter
~~~~~~~~~~~~~~~~~

Module này là cầu nối giữa backend server và các route handler.
Nó nhận kết nối từ client, đọc request, kiểm tra cookie xác thực,
và quyết định trả về file tĩnh hay gọi đúng API handler.
"""

import json  # Thư viện hỗ trợ đóng gói và phân giải bộ dữ liệu JSON băng chuyền
from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict


# Đóng vai trò bộ chuyển đổi (Adapter) trung tâm phân tích các luồng giao tiếp logic HTTP
class HttpAdapter:
    """
    Lớp trung gian xử lý HTTP request cho mỗi kết nối client.
    Nhận socket kết nối, đọc dữ liệu, phân tích request,
    và trả về response phù hợp.
    """

    # Khai báo cấu trúc các trường thuộc tính cốt lõi (Core Attributes)
    # nhằm định hướng và giới hạn chu kỳ sống của vòng lặp xử lý giao thức
    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    # Khởi tạo bộ chứa tài nguyên, chuẩn bị tiếp nhận phân luồng Request và kết xuất Response
    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Khởi tạo đối tượng HttpAdapter và chuẩn bị các đối tượng Request/Response.
        """
        self.ip = ip  # Địa chỉ IP server
        self.port = port  # Cổng server
        self.conn = conn  # Socket kết nối client
        self.connaddr = connaddr  # Địa chỉ client (IP, port)
        self.routes = routes  # Bảng route từ WeApRous
        self.request = Request()  # Đối tượng phân tích request
        self.response = Response()  # Đối tượng xây dựng response

    # Phân tích luồng giao tiếp Raw Socket, luyện thành HTTP Request để chuyển định tuyến (Router)
    def handle_client(self, conn, addr, routes):
        """
        Xử lý toàn bộ một kết nối HTTP của client.
        Quy trình:
        1. Đọc headers (cho đến khi gặp '\r\n\r\n')
        2. Đọc body nếu có Content-Length
        3. Kiểm tra cookie xác thực cho /index.html
        4. Gọi API hook nếu route khớp
        5. Fallback trả về file tĩnh
        """
        self.conn = conn
        self.connaddr = addr
        req = self.request
        resp = self.response

        # Bước 1: Đọc dữ liệu từ socket cho đến khi gặp phần kết thúc header '\r\n\r\n'
        conn.settimeout(2)  # Timeout 2 giây nếu client không gửi gì
        raw = b""
        try:
            while b"\r\n\r\n" not in raw:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                raw += chunk
        except Exception:
            pass

        # Nếu không nhận được dữ liệu gì → đóng kết nối
        if not raw:
            try:
                conn.close()
            except Exception:
                pass
            return

        # Tách phần header khỏi raw bytes
        header_end = raw.find(b"\r\n\r\n")
        header_bytes = raw[: header_end + 4] if header_end != -1 else raw
        try:
            header_text = header_bytes.decode("utf-8", errors="replace")
        except Exception:
            header_text = header_bytes.decode("latin1", errors="replace")

        # Bước 2: Phân tích request line, headers, cookies, route hook
        req.prepare(header_text, routes)

        # Bước 3: Xác định độ dài body từ header Content-Length
        content_length = 0
        cl = req.headers.get("content-length")
        if cl:
            try:
                content_length = int(cl)
            except Exception:
                content_length = 0

        # Phần body đã đọc được cùng với headers (nếu có)
        body_already = raw[header_end + 4 :] if header_end != -1 else b""
        body = body_already
        to_read = content_length - len(body)
        # Đọc phần body còn thiếu (nếu body dài hơn buffer đầu tiên)
        try:
            while to_read > 0:
                chunk = conn.recv(min(4096, to_read))
                if not chunk:
                    break
                body += chunk
                to_read -= len(chunk)
        except Exception:
            pass

        # Lưu body dưới dạng chuỗi vào req.body
        try:
            req.body = body.decode("utf-8", errors="replace")
        except Exception:
            req.body = body.decode("latin1", errors="replace")

        # Now business logic: login + cookie-protected index
        try:
            # Normalize path: treat "/" as "/index.html"
            path = req.path
            if path == "/":
                path = "/index.html"
                req.path = path

            # Hàm tiện ích: gửi response và đóng kết nối
            def send_and_close(data_bytes):
                try:
                    conn.sendall(data_bytes)
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass

            # (Code POST /login đã chuyển vào start_chat_server.py – xử lý bởi WeApRous hook)

            # Kiểm tra cookie xác thực cho GET /index.html
            # Nếu cookie 'auth' không phải 'true' → trả 401 Unauthorized
            if req.method == "GET" and req.path in ["/index.html"]:
                cookie_val = req.cookies.get("auth", "")
                is_auth = False
                if cookie_val:
                    if cookie_val.split(";", 1)[0].strip() == "true":
                        is_auth = True
                if not is_auth:
                    # Chưa xác thực → trả 401
                    result = resp.build_unauthorized()
                    send_and_close(result)
                    return
                # Đã xác thực → phục vụ trang index.html bình thường
                result = resp.build_response(req)
                send_and_close(result)
                return

            # Nếu có API hook đã được đăng ký → gọi handler tương ứng
            if req.hook:
                try:
                    api_response = req.hook(req)  # Gọi hàm xử lý đã đăng ký
                    send_and_close(api_response)
                    return

                except Exception as e:
                    # Lỗi khi chạy handler → trả 500 Internal Server Error
                    import json

                    err = json.dumps(
                        {"error": "Internal Server Error", "message": str(e)}
                    )
                    response_bytes = (
                        "HTTP/1.1 500 Internal Server Error\r\n"
                        "Content-Type: application/json\r\n"
                        f"Content-Length: {len(err.encode('utf-8'))}\r\n"
                        "Connection: close\r\n"
                        "\r\n"
                        f"{err}"
                    ).encode("utf-8")
                    send_and_close(response_bytes)
                    return

            # Fallback: không có hook → phục vụ file tĩnh
            result = resp.build_response(req)
            send_and_close(result)
            return

        except Exception as e:
            # Xảy ra lỗi bất ngờ → trả 500
            body = b"Internal Server Error"
            header = (
                "HTTP/1.1 500 Internal Server Error\r\n"
                "Content-Type: text/plain\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode("utf-8")
            try:
                conn.sendall(header + body)
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            return

    # Tiện ích bóc tách rãnh rỗi và phân rã các cấu trúc Cookie truyền thống trong Header
    @property
    def extract_cookies(self, req, resp):
        """Trích xuất và phân tích cookie từ header của request."""
        cookies = {}
        cookie_header = req.headers.get("cookie", "")
        if cookie_header:
            for pair in cookie_header.split(";"):
                try:
                    key, value = pair.strip().split("=")
                    cookies[key.strip()] = value.strip()
                except ValueError:
                    pass
        return cookies

    # Cấu trúc đóng gói toàn văn phản hồi (Response) để sẵn sàng gửi trả lại hệ thống Client
    def build_response(self, req, resp):
        """Xây dựng đối tượng Response từ request và raw response data."""
        response = Response()

        response.raw = resp
        response.reason = "OK"

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        response.cookies = self.extract_cookies(req, resp)
        response.request = req
        response.connection = self

        return response

    # Trụ chờ cung cấp tham số mở rộng cho các hệ thống Header bổ trợ linh hoạt
    def add_headers(self, request):
        """Thêm header vào request (chưa hiện thực)."""
        pass

    # Xây dựng các nhóm Header đặc trưng nhằm định danh hệ thống qua cấu hình Server Proxy trung gian
    def build_proxy_headers(self, proxy):
        """Xây dựng header xác thực cho request qua proxy.
        Hiện tại sử dụng thông tin xác thực cứng – cần thay bằng Basic Auth thực sự.
        """
        headers = {}
        username, password = ("user1", "password")  # Xác thực tạm thời (dummy)

        if username:
            # Cần chuẩn bị Basic Auth (base64 encode néu dùng thực tế)
            # import base64
            # auth_str = f"{username}:{password}"
            # auth_b64 = base64.b64encode(auth_str.encode()).decode()
            # headers["Proxy-Authorization"] = f"Basic {auth_b64}"
            pass

        return headers
