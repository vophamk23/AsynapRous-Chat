@echo off
REM run.bat – Khoi dong he thong de DEMO tren Windows CMD (Ban Go Lenh CLI)
REM Khong can WSL - Mo 7 cua so Windows truc tiep

ECHO Dang mo 7 cua so CMD cua Windows...

:: Khoi dong Trackers (Kenh 1 va Kenh 2 theo y henh trong DEMO_GUIDE)
start "Tracker Kenh 1" cmd /k "title Tracker-8001 && echo [Tracker 1] Port 8001 && python start_tracker.py --server-port 8001"
start "Tracker Kenh 2" cmd /k "title Tracker-8002 && echo [Tracker 2] Port 8002 && python start_tracker.py --server-port 8002"

:: Khoi dong Peers (Su dung start_peer_cli.py de ho tro viec go lenh /join)
:: [Peer 1] VoPham: Mo cong P2P 9001. San sang ket noi va ban tin doc lap.
start "VoPham" cmd /k "title VoPham-9001 && python start_peer_cli.py --username VoPham --port 9001"
:: [Peer 2] MinhDuc: Mo cong P2P 9002. Dung de test tinh nang Chat 1-1 voi VoPham.
start "MinhDuc" cmd /k "title MinhDuc-9002 && python start_peer_cli.py --username MinhDuc --port 9002"
:: [Peer 3] TrungQuan: Mo cong P2P 9003. Mo rong mang luoi P2P, ho tro nhan Broadcast toàn kenh.
start "TrungQuan" cmd /k "title TrungQuan-9003 && python start_peer_cli.py --username TrungQuan --port 9003"
:: [Peer 4] MinhKhang: Mo cong P2P 9004. Dong vai tro Peer nam ngoai ranh gioi de test xuyen kenh.
start "MinhKhang" cmd /k "title MinhKhang-9004 && python start_peer_cli.py --username MinhKhang --port 9004"
:: [Peer 5] ChanKien: Mo cong P2P 9005. Nhan to thu 5, thu nghiem luu luong truyen tai lon.
start "ChanKien" cmd /k "title ChanKien-9005 && python start_peer_cli.py --username ChanKien --port 9005"

ECHO Da khoi dong xong toan bo he thong!
