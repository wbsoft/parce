# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2019-2020 by Wilbert Berendsen <info@wilbertberendsen.nl>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Test the recursion depth (should be "infinite" :-)
"""

import sys
sys.path.insert(0, '.')

import parce


def test_main():

    # ten thousand open tags :-)
    root = parce.root(parce.find("xml"), "<xml>" * 10000)
    assert len(list(root.tokens())) == 30000
    assert root.height() == 10000
    assert root.query.all.count() == 40000


if __name__ == "__main__":
    test_main()

