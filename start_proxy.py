# reverse_proxy.py
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
start_proxy
~~~~~~~~~~~~~~~~~

Module nay la diem khoi dau de chay Reverse Proxy Server su dung WeApRous.

Chuc nang chinh:
- Doc file cau hinh (config/proxy.conf) de lay thong tin virtual host va chinh sach phan phoi
- Phan tich cac khoi 'host' trong file conf de xay dung bang dinh tuyen (routing table)
- Khoi dong proxy server tren ip:port truyen vao tu dong lenh

Cach Proxy hoat dong:
- Nhan request tu client
- Tra cuu routing table de tim backend phu hop
- Chuyen tiep (forward) request den backend do
- Chinh sach mac dinh: round-robin

Cach chay:
    python start_proxy.py --server-ip 127.0.0.1 --server-port 8080
"""

import socket
import threading
import argparse
import re

# from urlparse import urlparse
from urllib.parse import urlparse
from collections import defaultdict

from daemon import create_proxy

# Cong mac dinh cho proxy server (co the ghi de bang --server-port)
PROXY_PORT = 8888


def parse_virtual_hosts(config_file):
    """
    Doc va phan tich file cau hinh proxy (dinh dang tuong tu NGINX).

    Ham nay tim tat ca khoi 'host' trong file .conf,
    sau do xay dung bang dinh tuyen (routes) dang:
        { "ten_host": (["backend1", "backend2"], "chinh-sach") }

    :config_file (str): Duong dan den file cau hinh proxy.
    :rtype dict: Bang dinh tuyen { host_name: (backend_list, policy) }
    """

    with open(config_file, "r") as f:
        config_text = f.read()

    # Match each host block
    host_blocks = re.findall(r'host\s+"([^"]+)"\s*\{(.*?)\}', config_text, re.DOTALL)

    dist_policy_map = ""

    routes = {}
    for host, block in host_blocks:
        proxy_map = {}

        # Find all proxy_pass entries
        proxy_passes = re.findall(r"proxy_pass\s+http://([^\s;]+);", block)
        map = proxy_map.get(host, [])
        map = map + proxy_passes
        proxy_map[host] = map

        # Find dist_policy if present
        policy_match = re.search(
            r"dist_policy\s+([\w-]+)", block
        )  # Fix: error extract policy [Ly]
        if policy_match:
            dist_policy_map = policy_match.group(1)
        else:  # default policy is round_robin
            dist_policy_map = "round-robin"

        #
        # @bksysnet: Build the mapping and policy
        # TODO: this policy varies among scenarios
        #       the default policy is provided with one proxy_pass
        #       In the multi alternatives of proxy_pass then
        #       the policy is applied to identify the highes matching
        #       proxy_pass
        #
        if len(proxy_map.get(host, [])) == 1:
            routes[host] = (proxy_map.get(host, [])[0], dist_policy_map)
        # esle if:
        #         TODO:  apply further policy matching here
        #
        else:
            routes[host] = (proxy_map.get(host, []), dist_policy_map)

    for key, value in routes.items():
        print(key, value)  # In ra bang dinh tuyen de kiem tra khi khoi dong
    return routes


if __name__ == "__main__":
    """
    Diem vao chinh de khoi dong Proxy Server.

    Luong thuc thi:
    1. Phan tich tham so dong lenh (--server-ip, --server-port)
    2. Doc file config/proxy.conf -> xay dung routing table
    3. Goi create_proxy(ip, port, routes) -> khoi dong proxy

    Tham so:
        --server-ip   (str): Dia chi IP cho proxy. Mac dinh: 0.0.0.0
        --server-port (int): So cong cho proxy.   Mac dinh: 8080
    """

    parser = argparse.ArgumentParser(
        prog="Proxy", description="", epilog="Proxy daemon"
    )
    parser.add_argument("--server-ip", default="0.0.0.0")
    parser.add_argument("--server-port", type=int, default=PROXY_PORT)

    args = parser.parse_args()
    ip = args.server_ip  # Dia chi IP proxy
    port = args.server_port  # Cong proxy

    # Doc file cau hinh va xay dung bang dinh tuyen
    routes = parse_virtual_hosts("config/proxy.conf")

    # Khoi dong proxy server voi routing table da xay dung
    create_proxy(ip, port, routes)
