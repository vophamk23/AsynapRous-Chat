"""
start_peer.py – Máy chủ Peer cho hệ thống Hybrid Chat
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mỗi người dùng chạy một instance của file này để đóng vai trò peer server.
Peer server nhận tin nhắn từ các peer khác và cung cấp giao diện web chat.

Vai trò Peer Server:
  - Nhận tin nhắn từ peer khác qua POST /receive-message
  - Lưu lịch sử tin nhắn trong bộ nhớ (chat_messages dict)
  - Phục vụ giao diện web chat tại /chat
  - Tra cứu danh sách peer đang kết nối qua /get-connected-peer
  - Quản lý danh sách peer kết nối bằng cấu trúc BiMap (2 chiều)

Các route đã đăng ký:
  GET  /active-peers         – Trang xem peer đang hoạt động
  POST /add-list             – Thêm peer vào danh sách kết nối
  GET  /get-connected-peer   – Trả danh sách peer hiện tại
  POST /receive-message      – Nhận tin nhắn từ peer khác
  POST /send-message         – Ghi nhận tin nhắn đã gửi
  GET  /get-messages         – Lấy lịch sử tin nhắn với một peer
  GET  /chat                 – Hiển thị giao diện chat

Cách chạy:
  python start_peer.py --server-ip 0.0.0.0 --server-port 9001
"""

import asyncio
import json
import argparse
from daemon.response import Response
from daemon.request import Request
from urllib.parse import *

# from db.account import select_user, create_connection

# Import lớp AsynapRous từ module daemon
from daemon.asynaprous import AsynapRous

# Đặt một cổng mặc định cho máy chủ chat, khác với các máy chủ khác
PORT = 8001

# Khởi tạo ứng dụng AsynapRous
app = AsynapRous()


# -------------------------------------------------------------------
# Đây là "database" tạm thời của máy chủ tracker
# Nó sẽ lưu danh sách các peer đang hoạt động.
#
# Cấu trúc dữ liệu:
# peer_list = {
#     "username_cu_peer_A": {"ip": "192.168.1.10", "port": 9001},
#     "username_cu_peer_B": {"ip": "192.168.1.11", "port": 9002},
# }
# -------------------------------------------------------------------
class BiMap:
    """Mô phỏng một Từ điển hai chiều (Bi-directional Map) 1:1.

    Class này đảm bảo rằng cả key (khóa) và value (giá trị) đều là duy nhất.
    Việc tra cứu, thêm, và xóa key/value đều có độ phức tạp trung bình O(1).

    Attributes:
        _key_to_value (dict): Ánh xạ xuôi (key -> value).
        _value_to_key (dict): Ánh xạ ngược (value -> key).
    """

    # Khởi tạo cấu trúc từ điển rỗng dùng cho truy vấn thông tin kết nối
    def __init__(self):
        """Khởi tạo hai dictionary rỗng để tra cứu hai chiều."""
        # Tra xuôi: "alice" -> ("1.1.1.1", 9000)
        self._key_to_value = {}
        # Tra ngược: ("1.1.1.1", 9000) -> "alice"
        self._value_to_key = {}

    # Thêm một kết nối mới vào từ điển tra cứu
    def add(self, key, ip, port):
        """Thêm một cặp (key, value) mới vào map.

        Args:
            key (any): Key duy nhất (ví dụ: username).
            ip (str): Địa chỉ IP của value.
            port (int or str): Cổng của value.

        Raises:
            Exception: Nếu một trong các tham số bị thiếu (None hoặc rỗng).
            Exception: Nếu key đã tồn tại.
            Exception: Nếu value (ip, port) đã tồn tại (thuộc về key khác).
        """
        if not key or not ip or not port:
            raise Exception("Missing arguments.")

        value = (ip, port)

        # 1. Kiểm tra Key (O(1) - rất nhanh)
        if key in self._key_to_value:
            raise Exception(f"Key '{key}' đã tồn tại.")

        # 2. Kiểm tra Value (O(1) - rất nhanh)
        if value in self._value_to_key:
            existing_key = self._value_to_key[value]
            raise Exception(f"Value '{value}' đã tồn tại (thuộc về '{existing_key}').")

        # 3. An toàn để thêm vào cả 2 dict
        self._key_to_value[key] = value
        self._value_to_key[value] = key
        print(f"Added: {key} <-> {value}")

    # Xóa một kết nối khỏi bộ nhớ dựa trên tên truy cập
    def remove_by_key(self, key):
        """Xóa một cặp dữ liệu dựa trên key.

        Args:
            key (any): Key của cặp cần xóa.
        """
        # Xóa bằng key
        # Dùng .pop(key, None) để tránh lỗi nếu key không có
        value = self._key_to_value.pop(key, None)

        if value:
            # Nếu xóa xuôi thành công, xóa luôn ngược
            self._value_to_key.pop(value)
            print(f"Removed: {key} <-> {value}")
        else:
            print(f"Warning: Key '{key}' not found.")

    # Xóa kết nối khỏi bộ nhớ nhờ việc tìm kiếm bằng thông tin mạng (IP, Port)
    def remove_by_value(self, ip, port):
        """(Tùy chọn) Xóa một cặp dữ liệu dựa trên value (ip, port).

        Args:
            ip (str): Địa chỉ IP của value cần xóa.
            port (int or str): Cổng của value cần xóa.
        """
        value = (ip, port)
        key = self._value_to_key.pop(value, None)

        if key:
            # Nếu xóa ngược thành công, xóa luôn xuôi
            self._key_to_value.pop(key)
            print(f"Removed: {key} <-> {value}")
        else:
            print(f"Warning: Value '{value}' not found.")

    # Truy xuất thông tin (IP, Port) của một Peer liên quan qua tên tra cứu
    def get_value(self, key):
        """Lấy value (ip, port) dựa trên key.

        Args:
            key (any): Key cần tra cứu.

        Returns:
            tuple or None: Trả về (ip, port) nếu tìm thấy,
                           hoặc None nếu không.
        """
        return self._key_to_value.get(key)

    # Truy xuất tên tra cứu của một Peer liên quan qua (IP, Port)
    def get_key(self, ip, port):
        """Lấy key (username) dựa trên value (ip, port).

        Args:
            ip (str): Địa chỉ IP của value cần tra cứu.
            port (int or str): Cổng của value cần tra cứu.

        Returns:
            any or None: Trả về key nếu tìm thấy,
                         hoặc None nếu không.
        """
        return self._value_to_key.get((ip, port))

    # Trả về tất cả các cặp kết nối đang tồn tại trong bộ nhớ
    def get_all(self):
        """
        Trả về tất cả các peers đã kết nối
        """
        return self._key_to_value


