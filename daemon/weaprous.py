#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.weaprous
~~~~~~~~~~~~~~~~~

Module này cung cấp đối tượng WeApRous – một framework web tiện ích tự viết
để đăng ký các endpoint RESTful theo mô hình decorator (giống Flask).
"""

from .backend import create_backend


class WeApRous:
    """Lớp WeApRous – framework web tự viết, nhẹ và dễ dùng.

    Cho phép đăng ký các route handler bằng decorator @app.route()
    và khởi động TCP server để phục vụ các request RESTful.
    Mỗi route được ánh xạ theo cặp (HTTP method, path) → hàm xử lý.
    Framework KHÔNG dùng Flask hay Django – toàn bộ viết bằng thư viện chuẩn Python.

    Ví dụ sử dụng::
      >>> import daemon.weaprous
      >>> app = WeApRous()
      >>> @app.route('/login', methods=['POST'])
      >>> def login(req):
      >>>     return Response().build_success({'message': 'Logged in'})

      >>> @app.route('/hello', methods=['GET'])
      >>> def hello(req):
      >>>     return Response().build_success({'message': 'Hello!'})

      >>> app.prepare_address('127.0.0.1', 9000)
      >>> app.run()
    """

    def __init__(self):
        """
        Khởi tạo đối tượng WeApRous.
        Tạo bảng route rỗng và các biến chứa IP/Port.
        """
        self.routes = {}  # Bảng ánh xạ (method, path) → hàm xử lý
        self.ip = None  # Địa chỉ IP server, được cấu hình qua prepare_address()
        self.port = None  # Cổng server
        return

    def prepare_address(self, ip, port):
        """
        Cấu hình địa chỉ IP và cổng cho backend server.
        Phải gọi hàm này trước khi gọi run().

        :param ip   (str): địa chỉ IP cần bind.
        :param port (int): số cổng cần lắng nghe.
        """
        self.ip = ip
        self.port = port

    def route(self, path, methods=["GET"]):
        """
        Decorator để đăng ký một hàm xử lý cho một route cụ thể.

        :param path    (str) : đường dẫn URL cắn lắng nghe (ví dụ: '/login').
        :param methods (list): danh sách HTTP method (ví dụ: ['GET', 'POST']).

        :rtype: function – decorator đăng ký hàm vào bảng routes.
        """

        def decorator(func):
            for method in methods:
                # Lưu hàm vào bảng route: khóa là (METHOD, /path)
                self.routes[(method.upper(), path)] = func

            # Gán metadata vào hàm để tiện debug sau này
            func._route_path = path
            func._route_methods = methods

            return func

        return decorator

    def run(self):
        """
        Khởi động backend server và bắt đầu lắng nghe request.
        Phải gọi prepare_address() trước, nếu không sẽ báo lỗi.
        """
        if not self.ip or not self.port:
            print(
                "WeApRous cần cấu hình địa chỉ trước – "
                "hãy gọi app.prepare_address(ip, port) trước khi run()"
            )

        # Khởi động backend server với bảng routes đã đăng ký
        create_backend(self.ip, self.port, self.routes)
