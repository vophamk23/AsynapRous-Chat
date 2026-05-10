"""
start_tracker.py – Máy chủ Tracker cho hệ thống Hybrid Chat
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Module này khởi động máy chủ Tracker – thành phần tập trung
quản lý danh sách peer trong mô hình Hybrid P2P.

Vai trò Tracker:
  - Xác thực người dùng qua form đăng nhập (HTTP Cookie)
  - Tiếp nhận đăng ký IP:Port của các peer qua /submit-info
  - Trả danh sách peer đang hoạt động qua /get-list
  - Phục vụ file tĩnh (HTML, CSS, JS) cho giao diện web

Các route đã đăng ký:
  POST /login          – Xác thực tài khoản, set cookie auth
  GET  /login          – Trả trang đăng nhập
  GET  /submit-info    – Trả form đăng ký P2P
  POST /submit-info    – Nhận đăng ký IP:Port từ peer
  GET  /get-list       – Trả danh sách peer (JSON + CORS)
  POST /save-tracker   – Lưu thông tin tracker vào file JSON

Cách chạy:
  python start_tracker.py --server-ip 0.0.0.0 --server-port 8001
"""

import json
import argparse
from db.account import select_user, create_connection
from daemon.request import Request
from daemon.response import Response
from urllib.parse import *

# from multiprocessing.managers import BaseManager


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
peer_list = {}


def require_auth(req):
    """
    Xác thực cookie trên Tracker. Nếu chưa đăng nhập, chuyển hướng về trang /login.
    """
    auth = req.cookies.get("auth", "") if req.cookies else ""
    if auth == "true":
        return None
    print("[Auth] Chưa đăng nhập Tracker, chuyển hướng về /login")
    return (
        "HTTP/1.1 302 Found\r\n"
        "Location: /login\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")


# --- Giai đoạn 1: Client-Server (Tracker) ---


# Endpoint tiếp nhận và xác thực thông tin tài khoản, cấp phát phiên đăng nhập trực tuyến
@app.route("/login", methods=["POST"])
def login(req):
    """
    [API Xác thực] POST /login
    - Nhận dữ liệu `username` và `password` từ form đăng nhập.
    - Đọc file database SQLite (`db/account.db`) để đối chiếu tài khoản.
    - Nếu khớp: Cấp một "giấy phép" (Cookie) cho trình duyệt và điều hướng mở trang chủ (index.html).
    - Nếu sai mật khẩu: Báo lỗi 401 Unauthorized (Không được phép).
    """
    from urllib.parse import parse_qs

    parsed = parse_qs(req.body, keep_blank_values=True)

    username = parsed.get("username", [""])[0]
    password = parsed.get("password", [""])[0]

    conn = create_connection("db/account.db")
    auth = select_user(conn, username)
    resp = Response()
    print(f"[Server] Login attempt: {username}")
    if auth:
        if password == auth[1]:
            # Đăng nhập thành công: set cookie và chuyển đến trang chủ
            resp.cookies.clear()
            resp.cookies["auth"] = "true; Path=/"
            resp.cookies["username"] = username
            # Giả lập GET /index.html để trả trang sau khi đăng nhập thành công
            req.path = "/index.html"
            req.method = "GET"
            print(f"[Tracker] Login success: {username}")
            return resp.build_response(req)

    print(f"[Tracker] Login failed: {username}")
    return resp.build_unauthorized()


# Endpoint phục vụ trả về giao diện trang đăng nhập hệ thống (HTML)
@app.route("/login", methods=["GET"])
def login_form(req):
    """
    [Giao diện Web] GET /login
    - Chỉ đơn giản là mở và trả về nguyên văn file `login.html`
      để hiển thị form đăng nhập màu mè trên trình duyệt.
    """
    print(f"[ChatServer] Nhận yêu cầu /submit-info...")

    try:
        req.path = "/login.html"
        return Response().build_response(req)
    except Exception as e:
        print(f"[ChatServer] Lỗi không xác định: {e}")
        return {"status": "error", "message": str(e)}


# Endpoint phục vụ trang Web chứa biểu mẫu khai báo địa chỉ mạng (IP, Port) cho các Peer
@app.route("/submit-info", methods=["GET"])
def submit_form(req):
    """
    [Giao diện Web] GET /submit-info
    - Trả về nguyên văn file `submit.html`.
    - Đây là trang hiển thị 2 ô trống yêu cầu người dùng điền IP và Port của máy mình
      để đăng ký tham gia vào mạng lưới chat P2P.
    - Yêu cầu đăng nhập.
    """
    unauth = require_auth(req)
    if unauth:
        return unauth

    try:
        req.path = "/submit.html"
        return Response().build_response(req)
    except Exception as e:
        print(f"[ChatServer] Lỗi không xác định: {e}")
        return {"status": "error", "message": str(e)}


