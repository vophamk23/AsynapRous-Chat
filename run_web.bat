@echo off
REM run_web.bat – Khoi dong he thong de DEMO tren Windows (Ban Giao Dien WEB)
REM Khong can WSL - Mo 7 cua so Windows CMD truc tiep de cap phat sever

ECHO Dang mo 1 Proxy + 1 Tracker + 5 Web Server...

:: Proxy (Dong vai tro canh sat giao thong nam o port 8888 - tuychon neu ho tro Web)
start "Proxy Load Balancer" cmd /k "title Proxy-8888 && echo [Proxy Server] Port 8888 && python start_proxy.py"

:: Tracker Server trung tam cho WEB (Thuong chay tren port 9000 do Web fix cung)
start "Web Tracker" cmd /k "title Tracker-9000 && echo [Tracker Server] Port 9000 && python start_tracker.py --server-ip 127.0.0.1 --server-port 9000 --mode callback"

:: Khoi dong Peers (Su dung start_peer.py de lang nghe cac Giao dien Web qua Port)
:: [Peer 1] Web VoPham: Mo cong Server Web 9001 (.html). Truy cap /login truoc!
start "Web VoPham" cmd /k "title VoPham-9001 && python start_peer.py --server-ip 127.0.0.1 --server-port 9001 --mode callback"
:: [Peer 2] Web MinhDuc: Mo cong Server Web 9002 (.html). Truy cap /login truoc!
start "Web MinhDuc" cmd /k "title MinhDuc-9002 && python start_peer.py --server-ip 127.0.0.1 --server-port 9002 --mode callback"
:: [Peer 3] Web TrungQuan: Mo cong Server Web 9003 (.html). Phuc vu API cap do Frontend.
start "Web TrungQuan" cmd /k "title TrungQuan-9003 && python start_peer.py --server-ip 127.0.0.1 --server-port 9003 --mode callback"
:: [Peer 4] Web MinhKhang: Mo cong Server Web 9004 (.html). P2P Client Node.
start "Web MinhKhang" cmd /k "title MinhKhang-9004 && python start_peer.py --server-ip 127.0.0.1 --server-port 9004 --mode callback"
:: [Peer 5] Web ChanKien: Mo cong Server Web 9005 (.html). Tuyen phong thu sau cung p2p.
start "Web ChanKien" cmd /k "title ChanKien-9005 && python start_peer.py --server-ip 127.0.0.1 --server-port 9005 --mode callback"

ECHO ==============================================================================
ECHO [!] DA KHOI DONG XONG TOAN BO HE THONG P2P (ASYNAPROUS FRAMEWORK) [!]
ECHO ==============================================================================
ECHO.
ECHO Hay nhan giu phim CTRL + Click chuot vao cac link ben duoi de mo trang web:
ECHO.
ECHO --- MAY CHU TRUNG TAM (TRACKER) ---
ECHO [Trang Dang nhap]          http://127.0.0.1:9000/login
ECHO [Trang Chu - Can Login]    http://127.0.0.1:9000/index.html
ECHO [Danh sach IP hien co]     http://127.0.0.1:9000/get-list
ECHO.
ECHO --- MAY CHU NGUOI DUNG (PEER CHAT) ---
ECHO [Web Peer 1 - VoPham]      http://127.0.0.1:9001/active-peers
ECHO [Web Peer 2 - MinhDuc]     http://127.0.0.1:9002/active-peers
ECHO [Web Peer 3 - TrungQuan]   http://127.0.0.1:9003/active-peers
ECHO [Web Peer 4 - MinhKhang]   http://127.0.0.1:9004/active-peers
ECHO [Web Peer 5 - ChanKien]    http://127.0.0.1:9005/active-peers
ECHO.
ECHO ------------------------------------------------------------------------------
ECHO Luu y: Ban bat buoc phai vao [Trang Dang nhap] truoc de khai bao IP P2P!
ECHO ------------------------------------------------------------------------------
pause


@REM # Chọn cơ chế xử lý đồng thời:
@REM #   threading  – Mỗi client 1 luồng riêng (mặc định)        - (--mode threading)
@REM #   callback   – Hướng sự kiện dùng Selector, tiet kiem RAM - (--mode callback)
@REM #   coroutine  – Async/Await hien dai, hieu nang cao nhat   - (--mode coroutine)