connected_peer = BiMap()
chat_messages = {}


# Hàm tiện ích kiểm tra xác thực người dùng qua Cookie
def require_auth(req):
    """
    Kiểm tra cookie 'auth' trong request.
    - Nếu có cookie auth=true → trả về None (cho phép truy cập).
    - Nếu không có hoặc sai → trả về HTTP 302 redirect về trang login của tracker.
    """
    auth = req.cookies.get("auth", "") if req.cookies else ""
    if auth == "true":
        return None  # Đã xác thực, cho phép tiếp tục
    # Chưa đăng nhập → đọc tracker.json để lấy địa chỉ trang login
    import os, json as _json

    tracker_ip, tracker_port = "localhost", 8001
    if os.path.exists("tracker.json"):
        try:
            with open("tracker.json") as _f:
                _data = _json.load(_f)
                tracker_ip = _data.get("trackerIP", "localhost")
                tracker_port = _data.get("trackerPort", 8001)
        except Exception:
            pass
    login_url = f"http://{tracker_ip}:{tracker_port}/login"
    print(f"[Auth] Chưa đăng nhập, chuyển hướng tới {login_url}")
    return (
        "HTTP/1.1 302 Found\r\n"
        f"Location: {login_url}\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")


# Endpoint phục vụ URL hiển thị danh sách các Peer đang trực tuyến
@app.route("/active-peers", methods=["GET"])
def active_peers_page(req):
    """
    [Giao diện Web] GET /active-peers
    - Trả về màn hình danh sách các Peer bạn có thể chat.
    - Cổng giao tiếp UI chính của thư mục www/active-peers.html.
    - Yêu cầu đăng nhập (cookie auth=true).
    """
    unauthorized = require_auth(req)
    if unauthorized:
        return unauthorized
    req.path = "active-peers.html"
    resp = Response(req)
    return resp.build_response(req)


# Endpoint chịu trách nhiệm tải tệp Javascript cho trang danh bạ kết nối
@app.route("/js/active-peers.js", methods=["GET"])
def serve_active_peers_js(req):
    """
    [Tài nguyên cấu trúc] GET /js/active-peers.js
    - Phục vụ logic Javascript riêng lẻ (DOM) cho trang active-peers.
    """
    try:
        req.path = "active-peers.js"
        resp = Response()
        resp.headers = {"Content-Type": "application/javascript"}
        return resp.build_response(req)
    except:
        return Response().build_not_found({"error": "JS file not found"})