# Endpoint lưu trữ IP được gửi tới và bổ sung thông tin Peer đó vào danh bạ của máy chủ Tracker
@app.route("/submit-info", methods=["POST"])
def submit_info(req):
    """
    [API Đăng ký Mạng] POST /submit-info
    - Trái tim của Tracker! Khi Peer bấm Submit trên giao diện gửi IP:Port về đây:
    - 1. Nó lấy `username` bí mật giấu trong Cookie lúc bạn đăng nhập.
    - 2. Đọc IP và Port.
    - 3. Lưu tất cả vào cuốn danh bạ liên lạc chung tên là `peer_list`.
    - Từ đây, tài khoản của bạn chính thức "Online" và đợi người khác kiếm.
    """
    print(f"[ChatServer] Nhận yêu cầu /submit-info...")

    unauth = require_auth(req)
    if unauth:
        return unauth

    try:
        body = req.body
        if body.strip().startswith("{"):
            data = json.loads(body)
            peer_id = data.get("username") or req.cookies.get("username")
            peer_ip = data.get("ip")
            peer_port = data.get("port")
        else:
            data = parse_qs(body)
            peer_id = req.cookies.get("username")
            peer_ip = data.get("ip")[0] if data.get("ip") else None
            peer_port = data.get("port")[0] if data.get("port") else None

        if peer_id and peer_ip and peer_port:

            for existing_id, info in peer_list.items():
                if info["ip"] == peer_ip and str(info["port"]) == str(peer_port):
                    if existing_id != peer_id:
                        # Nếu IP:Port này đã bị người khác chiếm
                        error_msg = f"Địa chỉ {peer_ip}:{peer_port} đã bị chiếm bởi {existing_id}!"
                        print(
                            f"[ChatServer] TỪ CHỐI: {peer_id} cố gắng dùng port của {existing_id}"
                        )
                        return Response().build_bad_request(
                            {"status": "error", "message": error_msg}
                        )

            peer_list[peer_id] = {"ip": peer_ip, "port": peer_port}
            print(peer_list)
            print(f"[ChatServer] Peer đã đăng ký: {peer_id} -> {peer_ip}:{peer_port}")
            resp = Response()
            return resp.build_success(
                {"status": "success", "message": "Submit successfully."}
            )
        else:
            return Response().build_bad_request(
                {"status": "error", "message": "Missing ip, port, or username"}
            )

    except json.JSONDecodeError:
        print("[ChatServer] Lỗi: Body không phải là JSON hợp lệ")
        return Response().build_bad_request(
            {"status": "error", "message": "Invalid JSON body"}
        )
    except Exception as e:
        print(f"[ChatServer] Lỗi không xác định: {e}")
        return Response().build_internal_error({"status": "error", "message": str(e)})


# Cấu trúc: {"Tên Nhóm": {"owner": "Trưởng nhóm", "members": ["Thành viên 1", "Thành viên 2"]}}
group_list = {}


@app.route("/create-group", methods=["POST", "OPTIONS"])
def create_group(req):
    """[API Group] Tạo nhóm và ĐÁNH DẤU CHỦ SỞ HỮU."""
    cors_headers = "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: POST, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n"
    if req.method == "OPTIONS":
        return ("HTTP/1.1 204 No Content\r\n" + f"{cors_headers}\r\n").encode("utf-8")

    try:
        data = json.loads(req.body)
        group_name = data.get("group_name")
        username = data.get("username") or (
            req.cookies.get("username") if req.cookies else None
        )

        if not group_name or not username:
            body = json.dumps(
                {"status": "error", "message": "Thiếu tên nhóm hoặc chưa đăng nhập"}
            )
            return (
                f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
            ).encode("utf-8")

        if group_name in group_list:
            body = json.dumps(
                {"status": "error", "message": f"Nhóm '{group_name}' đã tồn tại!"}
            )
            return (
                f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
            ).encode("utf-8")

        initial_members = data.get("initial_members", [])
        if not isinstance(initial_members, list):
            initial_members = []
            
        members_list = [username]
        for m in initial_members:
            if m not in members_list:
                members_list.append(m)

        # NÂNG CẤP: Lưu ai là chủ nhóm và các thành viên khởi tạo
        group_list[group_name] = {"owner": username, "members": members_list}
        print(f"[Tracker] {username} đã khởi tạo nhóm: {group_name}")

        body = json.dumps(
            {
                "status": "success",
                "message": "Tạo nhóm thành công",
                "group_name": group_name,
            }
        )
        return (
            f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
        ).encode("utf-8")
    except Exception as e:
        return Response().build_internal_error({"message": str(e)})


