@ECHO OFF
REM test1.bat – Kiểm tra đầy đủ: Proxy + Manager + 2 Tracker + 2 Peer
REM Tài khoản test: MinhKhang (9100), ChanKien (9200)
REM Phải chạy từ thư mục gốc dự án, không chạy trực tiếp từ folder tests/

:: Chuyển đường dẫn Windows sang WSL path (giống run.bat)
for /f "delims=" %%i in ('wsl wslpath "%cd%"') do set WSL_PATH=%%i

ECHO Dang mo 6 terminal WSL...
ECHO WSL_PATH = %WSL_PATH%

:: Peer Manager (quản lý shared state)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [Manager] && python3 manager.py || echo LOI MANAGER && read -n 1"

:: Proxy (Load Balancer – port 8080)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [Proxy] port 8080 && python3 start_proxy.py || echo LOI PROXY && read -n 1"

:: Tracker 1 (port 9002)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [Tracker1] port 9002 && python3 start_tracker.py --server-ip 127.0.0.1 --server-port 9002 || echo LOI TRACKER && read -n 1"

:: Tracker 2 (port 9003)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [Tracker2] port 9003 && python3 start_tracker.py --server-ip 127.0.0.1 --server-port 9003 || echo LOI TRACKER && read -n 1"

:: Peer 1 - MinhKhang (port 9100)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [MinhKhang] port 9100 && python3 start_peer.py --server-ip 127.0.0.1 --server-port 9100 || echo LOI PEER && read -n 1"

:: Peer 2 - ChanKien (port 9200)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [ChanKien] port 9200 && python3 start_peer.py --server-ip 127.0.0.1 --server-port 9200 || echo LOI PEER && read -n 1"
