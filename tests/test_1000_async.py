import asyncio
import time

TARGET_IP = "127.0.0.1"
TARGET_PORT = 9000
NUM_CLIENTS = 1000  # Thử thách 1000 request cùng lúc!

async def simulate_client_async(client_id):
    try:
        # Mở kết nối TCP bất đồng bộ
        reader, writer = await asyncio.open_connection(TARGET_IP, TARGET_PORT)
        
        # Gửi request
        request = f"GET /login HTTP/1.1\r\nHost: {TARGET_IP}\r\nConnection: close\r\n\r\n"
        writer.write(request.encode('utf-8'))
        await writer.drain()
        
        # Nhận phản hồi
        response = await reader.read(1024)
        status_line = response.decode('utf-8').splitlines()[0] if response else "No Response"
        
        print(f"[Client {client_id:04d}] Nhan phan hoi: {status_line}")
        
        # Đóng kết nối
        writer.close()
        await writer.wait_closed()
        
    except Exception as e:
        print(f"[Client {client_id:04d}] LOI: {e}")

async def main():
    print(f"--- BAT DAU TEST BAT DONG BO VOI {NUM_CLIENTS} CLIENTS ---")
    start_time = time.time()
    
    # Tạo 1000 nhiệm vụ bắn request cùng lúc
    tasks = [simulate_client_async(i) for i in range(NUM_CLIENTS)]
    
    # Chạy song song toàn bộ
    await asyncio.gather(*tasks)
        
    end_time = time.time()
    print(f"--- HOAN THANH {NUM_CLIENTS} REQUEST TRONG {end_time - start_time:.2f} GIAY ---")

if __name__ == "__main__":
    # Dùng policy này để tránh lỗi Event Loop trên Windows

    asyncio.run(main())