@app.route("/add-to-group", methods=["POST", "OPTIONS"])
def add_to_group(req):
    """[API Group MỚI] Chủ nhóm gọi hàm này để nạp thêm thành viên."""
    cors_headers = "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: POST, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n"
    if req.method == "OPTIONS":
        return ("HTTP/1.1 204 No Content\r\n" + f"{cors_headers}\r\n").encode("utf-8")

    try:
        data = json.loads(req.body)
        group_name = data.get("group_name")
        target_users = data.get("target_users", []) # Hỗ trợ mảng nhiều user
        target_user_single = data.get("target_user") # Tương thích ngược
        if target_user_single and target_user_single not in target_users:
            target_users.append(target_user_single)
            
        requester = data.get("username") or (
            req.cookies.get("username") if req.cookies else None
        )  # Người bấm nút

        if group_name not in group_list:
            body = json.dumps({"status": "error", "message": "Nhóm không tồn tại"})
            return (
                f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
            ).encode("utf-8")

        # KIỂM TRA QUYỀN: Chỉ Owner mới được quyền add (Thích thì bạn có thể mở rộng cho mọi member)
        if group_list[group_name]["owner"] != requester:
            body = json.dumps(
                {
                    "status": "error",
                    "message": "Chỉ Trưởng nhóm mới có quyền thêm người!",
                }
            )
            return (
                f"HTTP/1.1 403 Forbidden\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
            ).encode("utf-8")

        added_count = 0
        for user in target_users:
            if user not in group_list[group_name]["members"]:
                group_list[group_name]["members"].append(user)
                print(f"[Tracker] {requester} đã add {user} vào nhóm {group_name}")
                added_count += 1

        body = json.dumps(
            {
                "status": "success",
                "message": f"Đã thêm {added_count} thành viên vào nhóm {group_name}",
            }
        )
        return (
            f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
        ).encode("utf-8")
    except Exception as e:
        return Response().build_internal_error({"message": str(e)})


@app.route("/get-group-members", methods=["GET", "OPTIONS"])
def get_group_members(req):
    """[API Group] Lấy IP/Port của các thành viên."""
    cors_headers = "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n"
    if req.method == "OPTIONS":
        return ("HTTP/1.1 204 No Content\r\n" + f"{cors_headers}\r\n").encode("utf-8")

    try:
        group_name = req.query_params.get("group_name")
        if group_name not in group_list:
            body = json.dumps({"status": "error", "message": "Nhóm không tồn tại"})
            return (
                f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
            ).encode("utf-8")

        members_info = []
        # Sửa lại cách lặp lấy danh sách thành viên
        for member in group_list[group_name]["members"]:
            if member in peer_list:
                members_info.append(
                    {
                        "username": member,
                        "ip": peer_list[member]["ip"],
                        "port": peer_list[member]["port"],
                    }
                )

        body = json.dumps({"status": "success", "members": members_info})
        return (
            f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
        ).encode("utf-8")
    except Exception as e:
        return Response().build_internal_error({"message": str(e)})


@app.route("/my-groups", methods=["GET", "OPTIONS"])
def my_groups(req):
    """[API Group] Lấy danh sách các nhóm mà user hiện tại đang tham gia."""
    cors_headers = "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n"
    if req.method == "OPTIONS":
        return ("HTTP/1.1 204 No Content\r\n" + f"{cors_headers}\r\n").encode("utf-8")

    try:
        username = req.query_params.get("username") or (
            req.cookies.get("username") if req.cookies else None
        )
        if not username:
            body = json.dumps({"status": "error", "message": "Chưa đăng nhập"})
            return (
                f"HTTP/1.1 401 Unauthorized\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
            ).encode("utf-8")

        my_group_list = []
        # Quét toàn bộ danh sách nhóm trên RAM
        for g_name, g_info in group_list.items():
            # Nếu tên mình có trong danh sách members của nhóm đó
            if username in g_info["members"]:
                my_group_list.append({"group_name": g_name, "owner": g_info["owner"]})

        body = json.dumps({"status": "success", "groups": my_group_list})
        return (
            f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n{cors_headers}Content-Length: {len(body.encode('utf-8'))}\r\n\r\n{body}"
        ).encode("utf-8")
    except Exception as e:
        return Response().build_internal_error({"message": str(e)})


