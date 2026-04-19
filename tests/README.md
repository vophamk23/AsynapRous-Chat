# Thu muc tests/ – Huong dan su dung

## Danh sach tai khoan he thong

| Username  | Password (MSSV) |
|-----------|-----------------|
| VoPham    | 2313946         |
| MinhDuc   | 2310797         |
| TrungQuan | 2312817         |
| MinhKhang | 2311399         |
| ChanKien  | 2211740         |

---

## Tong quan cac file

| File             | Loai          | Can gi de chay          | Muc dich chinh                  |
|------------------|---------------|-------------------------|---------------------------------|
| test_2_bimap.py   | Python test   | Khong can gi            | Unit test class BiMap           |
| test_0.py        | Python test   | manager.py dang chay    | Test chong trung add_peer()     |
| test_1.py        | Python test   | manager.py dang chay    | Test doc/ghi shared dict        |
| test_0.bat       | Bat launcher  | WSL + Windows Terminal  | Bat Tracker + 2 Peer (demo nhanh) |
| test_1.bat       | Bat launcher  | WSL + Windows Terminal  | Bat Manager + Proxy + 2 Tracker + 2 Peer |

---

## Moi quan he giua .bat va .py

```
test_1.bat ──khoi dong──> manager.py (port 50001)
                                |
                         co the ket noi
                        /               \
                 test_0.py           test_1.py

test_0.bat ──khoi dong──> Tracker + VoPham + MinhDuc
                          (khong lien quan den cac file test .py)

test_2_bimap.py ──chay doc lap──> khong can server gi ca
```

Ket luan:
- Chay test_1.bat truoc thi test_0.py va test_1.py co the ket noi
- test_0.bat chi dung de test chat system, khong lien quan den test .py
- test_2_bimap.py chay duoc bat cu luc nao

---

## Huong dan chay tung file

---

### 1. test_2_bimap.py

    Chay tu thu muc goc du an (PowerShell):
        python tests/test_2_bimap.py

    Chay tu WSL:
        python3 tests/test_2_bimap.py

    Ket qua mong doi:
        --- Testing BiMap ---
        Added: VoPham <-> ('127.0.0.1', 9001)
        Added: MinhDuc <-> ('127.0.0.1', 9002)
        Added: TrungQuan <-> ('127.0.0.1', 9003)
        Added: MinhKhang <-> ('127.0.0.1', 9004)
        Them ChanKien (127.0.0.1:9002) -> LOI (trung port voi MinhDuc)
        VoPham dang o dau? -> ('127.0.0.1', 9001)
        TrungQuan dang o dau? -> ('127.0.0.1', 9003)
        Ai dang dung (9002)? -> MinhDuc
        Ai dang dung (9004)? -> MinhKhang
        Removed: VoPham ...
        Removed: TrungQuan ...
        Map xuoi: {'MinhDuc': ..., 'MinhKhang': ...}

---

### 2. test_0.py va test_1.py (can manager.py chay truoc)

    BUOC 1 – Mo Terminal 1, bat manager.py:

        PowerShell:
            python manager.py

        WSL:
            python3 manager.py

        Cho den khi thay dong nay moi sang Terminal 2:
            --- Server Quan ly (Chong trung Value) ---
            Tai: 127.0.0.1:50001

    BUOC 2 – Mo Terminal 2, chay test:

        # Test chong trung add_peer()
        python tests/test_0.py

        # Test doc/ghi shared dict
        python tests/test_1.py

    HOAC: Chay test_1.bat truoc (no se tu dong bat manager.py),
          sau do chay test_0.py hoac test_1.py o terminal rieng.

---

### 3. test_0.bat (khoi nhanh chat system)

    Chay tu thu muc GOC du an (khong vao trong tests/):

        tests\test_0.bat

    Se mo 3 terminal WSL:
        [Tracker]  port 9000  – may chu trung tam
        [VoPham]   port 9001  – peer server 1
        [MinhDuc]  port 9002  – peer server 2

    Sau do mo browser:
        http://127.0.0.1:9000/login  – dang nhap

---

### 4. test_1.bat (khoi day du system + manager)

    Chay tu thu muc GOC du an (khong vao trong tests/):

        tests\test_1.bat

    Se mo 6 terminal WSL:
        [Manager]  port 50001 – shared state (ho tro test_0.py, test_1.py)
        [Proxy]    port 8080  – load balancer
        [Tracker1] port 9002  – tracker server thu nhat
        [Tracker2] port 9003  – tracker server thu hai
        [MinhKhang] port 9100 – peer server 1
        [ChanKien]  port 9200 – peer server 2

    Sau khi bat test_1.bat, co the chay tiep:
        python tests/test_0.py
        python tests/test_1.py

---

## Loi thuong gap va cach xu ly

| Loi                            | Nguyen nhan                     | Cach fix                               |
|--------------------------------|---------------------------------|----------------------------------------|
| "Python khong tim thay"        | Dung python3 tren Windows       | Thay python3 bang python               |
| "Khong the ket noi Manager"    | Chua chay manager.py            | Chay python manager.py truoc           |
| Terminal .bat mo nhung loi cd  | Chay .bat tu trong tests/       | Chay tu thu muc goc du an              |
| Port da duoc su dung           | Terminal cu chua tat            | Tat terminal cu hoac doi port khac     |
| UnicodeEncodeError             | Windows terminal khong hieu UTF-8 | Da fix san: sys.stdout.reconfigure() |
