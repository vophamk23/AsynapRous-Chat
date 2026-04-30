📋 TÀI LIỆU DEMO – Assignment 1 MMT (CO3093/CO3094)

**Tên Đề tài:** Implement non-blocking HTTP server and chat application (AsynapRous)

## PHẦN A – TOÀN BỘ YÊU CẦU ĐỀ BÀI & FILE HIỆN THỰC

## 🔷 Mục 2.1 – Non-blocking Mechanism (2 điểm)

> Xây dựng cơ chế xử lý nhiều kết nối cùng lúc, không bị chặn (blocking)

| Yêu cầu                                   | File hiện thực                                        | Chức năng                                                                                          |
| ----------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Multi-thread – mỗi kết nối 1 thread riêng | `daemon/backend.py` → `run_backend()`                 | Khi client kết nối vào, tạo `threading.Thread` mới để xử lý, main thread tiếp tục nhận kết nối mới |
| Multi-thread ở tầng Proxy                 | `daemon/proxy.py` → `run_proxy()`                     | Proxy server cũng dùng threading cho mỗi client, kèm round-robin load balancing                    |
| Coroutine / asyncio                       | `daemon/httpadapter.py` → `handle_client_coroutine()` | Phiên bản async dùng `async/await`, `await reader.read()` không block event loop                   |
| Callback / Selectors                      | `daemon/backend.py` → import `selectors`              | Khai báo cơ chế event-driven (1 thread theo dõi nhiều socket)                                      |
| Framework tự viết                         | `daemon/asynaprous.py` → class `AsynapRous`           | Router decorator thông minh (Sync/Async) tự viết bằng Python thuần                                 |
| Request parser                            | `daemon/request.py` → class `Request`                 | Parse HTTP request line, headers, cookies, query params                                            |
| Response builder                          | `daemon/response.py` → class `Response`               | Build HTTP response 200/400/401/404/500, Set-Cookie header                                         |
| HTTP Adapter                              | `daemon/httpadapter.py` → class `HttpAdapter`         | Nhận kết nối, đọc request, dispatch đến handler hoặc serve file tĩnh                               |

## 🔷 Mục 2.2 – HTTP Authentication (2 điểm)

> Xác thực người dùng qua Cookie theo RFC 6265 và RFC 7235

| Yêu cầu                              | File hiện thực                                           | Chức năng                                                          |
| ------------------------------------ | -------------------------------------------------------- | ------------------------------------------------------------------ |
| `GET /login` → trả form đăng nhập    | `start_tracker.py` → `login_form()`                      | Serve file `www/login.html`                                        |
| Form đăng nhập HTML                  | `www/login.html`                                         | Form nhập username/password, gửi POST /login qua fetch()           |
| `POST /login` → validate credentials | `start_tracker.py` → `login()`                           | Parse body, truy vấn SQLite DB, so khớp password                   |
| Database tài khoản                   | `db/account.py` + `db/account.db`                        | SQLite: bảng `account(username, password)`, hàm `select_user()`    |
| Set-Cookie sau login thành công      | `daemon/response.py` → `build_response_header()`         | Xuất `Set-Cookie: auth=true; Path=/` và `Set-Cookie: username=xxx` |
| `GET /index.html` → kiểm tra cookie  | `daemon/httpadapter.py` → `handle_client()` line 276-292 | Đọc `req.cookies.get("auth")`, nếu không phải `"true"` → 401       |
| `401 Unauthorized` response          | `daemon/response.py` → `build_unauthorized()`            | Build HTTP 401 response theo RFC 7235                              |
| Trang chủ sau login                  | `www/index.html`                                         | Trang được bảo vệ, chỉ vào được khi có cookie auth=true            |

## 🔷 Mục 2.3 – Hybrid Chat Application (3 điểm)

### Giai đoạn 1: Client-Server / Tracker (1 điểm)

> Server trung tâm biết địa chỉ (IP:Port) của tất cả peer đang online

