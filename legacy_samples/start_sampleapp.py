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
start_sampleapp
~~~~~~~~~~~~~~~~~

Module nay la vi du mau (sample) minh hoa cach su dung framework WeApRous
de dinh nghia cac route (duong dan HTTP) va chay mot web server don gian.

Chuc nang chinh:
- Dang ky cac route /login (POST) va /hello (PUT) bang decorator @app.route
- Khoi dong WeApRous server tren ip:port truyen vao tu dong lenh

Muc dich:
- Kiem tra framework WeApRous hoat dong dung
- Lam mau de hieu cach viet route trong he thong

Cach chay:
    python start_sampleapp.py --server-ip 127.0.0.1 --server-port 8000
"""

import json
import socket
import argparse

from daemon.weaprous import WeApRous  # Import framework WeApRous tu nhom tu xay dung

PORT = 8000  # Cong mac dinh cho sample app

# Khoi tao doi tuong WeApRous (tuong tu Flask app = Flask(__name__))
app = WeApRous()


@app.route("/login", methods=["POST"])
def login(headers="guest", body="anonymous"):
    """
    Xu ly yeu cau dang nhap qua POST /login.

    Tham so:
        headers: HTTP headers cua request
        body:    Noi dung body (JSON)

    Tra ve:
        dict chua status va thong tin headers/body da nhan
    """
    print(f"[SampleApp] Xu ly dang nhap - headers: {headers}, body: {body}")
    return {"status": "login_called", "headers": str(headers), "body": body}


@app.route("/hello", methods=["PUT"])
def hello(headers, body):
    """
    Xu ly yeu cau chao hoi qua PUT /hello.

    Tham so:
        headers: HTTP headers cua request
        body:    Noi dung body

    Tra ve:
        dict chua status va thong tin headers/body da nhan
    """
    print(f"[SampleApp] Xu ly /hello [PUT] - headers: {headers}, body: {body}")
    return {"status": "hello_called", "headers": str(headers), "body": body}


if __name__ == "__main__":
    # Phan tich tham so dong lenh
    parser = argparse.ArgumentParser(
        prog="SampleApp",
        description="Chay ung dung mau WeApRous de kiem tra framework",
        epilog="WeApRous Sample Application",
    )
    parser.add_argument(
        "--server-ip",
        default="0.0.0.0",
        help="Dia chi IP cho server. Mac dinh: 0.0.0.0",
    )
    parser.add_argument(
        "--server-port",
        type=int,
        default=PORT,
        help=f"So cong cho server. Mac dinh: {PORT}",
    )

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Gan dia chi va chay server
    app.prepare_address(ip, port)
    app.run()  # Chay WeApRous server (non-blocking, dung threading)
