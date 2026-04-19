"""
start_peer_cli.py – Phiên bản Chat Client chạy trên nền Màn Hình Đen (Giao diện CLI)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

File này dành riêng cho việc chat kiểu "Hacker", không cần đến trình duyệt web!
Bạn có thể kết nối nhiều Kênh, nhắn tin riêng, gửi broadcast trong mạng P2P hoàn toàn bằng câu lệnh.

Vai trò:
  - Khởi tạo cổng kết nối P2P cục bộ.
  - Xin Tracker tham gia các Mạng / Kênh dựa vào lệnh `/join`.
  - Hỗ trợ gõ lệnh tin nhắn trực tiếp từ Terminal.

Các lệnh hỗ trợ chính:
  /join <ip:port>           : Đăng ký tham gia một Kênh chat mới.
  /leave <ip:port>          : Thoát khỏi một Kênh.
  /list                     : Hiển thị sách tất cả những ai đang online.
  /list_channels            : Nhắc lại xem mình đang cắm chốt ở những Kênh nào.
  /broadcast <nội dung>     : Gét-gô, phát tin nhắn đến TẤT CẢ mọi người.
  /send <ip:port> <nội dung>: Gửi thư đến tất cả anh em trong MỘT Kênh cụ thể.
  /msg <tên> <nội dung>     : Mật khẩu, gửi tin nhắn đi thẳng vào túi người nhận (Đảm bảo riêng tư 1-1).
  /quit                     : Đóng app, chia tay cả làng.

Cách chạy 1 Peer mới (ví dụ: VoPham nghe port 9001):
  python start_peer_cli.py --username VoPham --port 9001
"""

# start_peer_cli.py - Client dòng lệnh xử lý kết nối P2P và các thao tác gửi/nhận tin nhắn
import socket
import threading
import argparse
import http.client
import json
import time
import os