| Yêu cầu                             | File hiện thực                        | Chức năng                                                           |
| ----------------------------------- | ------------------------------------- | ------------------------------------------------------------------- |
| Peer registration – đăng ký IP:Port | `start_tracker.py` → `submit_info()`  | Nhận POST /submit-info, lưu vào `peer_list` dict in-memory          |
| Tracker update – cập nhật danh sách | `start_tracker.py` → `peer_list = {}` | Dict lưu `{username: {ip, port}}` trong bộ nhớ                      |
| Peer discovery – tìm kiếm peer      | `start_tracker.py` → `get_list()`     | GET /get-list trả JSON toàn bộ peer_list + CORS headers             |
| Save tracker info                   | `start_tracker.py` → `save_tracker()` | POST /save-tracker lưu IP:Port tracker vào file `tracker.json`      |
| Logout khi thoát                    | `start_tracker.py` → `logout()`       | Xóa peer khỏi peer_list khi peer gửi POST /logout                   |
| UI đăng ký                          | `www/submit.html`                     | Form nhập IP:Port, submit lên tracker rồi redirect sang peer server |

### Giai đoạn 2: Peer-to-Peer (2 điểm)

> Peer giao tiếp trực tiếp với nhau, không qua server trung tâm

| Yêu cầu                 | File hiện thực                                    | Chức năng                                                    |
| ----------------------- | ------------------------------------------------- | ------------------------------------------------------------ |
| Peer server (HTTP)      | `start_peer.py`                                   | Mỗi peer chạy HTTP server riêng nhận request từ peer khác    |
| Peer management (BiMap) | `start_peer.py` → class `BiMap`                   | Dict 2 chiều: username ↔ (ip, port), tra cứu O(1) cả 2 chiều |
| Connection setup        | `start_peer.py` → `add_peer()` + `POST /add-list` | Thêm peer vào BiMap khi bấm Connect                          |
| Nhận tin nhắn P2P       | `start_peer.py` → `POST /receive-message`         | Peer khác gửi tin đến, lưu vào `chat_messages` dict          |
| Gửi tin nhắn            | `start_peer.py` → `POST /send-message`            | Lưu tin nhắn đã gửi vào lịch sử phía mình                    |
| Lấy lịch sử chat        | `start_peer.py` → `GET /get-messages?peer=xxx`    | Trả danh sách tin nhắn với peer cụ thể                       |
| Xem peer đã kết nối     | `start_peer.py` → `GET /get-connected-peer`       | Trả BiMap dưới dạng JSON                                     |
| Lấy tracker info        | `start_peer.py` → `GET /get-tracker`              | Đọc `tracker.json` trả về IP:Port tracker                    |
| Broadcast (CLI)         | `start_peer_cli.py` → `broadcast_message()`       | Gửi TCP trực tiếp đến tất cả peer trong tất cả kênh          |
| Direct message (CLI)    | `start_peer_cli.py` → `send_direct_message()`     | Gửi TCP trực tiếp đến 1 peer cụ thể                          |
| Send to channel (CLI)   | `start_peer_cli.py` → `send_channel_message()`    | Gửi TCP đến tất cả peer trong 1 kênh cụ thể                  |
| Nhận P2P (CLI)          | `start_peer_cli.py` → `handle_peer_connection()`  | Lắng nghe TCP, in tin nhắn nhận được ra terminal             |

### Channel Management

| Yêu cầu            | File hiện thực                                                          | Chức năng                                    |
| ------------------ | ----------------------------------------------------------------------- | -------------------------------------------- |
| Channel listing    | `start_peer.py` → `GET /view-my-channels` + `www/view-my-channels.html` | Hiển thị danh sách peer đã kết nối           |
| Message display    | `www/chat.html` + `static/js/chat.js`                                   | Cửa sổ chat, tự render tin nhắn, có scroll   |
| Message submission | `static/js/chat.js` → `sendMessage()` + `saveMessage()`                 | Gửi tin qua fetch(), lưu lịch sử             |
| Polling nhận tin   | `static/js/chat.js` → `setInterval(fetchMessages, 1000)`                | Tự động load tin nhắn mới mỗi 1 giây         |
| Active peers UI    | `www/active-peers.html` + `static/js/active-peers.js`                   | Bảng danh sách peer, nút Connect/Connected   |
| No edit/delete     | Không có route nào                                                      | Đúng yêu cầu – tin nhắn bất biến sau khi gửi |

## 📁 Cấu trúc file quan trọng

