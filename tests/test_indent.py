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
Testing parce.indent.
"""

import os
import sys

sys.path.insert(0, ".")

from parce import Document, Cursor
from parce.indent import Indenter


def text_fragments():
    from parce.lang.css import Css
    yield (Css.root,
"""
h1 {
color: red;
    }
""",
"""
h1 {
    color: red;
}
""")


def test_main():
    i = Indenter()
    i.indent_string = "    "
    for root_lexicon, text, indented in text_fragments():
        d = Document(root_lexicon, text)
        c = Cursor(d, 0, None)      # select all
        i.indent(c)
        assert d.text() == indented


if __name__ == "__main__":
    test_main()