@app.route("/logout", methods=["POST"])
def logout(req):
    """
    [API Đăng xuất Mạng] POST /logout
    Xóa tài khoản khỏi danh bạ liên lạc của mạng.
    """
    try:
        body = req.body
        peer_id = None
        if body.strip().startswith("{"):
            data = json.loads(body)
            peer_id = data.get("username") or req.cookies.get("username")
        else:
            peer_id = req.cookies.get("username")

        if peer_id and peer_id in peer_list:
            del peer_list[peer_id]
            print(f"[ChatServer] Peer đã rời mạng: {peer_id}")

        resp = Response()
        resp.cookies["auth"] = "false; Path=/; Max-Age=0"
        resp.cookies["username"] = "deleted; Path=/; Max-Age=0"

        return resp.build_success({"status": "success"})
    except Exception as e:
        return Response().build_internal_error({"status": "error", "message": str(e)})


# Endpoint trích xuất và phân phối toàn bộ danh bạ thiết bị của hệ thống (hỗ trợ luồng CORS)
@app.route("/get-list", methods=["GET", "OPTIONS"])
def get_list(req):
    """
    [API Cung cấp Danh bạ] GET /get-list
    - Tra cứu toàn bộ "cuốn danh bạ" `peer_list` hiện có mặt trên Tracker.
    - Khi Peer (hoặc giao diện Web của Peer) mạn phép gọi hàm này, Tracker
      sẽ đóng gói danh bạ thành JSON và trả về.
    - Đặc biệt hỗ trợ khối `OPTIONS` báo mã 204 để xử lý triệt để lỗi
      chặn chéo tên miền CORS của các trình duyệt hiện đại.
    """
    cors_headers = (
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        "Access-Control-Allow-Headers: Content-Type\r\n"
    )

    # Preflight OPTIONS request – trả 204 để browser cho phép CORS
    if req.method == "OPTIONS":
        return ("HTTP/1.1 204 No Content\r\n" f"{cors_headers}\r\n").encode("utf-8")

    # GET: trả dữ liệu peer_list dưới dạng JSON
    data = {"status": "success", "peers": dict(peer_list)}
    body = json.dumps(data)
    content_length = len(body)
    print(f"[Response] Get list successfully, return {peer_list}")
    return (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {content_length}\r\n"
        f"{cors_headers}\r\n"
        f"{body}"
    ).encode("utf-8")


# Endpoint phục vụ tải các tệp tài nguyên định dạng tĩnh (CSS)
@app.route("/styles.css")
def style(req):
    """[Tài nguyên tĩnh] Phục vụ file giao diện CSS (làm đẹp web)."""
    resp = Response()
    return resp.build_response(req)


# Endpoint phục vụ tải tài nguyên ảnh biểu tượng tĩnh (Icon)
@app.route("/favicon.ico")
def favicon(req):
    """[Tài nguyên tĩnh] Phục vụ logo nhỏ xinh trên thanh tab trình duyệt."""
    resp = Response()
    return resp.build_response(req)


# Endpoint tiện ích hỗ trợ lưu trữ IP/Port mặc định của Tracker lên file cấu hình tĩnh
@app.route("/save-tracker", methods=["POST"])
def save_tracker(req):
    """
    [API Lưu nháp IP Tracker] POST /save-tracker
    - Một tiện ích nhỏ: Xuất địa chỉ IP và Port của chính máy Tracker này
      ra một file text cài đặt là `tracker.json`.
    - Sau này client chỉ cần đọc file này là biết Tracker nằm bến phương nào để kết nối tới.
    """
    resp = Response()
    try:
        data = json.loads(req.body)
        tracker_ip = data.get("trackerIP")
        tracker_port = data.get("trackerPort")
        if not tracker_ip or not tracker_port:
            return resp.build_bad_request({"error": "Missing tracker info"})

        # Lưu vào file tracker.json
        with open("tracker.json", "w") as f:
            json.dump({"trackerIP": tracker_ip, "trackerPort": tracker_port}, f)

        return resp.build_success({"status": "success"})

    except Exception as e:
        return resp.build_internal_error({"error": str(e)})


# --- Khối khởi chạy máy chủ ---
if __name__ == "__main__":
    """
    Điểm khởi động chương trình: parse tham số dòng lệnh
    và khởi chạy máy chủ AsynapRous (Tracker).
    """

    parser = argparse.ArgumentParser(
        prog="ChatServer",
        description="Khởi động máy chủ Hybrid Chat (Tracker)",
        epilog="Tracker daemon của ứng dụng AsynapRous",
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
        f"[ChatServer] Đang khởi chạy máy chủ tracker ({args.mode}) tại http://{ip}:{port}"
    )
    app.prepare_address(ip, port)
    app.run()
