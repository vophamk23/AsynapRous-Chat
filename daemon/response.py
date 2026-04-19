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
daemon.response
~~~~~~~~~~~~~~~~~

Module này cung cấp lớp `Response` dùng để quản lý các thiết lập trả về của máy chủ HTTP (chẳng hạn như
cookie, thông tin xác thực) và tự động đóng gói nội dung để gửi trả về cho Client.
Hỗ trợ kiểm tra định dạng file (MIME type), truyền tải file HTML/CSS/JS tĩnh hoặc báo lỗi (401, 404, v.v.).
"""

import datetime
import json
import os
import mimetypes
from .dictionary import CaseInsensitiveDict

# Thiết lập BASE_DIR rỗng để biểu thị thư mục gốc của dự án.
# Nơi start_backend.py được chạy.
# Các thư mục con www/ và static/ sẽ được nối vào đây.
BASE_DIR = ""


# Quản lý cấu trúc chuẩn hóa vòng đời gói tin tạo lập HTTP Response chuyên nghiệp
class Response:
    """Lớp :class:`Response <Response>`, đại diện cho
    phản hồi của máy chủ HTTP khi có yêu cầu (Request) truyền tới.
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]

    # Thiết lập nguyên mẫu đối tượng rỗng tích lũy phân mảng trả lời HTTP Server
    def __init__(self, request=None):
        """
        Khởi tạo một đối tượng :class:`Response <Response>` mới.

        : tham số request : Đối tượng yêu cầu ban đầu.
        """

        self._content = b""  # Khởi tạo mặc định nội dung là kiểu bytes
        self._content_consumed = False
        self._next = None

        #: Mã trạng thái số nguyên HTTP trả về, ví dụ: 404 hoặc 200.
        self.status_code = None

        #: Từ điển thẻ khai báo Response Headers không phân biệt hoa thường.
        #: Ví dụ: ``headers['content-type']`` sẽ trả về
        #: giá trị của cấu trúc tiêu đề ``'Content-Type'``.
        self.headers = {}

        #: Vị trí URL gốc đính kèm với Response.
        self.url = None

        #: Loại mã hóa giải mã nội dung văn bản Response.
        self.encoding = None

        #: Danh sách lưu trữ vòng đời đối tượng :class:`Response <Response>`
        #: tính từ nhật ký của Request.
        self.history = []

        #: Diễn giải nguyên nhân dạng khối văn bản của HTTP Status, ví dụ: "Not Found" hoặc "OK".
        self.reason = None

        #: Danh sách các Cookie thu nạp từ Headers của Response.
        #: Bộ đệm lưu trữ danh sách Cookie cho Response headers.
        # Khởi tạo CaseInsensitiveDict để đảm bảo tiêu chuẩn HTTP.
        self.cookies = CaseInsensitiveDict()

        #: Tổng lượng thời gian xử lý tiêu tốn tính từ khoản khắc gửi yêu cầu
        self.elapsed = datetime.timedelta(0)

        #: Tham chiếu chéo trực tiếp tới đối tượng :class:`PreparedRequest <PreparedRequest>`
        #: mà Response này đang phản hồi.
        self.request = None

    # Truy xuất tính thống nhất phân loại (MIME) tương ứng đuôi mở rộng thư mục tham chiếu
    def get_mime_type(self, path):
        """
        Xác định định dạng tệp (MIME type) dựa trên đuôi của tệp.

        :tham số path (str): Đường dẫn đến tệp.

        :kiểu trả về str: Chuỗi loại MIME (ví dụ: 'text/html', 'image/png').
        """

        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return "application/octet-stream"

        # Cập nhật xử lý chuyên dụng cho logo trang web (Favicon .ico)
        if path.endswith(".ico"):
            return "image/x-icon"

        return mime_type or "application/octet-stream"

    # Định đoạt đường dẫn cơ sở phân tầng ranh giới truy cập thông qua chuẩn MIME bảo mật
    def prepare_content_type(self, mime_type="text/html"):
        """
        Gắn thẻ loại nội dung (Content-Type header) và thiết lập
        thư mục khởi gốc dùng để lấy file dựa trên loại MIME của nó.
        """

        base_dir = ""

        # Phân nhánh thư mục đích tùy thuộc vào phân loại MIME Type

        # Đặt header Content-Type trước
        self.headers["Content-Type"] = str(mime_type)

        # Xác định thư mục dựa trên MIME type
        if mime_type == "text/html":
            base_dir = BASE_DIR + "www/"
        elif mime_type == "text/css":
            base_dir = BASE_DIR + "static/css"
        elif mime_type == "text/javascript":
            base_dir = BASE_DIR + "static/js"
        elif mime_type.startswith("image/"):
            base_dir = BASE_DIR + "static/"
        elif mime_type.startswith("application/"):
            # Dành cho các tệp ứng dụng (ví dụ: /login API trả về JSON)
            # Nhưng logic đó đã được xử lý trong httpadapter.py
            # Ở đây chúng ta giả định là file tĩnh
            base_dir = BASE_DIR + "apps/"
        else:
            # Các loại file khác không được hỗ trợ
            raise ValueError(f"Invalid MIME type: {mime_type}")

        print(f"[Response] processing MIME {mime_type} from base_dir {base_dir}")
        return base_dir

    # Kéo tài liệu ổ cứng bọc kén an toàn từ chối thủ đoạn lợi dụng Directory Traversal
    def build_content(self, path, base_dir):
        """
        Tải nội dung object file (HTML, CSS, JS...) từ ổ cứng lên máy chủ.
        """

        # filepath = os.path.join(base_dir, path.lstrip('/'))
        # Lược bỏ dấu / ở đầu path
        rel_path = path.lstrip("/")

        # Tạo đường dẫn mục tiêu và chuẩn hóa
        target = os.path.join(base_dir, rel_path)

        # Biện pháp bảo mật: Chặn khai thác lùi thư mục (Directory Traversal) bằng realpath/commonpath
        base_real = os.path.realpath(base_dir)
        target_real = os.path.realpath(target)

        # Nếu target không nằm trong base -> từ chối

        # Đảm bảo đường dẫn là an toàn (không đi ngược thư mục)
        # if '..' in filepath:
        if not os.path.commonpath([base_real]) == os.path.commonpath(
            [base_real, target_real]
        ):
            # Không cho phép truy cập ra ngoài base_dir
            raise IOError("File path is not allowed")

        # print("[Response] serving the object at location {}".format(filepath))
        print("[Response] serving the object at location {}".format(target_real))

        # Thực hiện đọc dữ liệu nhị phân từ ổ đĩa lưu trữ
        content = b""
        # Mở tệp ở chế độ 'rb' (read binary) vì chúng ta cần gửi bytes
        with open(target_real, "rb") as f:
            content = f.read()

        return len(content), content

    # Lắp ghép băng chuyền Headers tuân thủ triệt để khung luật diễn đạt của HTTP
    def build_response_header(self, request):
        """Xây dựng bộ thẻ khai báo (HTTP response headers) chi tiết dựa vào đối tượng bản tin Client (request)."""

        # Quy trình cấu trúc hệ thống Headers:

        # 1. Tạo dòng trạng thái (Status Line)
        status_line = f"HTTP/1.1 {self.status_code} {self.reason}\r\n"

        # 2. Thêm các header từ self.headers (đã được đặt ở các hàm khác)
        header_lines = []

        # Thêm header 'Date'
        self.headers["Date"] = datetime.datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        self.headers["Server"] = "BKSysNet-Server (Python)"

        for key, value in self.headers.items():
            header_lines.append(f"{key}: {value}")

        # 3. Thêm các cookie (Rất quan trọng cho Task 2.1)
        for key, value in self.cookies.items():
            # Ví dụ: Set-Cookie: auth=true
            header_lines.append(f"Set-Cookie: {key}={value}")

        # 4. Ghép tất cả lại
        # Nối các dòng header bằng \r\n, và kết thúc bằng một dòng trống \r\n
        fmt_header = status_line + "\r\n".join(header_lines) + "\r\n\r\n"

        return fmt_header.encode("utf-8")

    # Đóng gói bộ đệm thông báo mã 404 chống cạn kiệt tài nguyên logic
    def build_notfound(self):
        """
        Đóng gói một thông báo lỗi HTTP 404 Not Found tiêu chuẩn.
        """

        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Accept-Ranges: bytes\r\n"
            "Content-Type: text/html\r\n"
            "Content-Length: 13\r\n"
            "Cache-Control: max-age=86000\r\n"
            "Connection: close\r\n"
            "\r\n"
            "404 Not Found"
        ).encode("utf-8")

    # Triển khai bộ đệm thành công mã 200 tích hợp phân vùng dữ liệu động chuẩn JSON
    def build_success(self, body):
        # self.status = 200
        # self.headers = {"Content-Type": "application/json"}
        json_body = json.dumps(body)
        content_length = len(json_body.encode("utf-8"))

        return (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {content_length}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{json_body}"
        ).encode("utf-8")

    # Triển khai bộ đệm lỗi truy cập mã 400 chặn đứng yêu cầu tồi vượt rào
    def build_bad_request(self, body):
        json_body = json.dumps(body)
        content_length = len(json_body.encode("utf-8"))
        return (
            "HTTP/1.1 400 Bad Request\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {content_length}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{json_body}"
        ).encode("utf-8")

    # Triển khai bộ đệm chấn thương hệ thống mã 500 duy trì Server giữ vững sinh lộ vòng lặp
    def build_internal_error(self, body):
        json_body = json.dumps(body)
        content_length = len(json_body.encode("utf-8"))
        return (
            "HTTP/1.1 500 Internal Server Error\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {content_length}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{json_body}"
        ).encode("utf-8")

    # Mắt xích cuối tổng hòa quy trình kết xuất mảng Header tĩnh và Content thành luồng Byte
    def build_response(self, request):
        """
        Lắp ráp gói HTTP Response đầy đủ cuối cùng, bao gồm cả Headers lẫn Payload (Content).
        """

        path = request.path
        mime_type = self.get_mime_type(path)
        print(
            "[Response] {} path {} mime_type {}".format(
                request.method, request.path, mime_type
            )
        )

        base_dir = ""
        c_len = 0

        # Khối Block thực thi chính: Đọc, đóng gói và kiểm soát Ngoại Lệ (Exception)
        try:
            # 1. Chuẩn bị content-type và thư mục
            base_dir = self.prepare_content_type(mime_type)

            # 2. Tải nội dung tệp
            c_len, self._content = self.build_content(path, base_dir)

            # 3. Nếu thành công, đặt status 200 OK
            self.status_code = 200
            self.reason = "OK"
            self.headers["Content-Length"] = c_len
            self.headers["Connection"] = "close"  # Đóng kết nối sau khi gửi

        except (IOError, FileNotFoundError, ValueError) as e:
            # 4. Nếu có lỗi (Không tìm thấy tệp, MIME không hỗ trợ)
            print(f"[Response] Error serving file {path}: {e}")
            return self.build_notfound()

        # 5. Xây dựng header
        self._header = self.build_response_header(request)

        # 6. Trả về header + nội dung
        return self._header + self._content

    # Củng cố rào cản từ chối cấp quyền truy cập với tín hiệu khước từ định mức 401
    def build_unauthorized(self):
        """Xây dựng phản hồi báo lỗi xác thực không được trao quyền."""
        self.status_code = 401
        self.reason = "Unauthorized"
        content = b"401 Unauthorized"

        headers = (
            f"HTTP/1.1 {self.status_code} {self.reason}\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(content)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )

        return headers.encode("utf-8") + content

    # Xác thực chuỗi phiên hệ thống, cấp thẻ Cookie chứng nhận, định hướng Landing
    def build_login_success(self, request):
        """Quản trị thủ tục tái điều hướng giao diện tĩnh kèm đánh dấu Phiên đăng nhập hợp thức hóa."""

        # 1. Đặt thông số ghi chú phiên xác thực
        self.cookies["auth"] = "true; Path=/"
        # 2. Điều hướng biến đổi thông số yêu cầu nguyên thủy
        request.path = "/index.html"
        request.method = "GET"

        # 3. Gọi hàm build_response thông thường
        # Hàm này sẽ đọc path mới, lấy tệp index.html
        # và build_response_header sẽ đọc cookie chúng ta vừa set
        return self.build_response(request)