```
assign1-mmt-finished-main/
├── daemon/
│   ├── backend.py         - Non-blocking (threading + asyncio + selectors)
│   ├── proxy.py           - Proxy + round-robin load balancing
│   ├── httpadapter.py     - HTTP dispatch + Cookie auth check
│   ├── request.py         - Parse HTTP request, cookie, query params
│   ├── response.py        - Build HTTP response (200/400/401/404/500)
│   ├── asynaprous.py      - AsynapRous framework (routing decorator)
│   └── dictionary.py      - CaseInsensitiveDict
├── start_tracker.py       - Tracker: login, submit-info, get-list
├── start_peer.py          - Peer server: add-list, send/receive msg
├── start_peer_cli.py      - CLI: broadcast, direct, join/leave channel
├── start_proxy.py         - Proxy server (load balancer)
├── start_backend.py       - Backend server đơn giản (demo non-blocking)
├── start_sampleapp.py     - Ứng dụng mẫu AsynapRous (demo framework)
├── manager.py             - Shared state manager (multiprocessing)
├── www/
│   ├── login.html           - Trang đăng nhập
│   ├── index.html           - Trang chủ (cần auth)
│   ├── submit.html          - Form đăng ký IP:Port
│   ├── chat.html            - Trang chat P2P
│   ├── active-peers.html    - Danh sách peers
│   └── view-my-channels.html- Kênh đã kết nối
├── static/js/
│   ├── chat.js              - Gửi/nhận tin, polling 1s
│   └── active-peers.js      - Load peer list, nút Connect
├── db/
│   ├── account.db           - SQLite user database
│   └── account.py           - select_user(), create_table(), CLI quản lý
├── tests/                 - Bộ test: BiMap, Manager, batch scripts
├── config/proxy.conf      - Routing config
├── run_web.bat            - Khởi động toàn bộ hệ thống Web (7 terminal)
└── run_cli.bat                - Khởi động toàn bộ hệ thống CLI (7 terminal)
```

## 🛠 Quản lý tài khoản DB

> File: `db/account.py` – Chạy trực tiếp từ dòng lệnh

### Danh sách tài khoản hiện tại:

| Username  | Password (MSSV) |
| --------- | --------------- |
| VoPham    | 2313946         |
| MinhDuc   | 2310797         |
| TrungQuan | 2312817         |
| MinhKhang | 2311399         |
| ChanKien  | 2211740         |

### Các lệnh quản lý:

```bash
# Xem danh sách tài khoản
python db/account.py list

# Thêm tài khoản mới
python db/account.py add <username> <password>
# Ví dụ:
python db/account.py add NguyenVanA 1234567

# Xóa 1 tài khoản
python db/account.py delete <username>
# Ví dụ:
python db/account.py delete ChanKien

# Xóa toàn bộ tài khoản (yêu cầu xác nhận "yes")
python db/account.py reset
```

## PHẦN B – KỊCH BẢN DEMO

## 🚀 KHỞI ĐỘNG HỆ THỐNG (Làm trước khi demo)

### Cách 1: Tự động – Chạy file `.bat` (Khởi Động Nhanh Trên Windows)

Dự án cung cấp sẵn tệp tin `.bat` chạy native trực tiếp trên Windows (KHÔNG CẦN CÀI WSL) để bạn dễ dàng trình diễn:

```bash
# Trình diễn Giao diện Web thông qua:
./run_web.bat
```

> Khi chạy, hệ thống sẽ tự động bật nhảy 7 cửa sổ Windows CMD riêng lẻ đại diện cho Trackers và Các Peers.

### Cách 2: Thủ công – Mở từng terminal

**Terminal 1 – Tracker Server (port 9000):**

```bash
python start_tracker.py --server-ip 127.0.0.1 --server-port 9000
```

**Terminal 2 – Peer 1 / VoPham (port 9001):**

```bash
python start_peer.py --server-ip 127.0.0.1 --server-port 9001
```

**Terminal 3 – Peer 2 / MinhDuc (port 9002):**

```bash
python start_peer.py --server-ip 127.0.0.1 --server-port 9002
```

**Terminal 4 – Peer 3 / TrungQuan (port 9003):**

```bash
python start_peer.py --server-ip 127.0.0.1 --server-port 9003
```

