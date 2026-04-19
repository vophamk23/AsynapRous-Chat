@ECHO OFF
REM test.bat – Kiểm tra nhanh: 1 Tracker + 2 Peer
REM Tài khoản test: VoPham (9001), MinhDuc (9002)
REM Phải chạy từ thư mục gốc dự án, không chạy trực tiếp từ folder tests/

:: Chuyển đường dẫn Windows sang WSL path (giống run.bat)
for /f "delims=" %%i in ('wsl wslpath "%cd%"') do set WSL_PATH=%%i

ECHO Dang mo 3 terminal WSL...
ECHO WSL_PATH = %WSL_PATH%

:: Tracker Server (port 9000)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [Tracker] port 9000 && python3 start_tracker.py --server-ip 127.0.0.1 --server-port 9000 || echo LOI TRACKER && read -n 1"

:: Peer 1 - VoPham (port 9001)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [VoPham] port 9001 && python3 start_peer.py --server-ip 127.0.0.1 --server-port 9001 || echo LOI PEER && read -n 1"

:: Peer 2 - MinhDuc (port 9002)
start "" wt -w 0 nt -- wsl bash -ic "cd '%WSL_PATH%' && echo [MinhDuc] port 9002 && python3 start_peer.py --server-ip 127.0.0.1 --server-port 9002 || echo LOI PEER && read -n 1"