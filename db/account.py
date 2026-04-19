import sqlite3


# Mở luồng kết nối tiêu chuẩn tới tập cơ sở dữ liệu SQLite cục bộ
def create_connection(db_file):
    """Tạo kết nối đến file database SQLite"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"[DB] Connected to {db_file} (SQLite v{sqlite3.sqlite_version})")
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn


# Khởi tạo kiến trúc bảng account chuẩn nếu chưa tồn tại trong cơ sở dữ liệu
def create_table(conn):
    """Tạo bảng mới"""
    sql_create_table = """
    CREATE TABLE IF NOT EXISTS account (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    );
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql_create_table)
        print("[DB] Table 'account' ready.")
    except sqlite3.Error as e:
        print(e)


# Khởi tạo và chèn mới một đối tượng tài khoản vào hệ thống lưu trữ
def insert_account(conn, account):
    """Thêm một tài khoản mới vào bảng"""
    sql = """ INSERT INTO account(username,password)
              VALUES(?,?) """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, account)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        print(f"Lỗi: Username '{account[0]}' đã tồn tại.")
        return None


# Truy xuất thông tin chi tiết của một tài khoản qua định danh (username)
def select_user(conn, username):
    """Truy vấn user bất kỳ"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account WHERE username=?", (username,))

    return cursor.fetchone()  # Lấy kết quả


# Quét và truy trả toàn bộ danh sách tài khoản đang được lưu trong cơ sở dữ liệu
def select_all_users(conn):
    """Truy vấn tất cả user"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account")
    return cursor.fetchall()


# Rút thông tin và xóa quyền truy cập của một tài khoản riêng biệt
def delete_account(conn, username):
    """Xóa một user"""
    sql = "DELETE FROM account WHERE username=?"
    cursor = conn.cursor()
    cursor.execute(sql, (username,))
    conn.commit()


# Dọn rác cơ sở dữ liệu bằng cách xóa toàn bộ tài khoản hiện hành
def delete_all_accounts(conn):
    """Xóa tất cả user"""
    sql = "DELETE FROM account"
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()


if __name__ == "__main__":
    import sys

    DB_FILE = "db/account.db"
    conn = create_connection(DB_FILE)
    create_table(conn)

    args = sys.argv[1:]

    # python db/account.py list
    if not args or args[0] == "list":
        rows = select_all_users(conn)
        print(f"\n{'='*42}")
        print(f"  Danh sach tai khoan ({len(rows)} tai khoan)")
        print(f"{'='*42}")
        for row in rows:
            print(f"  {row[0]:<15} | {row[1]}")
        print(f"{'='*42}\n")

    # python db/account.py add <username> <password>
    elif args[0] == "add" and len(args) == 3:
        username, password = args[1], args[2]
        result = insert_account(conn, (username, password))
        if result:
            print(f"Da them: {username} / {password}")

    # python db/account.py delete <username>
    elif args[0] == "delete" and len(args) == 2:
        delete_account(conn, args[1])
        print(f"Da xoa tai khoan: {args[1]}")

    # python db/account.py reset
    elif args[0] == "reset":
        confirm = input("Xoa TOAN BO tai khoan? (yes/no): ")
        if confirm.lower() == "yes":
            delete_all_accounts(conn)
            print("Da xoa toan bo tai khoan.")

    else:
        print("\nCach dung:")
        print("  python db/account.py list                    # Xem danh sach")
        print("  python db/account.py add <username> <pass>   # Them tai khoan")
        print("  python db/account.py delete <username>       # Xoa 1 tai khoan")
        print("  python db/account.py reset                   # Xoa tat ca\n")

    conn.close()