**Terminal 5 – Peer 4 / MinhKhang (port 9004) – nếu cần:**

```bash
python start_peer.py --server-ip 127.0.0.1 --server-port 9004
```

**Terminal 6 – Peer 5 / ChanKien (port 9005) – nếu cần:**

```bash
python start_peer.py --server-ip 127.0.0.1 --server-port 9005
```

> ✅ Chờ đến khi tất cả terminal hiện `[Backend] Listening on port XXXX` là sẵn sàng

## 🌐 BẢNG CỔNG (PORT) CỦA HỆ THỐNG

| Dịch vụ                | Port | URL truy cập            | Mô tả                                          |
| ---------------------- | ---- | ----------------------- | ---------------------------------------------- |
| **Tracker Server**     | 9000 | `http://127.0.0.1:9000` | Server trung tâm: login, submit-info, get-list |
| **Peer 1** (VoPham)    | 9001 | `http://127.0.0.1:9001` | Peer server: chat, active-peers, messages      |
| **Peer 2** (MinhDuc)   | 9002 | `http://127.0.0.1:9002` | Peer server: chat, active-peers, messages      |
| **Peer 3** (TrungQuan) | 9003 | `http://127.0.0.1:9003` | Peer server: chat, active-peers, messages      |
| **Peer 4** (MinhKhang) | 9004 | `http://127.0.0.1:9004` | Peer server: chat, active-peers, messages      |
| **Peer 5** (ChanKien)  | 9005 | `http://127.0.0.1:9005` | Peer server: chat, active-peers, messages      |
| **Proxy**              | 8080 | `http://127.0.0.1:8080` | Load balancer (nếu chạy start_proxy.py)        |

### Các URL quan trọng hay dùng khi demo:

| URL                                                              | Mục đích                     |
| ---------------------------------------------------------------- | ---------------------------- |
| `http://127.0.0.1:9000/login`                                    | Trang đăng nhập              |
| `http://127.0.0.1:9000/index.html`                               | Trang chủ (cần cookie auth)  |
| `http://127.0.0.1:9000/submit-info`                              | Form đăng ký IP:Port         |
| `http://127.0.0.1:9000/get-list`                                 | Xem danh sách peers (JSON)   |
| `http://127.0.0.1:9001/active-peers`                             | Danh sách peer của VoPham    |
| `http://127.0.0.1:9001/view-my-channels`                         | Kênh của VoPham              |
| `http://127.0.0.1:9001/chat?peer=MinhDuc&ip=127.0.0.1&port=9002` | Chat VoPham → MinhDuc        |
| `http://127.0.0.1:9002/chat?peer=VoPham&ip=127.0.0.1&port=9001`  | Chat MinhDuc → VoPham        |
| `http://127.0.0.1:9004/active-peers`                             | Danh sách peer của MinhKhang |
| `http://127.0.0.1:9005/active-peers`                             | Danh sách peer của ChanKien  |

## 🎬 PHẦN 1 – Authentication (2 điểm)

### Chuẩn bị:

```bash
python start_tracker.py --server-ip 127.0.0.1 --server-port 9000
```

### Tài khoản có sẵn trong DB:

| Username  | Password (MSSV) |
| --------- | --------------- |
| VoPham    | 2313946         |
| MinhDuc   | 2310797         |
| TrungQuan | 2312817         |
| MinhKhang | 2311399         |
| ChanKien  | 2211740         |

### Kịch bản:

**Bước 1 – Chứng minh trang được bảo vệ:**

- Mở browser → `http://127.0.0.1:9000/index.html`
- **Kết quả:** Hiện `401 Unauthorized` → chứng minh không vào được khi chưa login

**Bước 2 – Vào trang đăng nhập:**

- Vào `http://127.0.0.1:9000/login`
- **Kết quả:** Hiện form Login có 2 ô username/password

**Bước 3 – Đăng nhập sai:**

- Nhập username/password bừa → bấm Login
- **Kết quả:** Alert "Login failed" → chứng minh có validate

**Bước 4 – Đăng nhập đúng:**

- Nhập `VoPham` / `2313946` → bấm Login
- **Kết quả:** Tự redirect vào `index.html` thành công

**Bước 5 – Xem Cookie:**