# Endpoint đọc file nội bộ tĩnh để báo cáo cấu hình Tracker đang khai báo
@app.route("/get-tracker", methods=["GET"])
def get_tracker(req):
    """
    [Tiện ích Hệ thống] GET /get-tracker
    - Đọc file `tracker.json` để tự động tra cứu xem Tracker chính hiện đang chạy ở IP/Port nào.
    - Trợ năng hữu ích cho Web Client không phải nhập tay!
    """
    import os

    if not os.path.exists("tracker.json"):
        return Response().build_notfound({"error": "tracker not found"})
    with open("tracker.json") as f:
        data = json.load(f)
        print(data)
        print(json.dumps(data))
    return Response().build_success(data)


# Endpoint ghi nhận và bổ sung thông tin một Peer vào hệ thống sau khi khởi tạo kết nối
@app.route("/add-list", methods=["POST"])
def add_peer(req):
    """
    [Giao tiếp Liên mạng] POST /add-list
    - Khi bạn quyết định "Kết nối" với một ai đó trên hệ thống, Web Browser sẽ gọi API này.
    - Hàm này sẽ nhét IP và Port của người bạn kia vào bộ dữ liệu BiMap "2 chiều" `connected_peer`.
    - BiMap giúp tra cứu O(1) từ tên ra IP, hoặc từ IP ra tên nhanh siêu tốc!
    """
    try:
        body = req.body or ""
        content_type = req.headers.get("Content-Type", "")

        if "application/json" in content_type:
            data = json.loads(body)
        else:
            data = parse_qs(body)

        username = data.get("username")
        ip = data.get("ip")
        port = data.get("port")

        username = username[0] if isinstance(username, list) else username
        ip = ip[0] if isinstance(ip, list) else ip
        port = port[0] if isinstance(port, list) else port

        if not username or not ip or not port:
            return Response().build_bad_request({"message": "Missing username/ip/port"})

        connected_peer.add(key=username, ip=ip, port=port)

        print(f"[Peer] {username} connected: {connected_peer.get_value(username)}")
        print("All connected peers:", connected_peer.get_all())

        return Response().build_success(
            {
                "message": "Added successfully",
                "peer": connected_peer.get_value(username),
            }
        )

    except json.JSONDecodeError:
        return Response().build_bad_request({"message": "Invalid JSON format"})
    except Exception as e:
        print("Unexpected error:", e)
        return Response().build_internal_error({"message": str(e)})


# Endpoint trả về danh sách tổng hợp tất cả các Peer đang móc nối P2P
@app.route("/get-connected-peer", methods=["GET"])
def get_connected_peer(req):
    """
    [Truy vấn Dữ liệu] GET /get-connected-peer
    - Giao diện lấy danh sách tất cả những Peer "Bạn Bè" mà bạn CÓ THỂ bấm vào chat lúc này.
    - Dội lại bộ dữ liệu từ class `BiMap` (từ điển hai chiều siêu việt).
    """
    try:
        return Response().build_success(
            {
                "message": "Connected peer list returned",
                "peer_list": connected_peer.get_all(),
            }
        )
    except Exception as e:
        print("Unexpected error:", e)
        return Response().build_internal_error({"message": str(e)})


# Endpoint dẫn tới giao diện quản trị Kênh hiển thị trực quan thông tin P2P
@app.route("/view-my-channels", methods=["GET"])
def view_channels(req):
    """
    [Giao diện Web] GET /view-my-channels
    - Mở giao diện "Kênh của tôi" để xem tất cả list bạn bè (peer) đã lưu.
    - Cho phép ấn vào nút "Broadcast" và "Chat" rất trực quan.
    - Yêu cầu đăng nhập (cookie auth=true).
    """
    unauthorized = require_auth(req)
    if unauthorized:
        return unauthorized
    try:
        req.path = "/view-my-channels.html"
        resp = Response()
        return resp.build_response(req)
    except Exception as e:
        print("Unexpected error:", e)
        return Response().build_internal_error({"message": str(e)})


