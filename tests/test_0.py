# test.py – Test BiMap chống trùng qua Manager Server
# Tài khoản dùng để test: VoPham (9001), MinhDuc (9002), TrungQuan (9003), MinhKhang (9004)
import sys

sys.stdout.reconfigure(encoding="utf-8")
from multiprocessing.managers import BaseManager, DictProxy

print("--- Test Client: GỌI HÀM (Chống trùng Value) ---")

try:
    # 1. Đăng ký stub cho các hàm
    BaseManager.register("add_peer")
    BaseManager.register("remove_peer")
    # Vẫn cần DictProxy cho hàm get_peer_list
    BaseManager.register("get_peer_list", proxytype=DictProxy)

    address = ("127.0.0.1", 50001)
    authkey = b"secret"

    print("Đang kết nối tới Manager Server...")
    manager = BaseManager(address=address, authkey=authkey)
    manager.connect()
    print("Kết nối thành công!")

    # --- BẮT ĐẦU TEST ---

    # A. Thêm 'VoPham' với info_A (Peer 1 – port 9001)
    print("\n--- Test A: Thêm 'VoPham' ---")
    info_A = {"ip": "127.0.0.1", "port": 9001}
    success = manager.add_peer("VoPham", info_A)
    print(f"... Đã gọi add_peer('VoPham'). Kết quả: {success}")

    # B. Thêm 'MinhDuc' với info_B (Peer 2 – port 9002)
    print("\n--- Test B: Thêm 'MinhDuc' ---")
    info_B = {"ip": "127.0.0.1", "port": 9002}
    success = manager.add_peer("MinhDuc", info_B)
    print(f"... Đã gọi add_peer('MinhDuc'). Kết quả: {success}")

    # B2. Thêm 'TrungQuan' với info_C (Peer 3 – port 9003)
    print("\n--- Test B2: Thêm 'TrungQuan' ---")
    info_C = {"ip": "127.0.0.1", "port": 9003}
    success = manager.add_peer("TrungQuan", info_C)
    print(f"... Đã gọi add_peer('TrungQuan'). Kết quả: {success}")

    # B3. Thêm 'MinhKhang' với info_D (Peer 4 – port 9004)
    print("\n--- Test B3: Thêm 'MinhKhang' ---")
    info_D = {"ip": "127.0.0.1", "port": 9004}
    success = manager.add_peer("MinhKhang", info_D)
    print(f"... Đã gọi add_peer('MinhKhang'). Kết quả: {success}")

    # C. Lấy danh sách (sẽ có 4 peer)
    list1 = manager.get_peer_list().copy()
    print(f"\nList hiện tại ({len(list1)} peers): {list1}")

    # D. Thêm 'ChanKien' với info_A (TRÙNG GIÁ TRỊ với VoPham – cùng IP:Port)
    print("\n--- Test D: Thêm 'ChanKien' (TRÙNG VALUE – cùng port 9001) ---")
    success = manager.add_peer("ChanKien", info_A)
    print(f"... Đã gọi add_peer('ChanKien'). Kết quả: {success}")  # <-- Phải là False

    # E. Lấy danh sách cuối cùng (Charlie không được thêm)
    print("\n--- Test E: Lấy danh sách cuối cùng ---")
    final_list = manager.get_peer_list().copy()
    print(f"List cuối cùng: {final_list}")

except ConnectionRefusedError:
    print("\n[LỖI] Không thể kết nối. Bạn đã chạy 'manager_server.py' chưa?")
except Exception as e:
    print(f"\n[LỖI] {e}")

print("\nClient test đã chạy xong.")