- Nhấn F12 → Application → Cookies → `http://127.0.0.1:9000`
- **Kết quả:** Thấy `auth=true` và `username=VoPham` → chứng minh Set-Cookie hoạt động

**Bước 6 – Xóa cookie, vào lại bị chặn:**

- F12 → xóa cookie `auth` → reload `http://127.0.0.1:9000/index.html`
- **Kết quả:** Bị 401 lại → chứng minh server kiểm tra cookie mỗi request

## 🎬 PHẦN 2 – Tracker / Client-Server (1 điểm)

### Chuẩn bị (giữ nguyên server port 9000, mở thêm):

```bash
# Terminal 2 - VoPham
python start_peer.py --server-ip 127.0.0.1 --server-port 9001

# Terminal 3 - MinhDuc
python start_peer.py --server-ip 127.0.0.1 --server-port 9002

# Terminal 4 - MinhKhang
python start_peer.py --server-ip 127.0.0.1 --server-port 9003

# Terminal 5 - ChanKien
python start_peer.py --server-ip 127.0.0.1 --server-port 9004
```

### Kịch bản:

**Bước 1 – VoPham & MinhDuc đăng nhập và khai báo IP:**

- Browser tab 1 → `http://127.0.0.1:9000/login` → Mở ẩn danh log VoPham, Submit Port: `9001`
- Browser tab 2 → `http://127.0.0.1:9000/login` → Mở ẩn danh log MinhDuc, Submit Port: `9002`

**Bước 2 – MinhKhang & ChanKien khai báo IP:**

- Khai báo lần lượt `MinhKhang` (port `9003`) và `ChanKien` (port `9004`) qua form `submit-info` trên Tracker tương tự như hai bạn trên.

**Bước 3 – Chứng minh Tracker ghi nhận toàn mạng (4 người):**

- Mở tab mới → `http://127.0.0.1:9000/get-list`
- **Kết quả:**

```json
{
  "status": "success",
  "peers": {
    "VoPham": { "ip": "127.0.0.1", "port": "9001" },
    "MinhDuc": { "ip": "127.0.0.1", "port": "9002" },
    "MinhKhang": { "ip": "127.0.0.1", "port": "9003" },
    "ChanKien": { "ip": "127.0.0.1", "port": "9004" }
  }
}
```

**Bước 4 – Peer discovery trọn vẹn đa thành viên:**

- Tab VoPham → `http://127.0.0.1:9001/active-peers`
- **Kết quả:** Thấy hiển thị cả 3 ngưi bạn: MinhDuc, MinhKhang, ChanKien để chuẩn bị nhấn "Connect".
- Giải thích với giáo viên: "Web của Peer chủ động lấy danh bạ từ Tracker để vẽ ra bảng danh sách liên hệ này ạ".

---

## 🎬 PHẦN 3 – P2P Chat (2 điểm)

> Tiếp theo sau Phần 2, đã có VoPham ở port 9001, MinhDuc ở port 9002

### Kịch bản:

**Bước 1 – VoPham kết nối với MinhDuc:**

- Tab VoPham → `http://127.0.0.1:9001/active-peers`
- Bấm nút **"Connect"** cạnh tên MinhDuc
- **Kết quả:** Nút chuyển thành "Connected", terminal 9001 in ra `[Peer] MinhDuc connected`

**Bước 2 – VoPham mở trang chat:**

- Vào `http://127.0.0.1:9001/chat?peer=MinhDuc&ip=127.0.0.1&port=9002`
- **Kết quả:** Hiện trang chat với tiêu đề "Chat with MinhDuc"

**Bước 3 – VoPham gửi tin nhắn:**

- Gõ "Chào MinhDuc!" → bấm Send
- **Kết quả:** Terminal MinhDuc (port 9002) in: `[Peer] Received from VoPham: Chào MinhDuc!`
- Tin gửi THẲNG đến MinhDuc, không qua Tracker

**Bước 4 – MinhDuc thấy tin và nhắn lại:**

- Tab MinhDuc → `http://127.0.0.1:9002/active-peers` → Connect với VoPham
- Vào `http://127.0.0.1:9002/chat?peer=VoPham&ip=127.0.0.1&port=9001`
- **Kết quả:** Thấy tin "Chào MinhDuc!" đã hiện lên (polling tự động 1s)
- MinhDuc gõ "Chào VoPham!" → Send → VoPham nhận sau 1 giây

