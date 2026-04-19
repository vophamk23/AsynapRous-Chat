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
daemon.request
~~~~~~~~~~~~~~~~~

Module này cung cấp lớp Request để phân tích (parse) HTTP request từ client.
Bất kỳ request nào gửi đến server đều được đƳa qua lớp này để trích xuất:
- Request line: method, path, version
- Headers: tất cả header (không phân biệt hoa/thường)
- Cookies: parse từ header 'Cookie'
- Query params: parse từ URL (ví dụ: ?user=Alice&peer=Bob)
- Hook: hàm xử lý tương ứng từ bảng route
"""

from .dictionary import CaseInsensitiveDict
import json as json_lib
from urllib.parse import urlparse, parse_qs


# Cấu trúc hệ thống quản trị chuyên sâu hỗ trợ phân giải và trích xuất nguyên hàm HTTP Request
class Request:
    """Lớp Request – đối tượng biểu diễn một HTTP request từ client.

    Mỗi kết nối từ client sẽ tạo ra một đối tượng Request để
    lưu trữ và truy cập các thông tin cịa request dễ dàng.

    Ví dụ sử dụng::
      >>> req = Request()
      >>> req.prepare(raw_http_string, routes)
      >>> print(req.method, req.path, req.cookies)
    """

    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
        "query_params",
    ]

    # Khởi tạo đối tượng rỗng đệm phục vụ quy trình bóc tách siêu dữ liệu HTTP
    def __init__(self):
        self.method = None  # HTTP verb: GET, POST, PUT, DELETE ...
        self.url = None  # URL đầy đủ của request
        self.headers = None  # Dict chứa các header (key thường thường)
        self.path = None  # Đường dẫn URL (ví dụ: /login, /index.html)
        self.cookies = None  # Dict các cookie parse từ header 'Cookie'
        self.body = None  # Nội dung body của request (dành cho POST)
        self.routes = {}  # Bảng ánh xạ route từ WeApRous
        self.hook = None  # Hàm xử lý (handler) khớp với route hiện tại
        # Dict chứa các tham số query string từ URL (ví dụ: ?user=Alice&peer=Bob)
        self.query_params = {}

    # Khai thác định dạng cốt lõi (Method, URL, Version) từ dòng Header mở đầu gói tin
    def extract_request_line(self, request):
        """Phân tích dòng đầu tiên của HTTP request (request line).
        Tích xuất method, path và query params từ URL."""
        try:
            lines = request.splitlines()
            first_line = lines[0]  # Ví dụ: 'GET /login?user=Alice HTTP/1.1'
            method, raw_path, version = first_line.split()

            parsed = urlparse(raw_path)  # Parse URL thành các phần
            path = parsed.path  # Lấy phần đường dẫn

            if path == "/":
                path = "/index.html"  # Mặc định '/' → '/index.html'

            # Chuyển query string thành dict {key: value}
            self.query_params = {
                k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()
            }

        except Exception:
            return None, None

        return method, path, version

    # Dàn phẳng hệ thống từ điển trạng thái phụ thuộc của luồng HTTP Headers vào bộ đệm tĩnh
    def prepare_headers(self, request):
        """Phân tích và cấu trúc lại các HTTP header từ chuỗi request thô."""
        lines = request.split("\r\n")
        headers = {}
        for line in lines[1:]:
            if ": " in line:
                key, val = line.split(": ", 1)
                headers[key.lower()] = val  # Đổi key về chữ thường để tra cứu dễ dàng
        return headers

    # Trạm trung tâm tổng thầu điều phối quy trình phân mảnh chuỗi văn bản Request thô
    def prepare(self, request, routes=None):
        """Phân tích toàn bộ HTTP request thô: request line, headers, cookies và route hook."""

        # Bước 1: Phân tích request line (method, path, version)
        self.method, self.path, self.version = self.extract_request_line(request)
        print(
            "[Request] {} path {} version {}".format(
                self.method, self.path, self.version
            )
        )

        # Bước 2: Gắn hàm xử lý (hook) dựa trên bảng route của WeApRous
        if not routes == {}:
            self.routes = routes
            # Tìm hàm xử lý khớp với (method, path) hiện tại
            self.hook = routes.get((self.method, self.path))

        # Bước 3: Phân tích headers
        self.headers = self.prepare_headers(request)

        # Bước 4: Phân tích cookie từ header 'Cookie'
        cookies_string = self.headers.get("cookie", "")
        self.cookies = {}
        if cookies_string:
            cookie_pairs = cookies_string.split("; ")  # Tách các cookie bằng '; '
            for pair in cookie_pairs:
                if "=" in pair:
                    name, value = pair.split("=", 1)  # Tách name=value
                    self.cookies[name.strip()] = value
        return

    # Định hình tập dữ liệu Body theo khuôn chuẩn mã hóa được yêu cầu từ Headers
    def prepare_body(self, data, files, json=None):
        """Xây dựng body cho request dựa trên kiểu dữ liệu đưa vào."""
        body = None
        if json is not None:
            # Dữ liệu JSON: chuyển dict → chuỗi JSON và set Content-Type
            body = json_lib.dumps(json).encode("utf-8")
            self.headers["Content-Type"] = "application/json"
        elif data is not None:
            # Dữ liệu thần: chuyển sang bytes nếu cần
            body = data if isinstance(data, bytes) else str(data).encode("utf-8")
        elif files is not None:
            # Tập tin: ghép nội dung các file lại
            combined = b""
            for f in files:
                combined += (
                    f.read() if isinstance(f.read(), bytes) else f.read().encode()
                )
            body = combined
        else:
            body = b""
        self.body = body
        self.prepare_content_length(self.body)

    # Chủ động lượng hóa quy mô Body và chèn thông số vào biến phụ Content-Length
    def prepare_content_length(self, body):
        """Tính và đặt header Content-Length dựa trên độ dài body."""
        self.headers["Content-Length"] = str(len(body)) if body else "0"
        return

    # Cổng chờ sẵn sàng bổ sung các chính sách xác thực Authorization chuyên biệt
    def prepare_auth(self, auth, url=""):
        """(Chưa hiện thực) Dành cho xác thực request phía client nếu cần."""
        return

    # Đầu nối trung chuyển bộ Cookie phiên người dùng gài cắm vào giao thức truyền dẫn
    def prepare_cookies(self, cookies):
        """Gán Cookie header vào request (dùng khi gửi request có cookie)."""
        self.headers["Cookie"] = cookies
