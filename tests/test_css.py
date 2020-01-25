# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2019 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Testing CSS parser with pytest-3.
"""

import sys

sys.path.insert(0, ".")

from parce import *
from parce.lang.css import *

css = r"""
h1[attribute="value"] + p {
    width: 500px;
    height: 90%;
    color: white;
    background: url(www.image.org/image.png);
    text-decoration: underline !important;
}
"""

tree = root(Css.root, css)

assert len(tree) == 7
assert tree[2][0][0].action is Name.Attribute
assert tree.query.all.action(Number).pick().pos == 40
assert tree.query.all(Css.declaration)[0][0].list() == [
    'width', 'height', 'color', 'background','text-decoration']
assert tree.query.all.action(Name.Property)("color").next.next.pick() == "white"