## Hướng dẫn sử dụng `start_peer_cli.py` (CLI P2P)

> Phiên bản đầy đủ: hỗ trợ đa kênh, tin nhắn riêng, gửi theo kênh cụ thể

### 1. Khởi chạy Tự động toàn bộ hệ thống (Tracker + Client) bằng run_cli.bat

Thay vì gõ lệnh thủ công để mở từng Tracker và từng Client, hãy chạy file `.bat` để tiết kiệm thời gian (7 cửa sổ sẽ tự động bật lên):

```bash
# Khởi động 7 Terminal CMD ngay lập tức (2 Tracker và 5 Client)
./run_cli.bat
```

> **Lưu ý:** Client tự tạo file `[username]_channels.json` để ghi nhớ các Kênh đã tham gia, lần sau mở lên không cần gõ join lại.

> 💡 Nhắc nhở: Lần đầu tiên khởi chạy, màn hình sẽ báo: `[Client] Chua tham gia kenh nao. Dung lenh: /join <ip:port>`. Mời bạn xem các lệnh ở mục kế tiếp.

### 2. Các lệnh CLI (Bảng tra cứu đầy đủ)

#### Quản lý Kênh (Channel)

Chức năng này giúp Client tương tác với hệ thống Tracker để "nhập/xuất" mạng lưới chat.

| Lệnh               | Mô tả                                                                           | Ví dụ thực tế           |
| ------------------ | ------------------------------------------------------------------------------- | ----------------------- |
| `/join <ip:port>`  | Tham gia một Server Kênh mới, ghi danh IP lên Tracker và lưu vào bộ nhớ cục bộ. | `/join 127.0.0.1:8001`  |
| `/leave <ip:port>` | Rời khỏi một kênh mạng và xóa khóa liên kết khỏi bộ nhớ cục bộ.                 | `/leave 127.0.0.1:8001` |
| `/list_channels`   | In ra danh sách toàn bộ các Kênh mà bạn đang "cắm chốt".                        | `/list_channels`        |

#### Nhắn tin (Messaging)

Hệ thống mạng lưới mạnh mẽ hỗ trợ 3 Mode gửi tin nhắn từ tầm gần đến tầm xa.

| Lệnh                         | Mô tả                                                                                                   | Ví dụ thực tế                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `/msg <username> <nội_dung>` | **Mode Riêng tư:** Gửi tin nhắn P2P trực tiếp 1-1 thẳng đến máy thụ hưởng. Rất bảo mật.                 | `/msg MinhDuc Mở cửa cho mình vào với`        |
| `/send <ip:port> <nội_dung>` | **Mode Kênh:** Bắn tin nhắn chùm cho TẤT CẢ các thành viên ĐANG CÓ MẶT tại một Kênh cụ thể.             | `/send 127.0.0.1:8002 Chào 500 anh em Kênh 2` |
| `/broadcast <nội_dung>`      | **Mode Toàn Lãnh Thổ:** Gét-gô, thổi còi phát thanh tới TẤT CẢ TẤT CẢ MỌI NGƯỜI ở MỌI KÊNH bạn đã join! | `/broadcast Giãn cách xã hội nhé ae!!`        |

#### Tiện ích (Utilities)

| Lệnh    | Mô tả                                                                                           | Ví dụ thực tế |
| ------- | ----------------------------------------------------------------------------------------------- | ------------- |
| `/list` | Tải về Danh bạ người dùng Toàn Mạng (gom từ tất cả các Kênh) để tra cứu xem ai đang Online.     | `/list`       |
| `/quit` | Đợt dọn dẹp cuối cùng. Rút dây mạng, gửi tín hiệu `/logout` cáo từ tất cả mọi người và sập app. | `/quit`       |

### 3. Kịch bản Demo Mẫu (5 Thành viên tương tác Đa Kênh)

Sử dụng 5 thành viên (VoPham, MinhDuc, TrungQuan, MinhKhang, ChanKien) để trình diễn sức mạnh thực tế của hệ thống lai (Hybrid).

