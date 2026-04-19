# test_1.py – Test ghi/đọc shared dict qua Manager Server
# Tài khoản dùng để test: MinhKhang (9001), ChanKien (9002), TrungQuan (9003), VoPham (9004)
import sys

sys.stdout.reconfigure(encoding="utf-8")
from multiprocessing.managers import BaseManager, DictProxy

print("--- Test Client: GHI (Bản Triệt Để) ---")

try:
    # 1. Đăng ký stub, nói rõ nó trả về một DictProxy
    BaseManager.register("get_peer_list", proxytype=DictProxy)

    address = ("127.0.0.1", 50001)
    authkey = b"secret"

    print("Đang kết nối tới Manager Server...")
    manager = BaseManager(address=address, authkey=authkey)
    manager.connect()
    print("Kết nối thành công!")

    # 2. Lấy proxy của DICT
    shared_dict_proxy = manager.get_peer_list()

    # 3. ĐỌC DỮ LIỆU (Dùng .copy())
    initial_data = shared_dict_proxy.copy()
    print(f"Trạng thái ban đầu (đọc từ server): {initial_data}")

    print("...Đã lấy proxy của DICT. Bắt đầu ghi.")

    # 4. GHI VÀO DICT PROXY (Dùng .update())
    # Dùng tài khoản thật: MinhKhang (MSSV: 2311399)
    key = "MinhKhang"
    value = {"ip": "127.0.0.1", "port": 9001}

    shared_dict_proxy.update({key: value})

    print(f"Đã GHI: {key} = {value}")

    # Dùng tài khoản thật: ChanKien (MSSV: 2211740)
    key2 = "ChanKien"
    value2 = {"ip": "127.0.0.1", "port": 9002}

    shared_dict_proxy.update({key2: value2})

    print(f"Đã GHI: {key2} = {value2}")

    # Dùng tài khoản thật: TrungQuan (MSSV: 2312817)
    key3 = "TrungQuan"
    value3 = {"ip": "127.0.0.1", "port": 9003}

    shared_dict_proxy.update({key3: value3})

    print(f"Đã GHI: {key3} = {value3}")

    # Dùng tài khoản thật: VoPham (MSSV: 2313946)
    key4 = "VoPham"
    value4 = {"ip": "127.0.0.1", "port": 9004}

    shared_dict_proxy.update({key4: value4})

    print(f"Đã GHI: {key4} = {value4}")

    # 5. ĐỌC LẠI (Dùng .copy())
    final_data = shared_dict_proxy.copy()
    print(f"Trạng thái dict HIỆN TẠI: {final_data}")

except ConnectionRefusedError:
    print("\n[LỖI] Không thể kết nối. Bạn đã chạy 'manager_server.py' chưa?")
except Exception as e:
    print(f"\n[LỖI] {e}")

print("Write client đã chạy xong.")
