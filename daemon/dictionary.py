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
daemon.dictionary
~~~~~~~~~~~~~~~~~

Module này cung cấp các cấu trúc dữ liệu lưu trữ từ điển đặc biệt phục vụ cho HTTP.
Cụ thể là `CaseInsensitiveDict` để lưu trữ HTTP Headers mà không phân biệt chữ hoa, chữ thường.
"""

# from collections import MutableMapping
from collections.abc import MutableMapping


# Cấu trúc từ điển đặc biệt tự động bỏ qua định dạng chữ hoa/chữ thường, chuyên trị cho HTTP Header
class CaseInsensitiveDict(MutableMapping):
    """Lớp CaseInsensitiveDict – từ điển không phân biệt hoa/thường.

    Kế thừa từ MutableMapping, tự động chuyển mọi key về chữ thường
    khi lưu và khi tra cứu, giúp thao tác với HTTP header dễ dàng hơn.
    (HTTP header không phân biệt hoa/thường theo RFC 7230)

    Ví dụ sử dụng::

      >>> word = CaseInsensitiveDict(status_code='404', msg="Not found")
      >>> word['STATUS_CODE']   # vẫn tìm được dù viết hoa
      '404'
      >>> word['MSG']
      'Not found'
      >>> print(word)
      {'status_code': '404', 'msg': 'Not found'}

    """

    # Khởi tạo và ép kiểu toàn bộ thuộc tính đầu vào thành chữ thường định chuẩn (lowercase)
    def __init__(self, *args, **kwargs):
        # Chuyển tất cả key về chữ thường ngay từ khi khởi tạo
        self.store = {k.lower(): v for k, v in dict(*args, **kwargs).items()}

    # Trích xuất giá trị bằng key không phân biệt hoa/thường
    def __getitem__(self, key):
        """Lấy giá trị theo key (không phân biệt hoa/thường)."""
        return self.store[key.lower()]

    # Gán giá trị mới sau khi đã chuẩn hóa key về chữ thường
    def __setitem__(self, key, value):
        """Ghi giá trị vào dict, key luôn được chuyển thành chữ thường."""
        self.store[key.lower()] = value

    # Xóa giá trị trong từ điển một cách an toàn không phân mảnh định dạng
    def __delitem__(self, key):
        """Xóa một phần tử theo key (không phân biệt hoa/thường)."""
        del self.store[key.lower()]

    # Luân chuyển và duyệt qua tập hợp các key hiện có
    def __iter__(self):
        """Duyệt qua các key trong dict."""
        return iter(self.store)

    # Thống kê kích thước bộ từ điển hiện hữu
    def __len__(self):
        """Trả về số lượng phần tử trong dict."""
        return len(self.store)