```text
[Bước 1] Khởi động toàn bộ Hệ thống (Trackers và Clients):
    Chạy file `./run_cli.bat`
    → 7 cửa sổ Terminal (2 Tracker + 5 Client) sẽ tự động mở ra sẵn sàng chờ lệnh!

--- ĐĂNG KÝ VÀO PHÒNG CHAT ---
[VoPham]    /join 127.0.0.1:8001    → VoPham vào Kênh 1
[MinhDuc]   /join 127.0.0.1:8001    → MinhDuc vào Kênh 1
[TrungQuan] /join 127.0.0.1:8001    → TrungQuan vào Kênh 1
[MinhKhang] /join 127.0.0.1:8002    → MinhKhang vào Kênh 2
[ChanKien]  /join 127.0.0.1:8002    → ChanKien vào Kênh 2

# Cho VoPham tham gia thêm Kênh 2 để làm tình báo "Điệp viên 2 mang":
[VoPham]    /join 127.0.0.1:8002    → VoPham hiện có mặt ở cả 2 Kênh!
[VoPham]    /list_channels          → Xác nhận VoPham đã kết nối thành công 2 kênh.

--- DEMO BẮN TIN NHẮN TẬP THỂ (CHANNEL) ---
[VoPham] /send 127.0.0.1:8001 Xin chao toan the anh em Kenh 1!
        → Chỉ có MinhDuc và TrungQuan nhận được ✅
        → (MinhKhang, ChanKien hoàn toàn không thấy vì ở Kênh 2)

[MinhKhang] /send 127.0.0.1:8002 Co ai onl ben Kenh 2 khong nhi?
        → ChanKien & VoPham nhận được ✅
        → (MinhDuc, TrungQuan không thấy)

--- DEMO BẮN TIN NHẮN TOÀN TRẠNG (BROADCAST) ---
# Khác biệt 1: Nếu một dân thường chỉ ở Kênh 1 (như TrungQuan) gửi Broadcast, uy lực chỉ giới hạn ở Kênh 1:
[TrungQuan] /broadcast Hnay nghi som nha ae!
        → Chỉ có MinhDuc và VoPham nhận được ✅. (MinhKhang và ChanKien ở Kênh 2 không thấy).

# Khác biệt 2 (Từ Điệp viên): Vì VoPham sở hữu chìa khóa từ cả 2 kênh, lệnh broadcast từ VoPham sẽ đi xuyên toàn lãnh thổ mạng:
[VoPham] /broadcast Chu y: Thay giao xuong quan li kiem tra ki !!
        → TẤT CẢ MỌI NGƯỜI (MinhDuc, TrungQuan, MinhKhang, ChanKien) ĐỀU NHẬN ĐƯỢC ALERT CÙNG MỘT LÚC! ✅

--- DEMO BẮN TIN P2P NHẮN RIÊNG TƯ (1-1) ---
# Từ con mắt bao quát của "Điệp viên" VoPham (Thấy toàn bộ 2 kênh):
[VoPham] /list
        → Thấy đầy đủ dân số: MinhDuc, TrungQuan (Kênh 1) và MinhKhang, ChanKien (Kênh 2).

# Trường hợp 1 (Thất bại do P2P bảo mật): Nếu một người ở Kênh 1 (MinhDuc) ráng chọc P2P sang Kênh 2 (ChanKien):
[MinhDuc] /msg ChanKien Chac ong ko nhan dc tin nay dau ha
        → Báo lỗi máy chủ: "Khong tim thay nguoi dung 'ChanKien'". Hệ thống P2P chặt đứt kết nối vì không xin được IP. ✅

# Trường hợp 2 (Thành công qua Kênh chung): Do có IP của ChanKien (cùng ở Kênh 2), Điệp viên VoPham lén chat riêng 1-1 với ChanKien:
[VoPham] /msg ChanKien Kien oi luon cham the cho minh xin code voi!!
        → CHỈ MÌNH ChanKien nhận được tin bí mật. MinhKhang (dù chung Kênh 2) cũng hoàn toàn không thể đọc trộm! ✅

--- DEMO RỜI MẠNG LƯỚI ---
[MinhKhang] /leave 127.0.0.1:8002   → MinhKhang tu dong rut khoi mang Kênh 2 de tat may an com.

[MinhDuc] /quit                     → MinhDuc thoát phần mềm, dọn dẹp port và sập app.
```

