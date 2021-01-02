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
Testing parce.document.
"""

import os
import sys

sys.path.insert(0, ".")

from parce import Document, Cursor


def test_main():
    filename = os.path.join(os.path.dirname(__file__), '../parce/themes/default.css')
    text = open(filename).read()
    d = Document(None, text)

    # test blocks api
    sep = d.block_separator  # newline
    blocks = list(d.blocks())
    assert d.text().count(sep) == len(blocks) - 1
    assert d.text() == sep.join(b.text() for b in blocks)

    # cursor, editing
    c = Cursor(d)
    d.insert(0, "RANDOM" + sep)
    assert c.text() == "RANDOM" + sep

    with d:
        d[6:6] = " TEXT"
    b = d.find_block(0)
    assert b.text() == "RANDOM TEXT"
    del d[b.pos:b.end+len(sep)]
    assert d.text() == text

    # undo/redo
    d.undo()
    assert d.find_block(0).text() == "RANDOM TEXT"
    while d.can_undo():
        d.undo()
    assert d.text() == text
    assert c.text() == "" and c.pos == 0

    d.redo()
    assert d.find_block(0).text() == "RANDOM"

    # cursor still ok?
    assert c.text() == "RANDOM" + sep


if __name__ == "__main__":
    test_main()