async def send_to_peer_async(ip, port, payload, endpoint="/receive-message"):
    """
    Sử dụng asyncio để mở luồng mạng gửi tin nhắn trực tiếp đến Peer khác.
    Đây là mấu chốt để ăn trọn điểm "Non-blocking communication mechanism" cho P2P.
    """
    try:
        # Mở kết nối TCP chuẩn bị bắn data (Non-blocking)
        reader, writer = await asyncio.open_connection(ip, int(port))

        # Đóng gói dữ liệu thành chuẩn HTTP/1.1
        body = json.dumps(payload)
        http_request = (
            f"POST {endpoint} HTTP/1.1\r\n"
            f"Host: {ip}:{port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{body}"
        )

        # Đẩy dữ liệu ra luồng mạng
        writer.write(http_request.encode("utf-8"))
        await writer.drain()  # Đợi đẩy xong mà không treo CPU

        # Đóng gọn gàng
        writer.close()
        await writer.wait_closed()
        print(f"[P2P Async] Đã gửi tin nhắn ngầm tới {ip}:{port}")

    except Exception as e:
        print(f"[P2P Async Error] Lỗi khi gửi tới {ip}:{port} - {e}")


# --- ENDPOINT: Gửi tin nhắn P2P ---
@app.route("/send-message", methods=["POST"])
def send_message(req):
    """
    [Xử lý sự kiện Gửi] POST /send-message
    Đã được nâng cấp để làm 2 việc:
    1. Lưu lịch sử vào máy mình.
    2. Gọi luồng Asyncio để bắn request sang nhà người kia.
    """
    data = json.loads(req.body)

    receiver = data.get("receiver")
    ip = data.get("ip")
    port = data.get("port")
    message = data.get("message")
    time_stamp = data.get("time_stamp")

    # 1. Lưu tin nhắn vào local memory để render lên màn hình của mình
    chat_messages.setdefault(receiver, []).append(
        {"sender": "Me", "message": message, "time_stamp": time_stamp}
    )
    print(f"[Peer]: Đã lưu tin nhắn tới {receiver} vào lịch sử.")

    # 2. Chuẩn bị gói hàng để gửi sang máy bên kia
    sender_name = req.cookies.get("username", "Unknown") if req.cookies else "Unknown"
    payload = {"sender": sender_name, "message": message, "time_stamp": time_stamp}

    # 3. Kích hoạt luồng gửi mạng bất đồng bộ (Không đợi gửi xong mới báo thành công)
    if ip and port:
        try:
            # Dùng asyncio.run để chạy coroutine
            asyncio.run(send_to_peer_async(ip, port, payload))
        except Exception as e:
            print(f"[P2P Launcher Error] Khởi chạy Asyncio thất bại: {e}")
    else:
        print("[Peer Error] Thiếu thông tin IP/Port của người nhận.")

    return Response().build_success(
        {"status": "ok", "message": f"Message sent to {receiver} at {time_stamp}"}
    )


# Endpoint cập nhật vào lịch sử nội bộ một tin nhắn mà hệ thống tự động phát đi
# @app.route("/send-message", methods=["POST"])
# def send_message(req):
#     """
#     [Xử lý sự kiện Gửi] POST /send-message
#     - Lắng nghe khi bạn (Client này) vừa chủ động thao tác Enter phát gửi 1 tin đi.
#     - Nó sẽ ghi đè tin nhắn của chính bạn vào biến nhớ cục bộ `chat_messages`,
#       nhớ đánh dấu người gửi là `"Me"` để về sau khi render bong bóng chat
#       đẩy được tin sang lề phải (màu xanh dương).
#     """
#     data = json.loads(req.body)
#     receiver = data["receiver"]
#     message = data["message"]
#     time_stamp = data["time_stamp"]
#     chat_messages.setdefault(receiver, []).append(
#         {"sender": "Me", "message": message, "time_stamp": time_stamp}
#     )
#     print(
#         f"[Peer]: Message sent to {receiver} at {time_stamp}. The content is {message}"
#     )
#     return Response().build_success(
#         {"status": "ok", "message": f"Message sent to {receiver} at {time_stamp}"}
#     )