## 🎬 PHẦN 4 – Non-blocking Mechanism (2 điểm)

> Phần này chủ yếu giải thích code, không cần chạy thêm gì

### Kịch bản:

**Bước 1 – Chứng minh trực quan (nhiều server chạy song song):**

- Chỉ vào 3 terminal đang chạy cùng lúc (port 9000, 9001, 9002)
- "Ba server đang hoạt động song song, không cái nào block cái kia → đây là non-blocking"

**Bước 2 – Mở `daemon/backend.py`, giải thích Multi-thread:**

```python
while True:
    conn, addr = server.accept()   # Chclient

    # Mỗi client → 1 thread riêng, không block main thread
    client_thread = threading.Thread(
        target=handle_client,
        args=(ip, port, conn, addr, routes)
    )
    client_thread.start()
```

**Giải thích:** "Main thread chỉ nhận kết nối rồi giao cho thread con xử lý. Main thread không bao giờ dừng chờ→ không blocking"

**Bước 3 – Mở `daemon/httpadapter.py`, giải thích Coroutine:**

```python
async def handle_client_coroutine(self, reader, writer):
    raw = await reader.read(4096)  # await = nhường CPU, không block
    ...
    await writer.drain()
```

**Giải thích:** "Ngoài multi-thread, còn viết thêm phiên bản dùng asyncio. `await` cho phép 1 thread phục vụ nhiều kết nối xen kẽ nhau"

**Bước 4 – Mở `daemon/backend.py`, giải thích Selectors (event-driven):**

```python
import selectors
sel = selectors.DefaultSelector()
```

**Giải thích:** "Ngoài threading và asyncio, còn khai báo cơ chế selectors – mô hình event-driven: 1 thread theo dõi nhiều socket cùng lúc, chỉ xử lý khi có sự kiện xảy ra. Đây là nn tảng của các web server hiệu suất cao như nginx"

**Bước 5 – Mở `daemon/asynaprous.py`, chứng minh tự viết framework:**

```python
class AsynapRous:
    def route(self, path, methods=['GET']):
        def decorator(func):
            for method in methods:
                self.routes[(method, path)] = func
            # Tự động bọc hàm Sync/Async
            if inspect.iscoroutinefunction(func):
               return async_wrapper
            else:
               return sync_wrapper
        return decorator
```

**Giải thích:** "Toàn bộ dùng Python standard library: socket, threading, asyncio. Không flask, không django. AsynapRous là framework tự xây dựng hỗ trợ cả hàm đồng bộ lẫn bất đồng bộ (Coroutine) rất linh hoạt"

**Bước 5 – Demo trực quan: Mở nhiều tab cùng lúc:**

- Mở 5 tab browser cùng vào `http://127.0.0.1:9000/login`
- Nhìn terminal → thấy 5 dòng log xuất hiện song song
- "5 request được xử lý đồng thời, không xếp hàng chờ nhau"

## 📊 TỔNG KẾT

### Ước tính điểm demo:

| Phần                    | Điểm tối đa | Ước tính    |
| ----------------------- | ----------- | ----------- |
| Authentication (Cookie) | 2đ          | ~1.8đ       |
| ChatApp Client-Server   | 1đ          | ~1đ         |
| ChatApp Peer-to-Peer    | 2đ          | ~1.7đ       |
| Non-blocking Mechanism  | 2đ          | ~1.5đ       |
| **Tổng demo**           | **7đ**      | **~6–6.5đ** |

### Thứ tự demo gợi ý:

```
[~3 phút] Phần 1: Login → 401 → Đăng nhập → Cookie → Xóa cookie → 401 lại
[~2 phút] Phần 2: Submit IP:Port → /get-list → Thấy cả 2 peer
[~3 phút] Phần 3: Connect → Chat qua lại → Broadcast CLI
[~3 phút] Phần 4: Mở code backend.py → Giải thích threading → selectors → weaprous.py
[~3 phút] Bonus: TrungQuan join 2 kênh → /broadcast → /send → /msg 1-1
```

**Tổng thi gian demo: ~11-14 phút**

> ⚠ Nếu thầy giới hạn thi gian, bỏ phần Bonus trước → vẫn đủ ~10 phút