class ChatClient:
    # Khởi tạo đối tượng Client với các thông tin cơ bản như tên và cổng P2P
    def __init__(self, username, client_port):
        self.username = username
        self.client_port = client_port

        # Thiết lập cấu trúc lưu trữ danh sách Peer
        # self.peer_list sẽ lưu trữ dữ liệu kiểu lồng nhau (nested dictionary) theo từng kênh
        # Format: { "127.0.0.1:8001": {"Bob": {...}, "Carol": {...}},
        #           "127.0.0.1:8002": {"David": {...}} }
        self.peer_list = {}
        self.channels = {}

        self.channel_file = f"{username}_channels.json"

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.client_ip = s.getsockname()[0]
            s.close()
        except Exception:
            self.client_ip = "127.0.0.1"

        self.server_socket = None
        self.running = True

    # --- Các hàm quản lý kênh (load/save/register/logout) ---
    # Phụ trách đọc/ghi cấu hình các kênh tham gia và khai báo/hủy khai báo với Tracker
    # Đọc danh sách các kênh đã tham gia trước đó từ file JSON cục bộ
    def load_channels(self):
        if os.path.exists(self.channel_file):
            try:
                with open(self.channel_file, "r") as f:
                    self.channels = json.load(f)
                    print(
                        f"[Client] Da tai {len(self.channels)} kenh tu {self.channel_file}"
                    )
            except Exception as e:
                print(f"[Client] Loi khi tai file channel: {e}")
        else:
            print("[Client] Khong tim thay file channel, bat dau voi danh sach rong.")

    # Ghi lại danh sách các kênh đang tham gia xuống file JSON để lưu trữ dứt điểm
    def save_channels(self):
        try:
            with open(self.channel_file, "w") as f:
                json.dump(self.channels, f, indent=4)
        except Exception as e:
            print(f"[Client] Loi khi luu file channel: {e}")

    # Gửi thông tin của mình (IP, Port, Tên) lên tất cả các Tracker để báo trạng thái online
    def register_with_all_trackers(self):
        print("[Client] Dang ky voi tat ca cac kenh...")
        if not self.channels:
            print("[Client] Ban chua tham gia kenh nao. Dung lenh: /join <ip:port>")
            return
        payload = {
            "username": self.username,
            "ip": self.client_ip,
            "port": self.client_port,
        }
        headers = {"Content-type": "application/json"}
        for location, info in self.channels.items():
            try:
                conn = http.client.HTTPConnection(info["ip"], info["port"], timeout=3)
                conn.request(
                    "POST", "/submit-info", json.dumps(payload).encode("utf-8"), headers
                )
                response = conn.getresponse()
                if response.status == 200:
                    print(f"[Client] Dang ky thanh cong voi kenh: {location}")
                else:
                    print(
                        f"[Client] Loi dang ky voi {location}: {response.status} {response.reason}"
                    )
                conn.close()
            except Exception as e:
                print(f"[Client] Khong the ket noi duoc kenh {location}: {e}")

    # Gửi yêu cầu thông báo đăng xuất tới tất cả Tracker để yêu cầu xóa thông tin của mình
    def logout_from_all_trackers(self):
        print(f"[Client] Dang thong bao thoat cho tat ca cac kenh...")
        payload = {"username": self.username}
        headers = {"Content-type": "application/json"}
        for location, info in self.channels.items():
            try:
                conn = http.client.HTTPConnection(info["ip"], info["port"], timeout=3)
                conn.request(
                    "POST", "/logout", json.dumps(payload).encode("utf-8"), headers
                )
                response = conn.getresponse()
                if response.status == 200:
                    print(f"[Client] Da logout khoi kenh {location}")
                else:
                    print(
                        f"[Client] Loi khi logout khoi {location}: {response.status} {response.reason}"
                    )
                conn.close()
            except Exception as e:
                print(f"[Client] Khong the ket noi tracker {location} de logout: {e}")

    #
    # --- HÀM LẤY DANH SÁCH PEER (GET_PEER_LIST) ---
    #
    def get_peer_list(self):
        """
        Lấy danh sách các peer từ TẤT CẢ các kênh và lưu trữ theo cấu trúc lồng nhau (nested dictionary)
        """
        print("[Client] Dang cap nhat danh sach peer tu tat ca cac kenh...")
        all_peers_by_channel = {}
        for location, info in self.channels.items():
            try:
                conn = http.client.HTTPConnection(info["ip"], info["port"], timeout=3)
                conn.request("GET", "/get-list")
                response = conn.getresponse()
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    peers_in_channel = data.get("peers", {})
                    # Xóa chính mình khỏi danh sách con (tránh việc hiển thị hoặc gửi chính mình)
                    if self.username in peers_in_channel:
                        del peers_in_channel[self.username]

                    # Lưu danh sách peer của kênh này
                    all_peers_by_channel[location] = peers_in_channel
                    print(
                        f"[Client] Kenh {location} co {len(peers_in_channel)} peers (khac)."
                    )
                conn.close()
            except Exception as e:
                print(f"[Client] Loi khi lay danh sach peer tu {location}: {e}")

        self.peer_list = (
            all_peers_by_channel  # Lưu trữ lại toàn bộ danh bạ từ tất cả các kênh
        )
        print(f"[Client] Da cap nhat. Tong so {len(self.channels)} kenh.")

    # --- Các hàm vận hành kết nối P2P (Mở dòng lắng nghe và nhận tin) ---
    # Khởi chạy một Socket Server chạy ngầm ở luồng riêng để liên tục chờ và nhận tin nhắn P2P
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("0.0.0.0", self.client_port))
        self.server_socket.listen(5)
        print(f"[Client] Dang lang nghe P2P tren port {self.client_port}")
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(
                    target=self.handle_peer_connection, args=(conn, addr)
                ).start()
            except socket.error:
                if self.running:
                    print("[Client] Loi server P2P")
                break
        print("[Client] Da dong server P2P.")

    # Xử lý các luồng kết nối P2P nhận được: Đọc nội dung tin nhắn và in trực tiếp ra màn hình
    def handle_peer_connection(self, conn, addr):
        try:
            data = conn.recv(1024).decode("utf-8")
            if data:
                print(
                    f"\r[Tin nhan P2P tu {addr[0]}]: {data}\n[Ban]: ",
                    end="",
                    flush=True,
                )
        except Exception as e:
            print(f"\r[Client] Loi khi nhan tin nhan P2P: {e}")
        finally:
            conn.close()

    #
    # --- HÀM GỬI BROADCAST (DÙNG CHO LỆNH /broadcast) ---
    #
    def broadcast_message(self, message):
        """
        Gửi tin nhắn Broadcast đến tất cả các peer (từ tất cả các kênh mà client đã tham gia)
        """
        print("[Client] Dang broadcast...")
        self.get_peer_list()  # Cập nhật danh sách Peer trước khi gửi

        full_message = f"[{self.username} - BROADCAST]: {message}"

        # Tạo một danh sách "phẳng" (gộp tất cả Peer từ các kênh) để tránh gửi trùng lặp cho người tham gia nhiều kênh
        all_peers_flat = {}
        for location, peers_in_channel in self.peer_list.items():
            all_peers_flat.update(peers_in_channel)

        if not all_peers_flat:
            print("[Client] Khong co peer nao de broadcast.")
            return

        print(f"[Client] Se gui broadcast den {len(all_peers_flat)} peers...")
        for peer_id, info in all_peers_flat.items():
            peer_ip = info.get("ip")
            peer_port = int(info.get("port"))
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_ip, peer_port))
                peer_socket.sendall(full_message.encode("utf-8"))
                peer_socket.close()
            except Exception as e:
                print(
                    f"[Client] Khong the gui broadcast den {peer_id} ({peer_ip}:{peer_port}): {e}"
                )

    #
    # --- HÀM GỬI TIN NHẮN TRỰC TIẾP (DÙNG CHO LỆNH /msg) ---
    #
    def send_direct_message(self, target_username, message):
        """
        Gửi tin nhắn riêng đến một peer cụ thể qua kết nối P2P
        """
        print(f"[Client] Dang gui tin nhan rieng cho {target_username}...")
        self.get_peer_list()  # Cập nhật danh bạ Peer

        target_info = None
        # Tìm kiếm peer đích trong danh sách của tất cả các kênh
        for location, peers_in_channel in self.peer_list.items():
            if target_username in peers_in_channel:
                target_info = peers_in_channel[target_username]
                break  # Đã tìm thấy Peer, thoát vòng lặp

        if not target_info:
            print(
                f"[Client] Loi: Khong tim thay nguoi dung '{target_username}' trong bat ky kenh nao."
            )
            return

        full_message = f"[{self.username} - RIENG]: {message}"
        peer_ip = target_info.get("ip")
        peer_port = int(target_info.get("port"))

        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_ip, peer_port))
            peer_socket.sendall(full_message.encode("utf-8"))
            peer_socket.close()
            print(f"[Client] Da gui tin nhan rieng cho {target_username}.")
        except Exception as e:
            print(
                f"[Client] Khong the gui den {target_username} ({peer_ip}:{peer_port}): {e}"
            )

    #
    # --- HÀM GỬI TIN ĐẾN MỘT KÊNH CỤ THỂ (DÙNG CHO LỆNH /send) ---
    #
    def send_channel_message(self, channel_location, message):
        """
        Gửi tin nhắn đến tất cả các peer hiện có mặt trong một kênh cụ thể.
        """
        # Kiểm tra xem client đã đăng ký tham gia kênh này chưa
        if channel_location not in self.channels:
            print(
                f"[Client] Loi: Ban chua tham gia kenh {channel_location}. Dung /join de tham gia."
            )
            return

        print(f"[Client] Dang gui tin nhan den kenh {channel_location}...")
        self.get_peer_list()  # Cập nhật danh bạ Peer

        # CHỈ lấy danh sách các peer thuộc về kênh được chỉ định
        peers_in_this_channel = self.peer_list.get(channel_location)

        if not peers_in_this_channel:
            print(
                f"[Client] Khong co peer nao trong kenh {channel_location} (ngoai ban)."
            )
            return

        full_message = f"[{self.username} @ {channel_location}]: {message}"

        print(
            f"[Client] Se gui den {len(peers_in_this_channel)} peers trong kenh {channel_location}..."
        )
        for peer_id, info in peers_in_this_channel.items():
            peer_ip = info.get("ip")
            peer_port = int(info.get("port"))
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_ip, peer_port))
                peer_socket.sendall(full_message.encode("utf-8"))
                peer_socket.close()
            except Exception as e:
                print(
                    f"[Client] Khong the gui (kenh) den {peer_id} ({peer_ip}:{peer_port}): {e}"
                )

    #
    # --- HÀM CHÍNH: KHỞI CHẠY CLIENT VÀ XỬ LÝ LỆNH ---
    #
    def start(self):
        """
        Khởi chạy toàn bộ quá trình (Load kênh, đăng ký, bật P2P server, và giao diện nhập lệnh)
        """
        self.load_channels()
        self.register_with_all_trackers()

        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()

        try:
            while True:
                msg = input("[Ban]: ")

                if msg.lower() == "/quit":
                    break

                elif msg.lower() == "/list_channels":
                    print("[Client] Cac kenh da tham gia:")
                    if not self.channels:
                        print(" (Chua tham gia kenh nao)")
                    for location in self.channels.keys():
                        print(f"- {location}")
                    continue

                elif msg.startswith("/join "):
                    try:
                        _, location = msg.split(" ", 1)
                        ip, port_str = location.split(":", 1)
                        port = int(port_str)
                        self.channels[location] = {"ip": ip, "port": port}
                        self.save_channels()
                        self.register_with_all_trackers()
                        print(f"[Client] Da tham gia va luu kenh: {location}")
                    except Exception as e:
                        print(
                            f"[Client] Loi cu phap. Su dung: /join <ip:port>. Loi: {e}"
                        )
                    continue

                elif msg.startswith("/leave "):
                    try:
                        _, location = msg.split(" ", 1)
                        if location in self.channels:
                            # TODO: Cần gọi API /logout cho riêng kênh này để xóa thông tin trên Tracker
                            del self.channels[location]
                            self.save_channels()
                            print(
                                f"[Client] Da roi kenh {location}. (Hay logout khoi kenh do thu cong neu can)"
                            )
                        else:
                            print(f"[Client] Ban chua tham gia kenh {location}")
                    except Exception as e:
                        print(
                            f"[Client] Loi cu phap. Su dung: /leave <ip:port>. Loi: {e}"
                        )
                    continue

                elif msg.lower() == "/list":
                    self.get_peer_list()
                    # In ra danh sách các peer đã được nhóm (phân loại) theo từng kênh
                    print(json.dumps(self.peer_list, indent=2))
                    continue

                elif msg.startswith("/msg "):
                    try:
                        _, target_username, message = msg.split(" ", 2)
                        self.send_direct_message(target_username, message)
                    except ValueError:
                        print(
                            "[Client] Loi: Cu phap sai. Su dung: /msg <username> <message>"
                        )
                    continue

                # --- XỬ LÝ LỆNH BROADCAST ---
                elif msg.startswith("/broadcast "):
                    try:
                        _, message = msg.split(" ", 1)
                        self.broadcast_message(message)
                    except ValueError:
                        print("[Client] Loi cu phap. Su dung: /broadcast <message>")
                    continue

                # --- XỬ LÝ LỆNH GỬI TIN NHẮN CHO KÊNH ---
                elif msg.startswith("/send "):
                    try:
                        # Cú pháp: /send <ip:port> <Nội dung tin nhắn>
                        _, location, message = msg.split(" ", 2)
                        self.send_channel_message(location, message)
                    except Exception as e:
                        print(
                            f"[Client] Loi cu phap. Su dung: /send <ip:port> <message>. Loi: {e}"
                        )
                    continue

                # Xử lý khi người dùng nhập sai lệnh, hoặc không gõ gì
                else:
                    if msg.startswith("/"):
                        print(f"[Client] Loi: Khong ro lenh '{msg}'.")
                    else:
                        print("[Client] Loi: Tin nhan phai bat dau bang mot lenh.")
                    print("Cac lenh hop le:")
                    print("  /send <ip:port> <message>   - Gui tin den KÊNH cu the")
                    print("  /broadcast <message>      - Gui tin den TAT CA cac kenh")
                    print("  /msg <username> <message>   - Gui tin nhan RIÊNG")
                    print(
                        "  /list                     - Xem danh sach peer (theo kenh)"
                    )
                    print("  /list_channels            - Xem cac kenh da tham gia")
                    print("  /join <ip:port>           - Tham gia mot kenh moi")
                    print("  /leave <ip:port>          - Roi mot kenh")
                    print("  /quit                     - Thoat")

        except KeyboardInterrupt:
            print("\n[Client] Dang thoat...")
        finally:
            self.running = False
            self.logout_from_all_trackers()
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self.client_ip, self.client_port))
                s.close()
            except:
                pass
            server_thread.join(1.0)
            print("[Client] Da thoat hoan toan.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P2P Chat Client (Multi-Channel)")
    parser.add_argument("--username", required=True, help="Ten cua ban (bat buoc)")
    parser.add_argument(
        "--port", type=int, required=True, help="Port P2P de ban lang nghe (bat buoc)"
    )

    args = parser.parse_args()

    client = ChatClient(args.username, args.port)
    client.start()
