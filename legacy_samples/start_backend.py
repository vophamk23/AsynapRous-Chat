#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
start_backend
~~~~~~~~~~~~~~~~~

Module nay la diem khoi dau de chay mot backend server don gian
su dung socket framework cua WeApRous.

Chuc nang chinh:
- Doc tham so dong lenh (--server-ip, --server-port) de cau hinh server
- Goi create_backend(ip, port) de khoi dong server HTTP khong chan (non-blocking)

Cach chay:
    python start_backend.py --server-ip 127.0.0.1 --server-port 9000
"""

import socket
import argparse

from daemon import create_backend

# Cong mac dinh neu nguoi dung khong truyen --server-port
PORT = 9000


if __name__ == "__main__":
    """
    Diem vao chinh cua chuong trinh backend.

    Phan tich tham so dong lenh de lay IP va Port,
    sau do goi create_backend(ip, port) de khoi dong server.

    Tham so:
        --server-ip   (str): Dia chi IP gan vao server. Mac dinh: 0.0.0.0
        --server-port (int): So cong gan vao server.   Mac dinh: 9000
    """

    parser = argparse.ArgumentParser(
        prog="Backend",
        description="Khoi dong Backend Server (Non-blocking HTTP)",  # Mo ta chuong trinh
        epilog="WeApRous Backend Daemon",
    )
    parser.add_argument(
        "--server-ip",
        type=str,
        default="0.0.0.0",
        help="Dia chi IP de bind server. Mac dinh la 0.0.0.0 (lang nghe tren moi interface)",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=PORT,
        help="So cong de bind server. Mac dinh la {}.".format(PORT),
    )

    args = parser.parse_args()
    ip = args.server_ip  # Lay IP tu tham so dong lenh
    port = args.server_port  # Lay Port tu tham so dong lenh

    # Khoi dong backend server voi ip va port da cau hinh
    create_backend(ip, port)