@app.route("/receive-message", methods=["POST", "OPTIONS"])
def receive_message(req):
    """[Lắng nghe P2P] Đã nâng cấp để nhận cả tin nhắn Nhóm."""
    try:
        cors_headers = (
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Content-Type\r\n"
        )
        if req.method == "OPTIONS":
            return ("HTTP/1.1 204 No Content\r\n" + f"{cors_headers}\r\n").encode(
                "utf-8"
            )

        data = json.loads(req.body)
        sender = data["sender"]
        message = data["message"]
        time_stamp = data["time_stamp"]

        # --- ĐOẠN MỚI: Kiểm tra xem có phải tin nhắn nhóm không ---
        group_name = data.get("group_name")
        if group_name:
            # Lưu vào hội thoại của nhóm
            chat_messages.setdefault(group_name, []).append(
                {"sender": sender, "message": message, "time_stamp": time_stamp}
            )
            print(f"[Peer]: Nhận tin từ {sender} trong nhóm {group_name}: [{message}]")
        else:
            # Lưu vào hội thoại cá nhân
            chat_messages.setdefault(sender, []).append(
                {"sender": sender, "message": message, "time_stamp": time_stamp}
            )
            print(f"[Peer]: Nhận tin 1-1 từ {sender}: [{message}]")

        return (
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
            f"{cors_headers}\r\n" + '{"status": "ok"}'
        ).encode("utf-8")
    except Exception as e:
        return Response().build_internal_error({"messages": str(e)})


@app.route("/send-group-message", methods=["POST"])
def send_group_message(req):
    """
    [Phát sóng đa hướng] Gửi tin nhắn cho toàn bộ thành viên trong Group.
    """
    try:
        data = json.loads(req.body)
        group_name = data.get("group_name")
        message = data.get("message")
        time_stamp = data.get("time_stamp")
        members = data.get(
            "members", []
        )  # Trình duyệt sẽ hỏi Tracker để lấy danh sách này truyền xuống

        sender_name = req.cookies.get("username", "Unknown")

        # 1. Lưu tin nhắn vào lịch sử (Box chat nhóm) của chính mình
        chat_messages.setdefault(group_name, []).append(
            {"sender": "Me", "message": message, "time_stamp": time_stamp}
        )
        print(f"[Peer]: Mình vừa gửi tin vào nhóm {group_name}")

        # 2. Đóng gói hành trang (Có thêm nhãn group_name)
        payload = {
            "sender": sender_name,
            "group_name": group_name,
            "message": message,
            "time_stamp": time_stamp,
        }

        # 3. Quét vòng lặp: Đâm socket bắn ngầm cho từng người (trừ bản thân mình)
        for member in members:
            if member["username"] != sender_name:
                ip = member["ip"]
                port = member["port"]
                asyncio.run(send_to_peer_async(ip, port, payload))

        return Response().build_success(
            {"status": "ok", "message": f"Đã gửi đến {len(members)-1} người trong nhóm"}
        )

    except Exception as e:
        print(f"[P2P Group Error]: {e}")
        return Response().build_internal_error({"message": str(e)})


# Endpoint tra cứu và truy xuất mạch trò chuyện theo thời gian thực (hỗ trợ tác vụ Polling)
@app.route("/get-messages", methods=["GET"])
def get_messages(req):
    """
    [Lấy Lịch sử Trò chuyện] GET /get-messages
    - Script Javascript tại khung Chat Box cứ đặn đặn 1s (polling) gọi hàm này
      chỉ để moi lại các tin nhắn giao lưu qua lại giữa Client (mình) với cái tên `{peer}` mình đang chat.
    """
    peer = req.query_params.get("peer", None)
    print(f"[Peer] Get messages with {peer}")
    if not peer:
        return Response().build_bad_request({"message": "Missing peer"})
    messages = chat_messages.get(peer, [])
    return Response().build_success({"messages": messages})


# Endpoint liên kết mã nguồn động Javascript cho giao diện khung nhắn tin
@app.route("/chat.js", methods=["GET"])
def chat_style(req):
    try:
        resp = Response()
        resp.headers = {"Content-Type": "application/javascript"}
        return resp.build_response(req)
    except Exception as e:
        return Response().build_internal_error({"message": str(e)})


from urllib.parse import urlparse, parse_qs


# Endpoint phục vụ đồ họa Web UI hiển thị cuộc trò chuyện với một Peer
@app.route("/chat", methods=["GET"])
def chat_page(req):
    """
    [Giao diện Chat Khủng] GET /chat
    - Mở trang hiển thị nội dung cuộc đàm thoại.
    - [NÂNG CẤP]: Hỗ trợ cả Chat 1-1 (cần peer, ip, port) và Chat Nhóm (cần group_name).
    """
    unauthorized = require_auth(req)
    if unauthorized:
        return unauthorized

    if not hasattr(req, "query_params") or req.query_params is None:
        req.query_params = {}
        parsed_url = urlparse(req.path)
        req.query_params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

    peer = req.query_params.get("peer")
    ip = req.query_params.get("ip")
    port = req.query_params.get("port")
    group_name = req.query_params.get("group_name")  # Lấy thêm tham số group_name

    # LẬP LUẬN LOGIC: Cho phép đi tiếp nếu có group_name HOẶC có đủ bộ 3 (peer, ip, port)
    if not group_name and not all([peer, ip, port]):
        return Response().build_bad_request(
            {
                "message": "Missing query param. Req: 'group_name' OR ('peer', 'ip', 'port')"
            }
        )

    # In log cho đẹp và dễ debug
    if group_name:
        print(f"[Peer] Đang mở giao diện chat nhóm: {group_name}")
    else:
        print(f"[Peer] Đang chat 1-1 với {peer} tại {ip}:{port}")

    try:
        req.path = "/chat.html"
        resp = Response(req)
        return resp.build_response(req)
    except Exception as e:
        print("Unexpected error:", e)
        return Response().build_internal_error({"message": str(e)})


# Endpoint định tuyến bỏ qua dữ liệu mặc định hệ thống của trình duyệt Chrome DevTools
@app.route("/.well-known/appspecific/com.chrome.devtools.json", methods=["GET"])
def dummy_chrome_devtools(req):
    resp = Response()
    resp.headers.update({"Content-Type": "application/json"})
    return resp.build_success({})


@app.route("/peer-disconnected", methods=["POST", "OPTIONS"])
def peer_disconnected(req):
    """
    [Lắng nghe] Xóa Peer khỏi danh bạ cục bộ khi họ Logout
    """
    try:
        cors_headers = (
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Methods: POST, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Content-Type\r\n"
        )
        if req.method == "OPTIONS":
            return ("HTTP/1.1 204 No Content\r\n" + f"{cors_headers}\r\n").encode(
                "utf-8"
            )

        data = json.loads(req.body)
        leaved_peer = data.get("username")

        if leaved_peer:
            # Xóa khỏi BiMap nội bộ
            connected_peer.remove_by_key(leaved_peer)
            print(f"[Peer] {leaved_peer} đã offline. Đã xóa khỏi danh bạ cục bộ.")

        return (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            f"{cors_headers}\r\n"
            '{"status": "ok"}'
        ).encode("utf-8")
    except Exception as e:
        return Response().build_internal_error({"messages": str(e)})


@app.route("/broadcast-logout", methods=["POST"])
def broadcast_logout(req):
    """
    Giao diện gọi hàm này khi user bấm Logout.
    Hàm sẽ quét BiMap, gửi thông báo đến các peer khác, sau đó mới báo lên Tracker.
    """
    my_username = req.cookies.get("username", "")
    all_friends = connected_peer.get_all()  # Lấy danh sách bạn bè hiện tại

    payload = {"username": my_username}

    # Bắn tin báo tử cho từng người bạn
    for friend_name, info in all_friends.items():
        ip = info[0]
        port = info[1]
        try:
            # Tận dụng lại hàm gửi mạng bất đồng bộ
            asyncio.run(
                send_to_peer_async(ip, port, payload, endpoint="/peer-disconnected")
            )
        except Exception as e:
            print(f"Lỗi khi báo offline cho {friend_name}: {e}")

    # Xóa sạch danh bạ cục bộ của mình
    connected_peer._key_to_value.clear()
    connected_peer._value_to_key.clear()

    return Response().build_success(
        {"status": "ok", "message": "Đã báo offline cho toàn mạng"}
    )


# --- Khối khởi chạy máy chủ ---
if __name__ == "__main__":
    """
        Điểm khởi động chương trình: parse tham số dòng lệnh
    và khởi chạy peer server AsynapRous.
    """

    parser = argparse.ArgumentParser(
        prog="PeerServer",
        description="Khởi động Peer Server cho hệ thống Hybrid Chat",
        epilog="Peer daemon của ứng dụng AsynapRous",
    )
    parser.add_argument(
        "--server-ip",
        type=str,
        default="0.0.0.0",
        help="Địa chỉ IP để bind server. Mặc định: 0.0.0.0",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=PORT,
        help=f"Cổng lắng nghe. Mặc định: {PORT}.",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["threading", "callback", "coroutine"],
        default="threading",
        help="Chế độ non-blocking. Mặc định: threading",
    )

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Ghi đè chế độ vào backend
    import daemon.backend as backend

    backend.mode_async = args.mode

    print(
        f"[ChatServer] Đang khởi chạy peer server ({args.mode}) tại http://{ip}:{port}"
    )
    app.prepare_address(ip, port)
    app.run()
