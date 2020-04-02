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
Testing CSS parser with pytest-3.
"""

import sys

sys.path.insert(0, ".")

from parce import *



class LeafTest(Language):
    @lexicon
    def root(cls):
        yield "A", Text, cls.leaf, cls.second
        yield "B", Text, cls.leaf

    @lexicon
    def leaf(cls):
        yield "B", Text
        yield "C", Text, -1

    @lexicon
    def second(cls):
        yield "C", Text, -1


def test_main():
    b = treebuilder.BasicTreeBuilder(LeafTest.root)
    b.build("ACBCBBBB")
    # removing the first two characters causes a leaf context to be merged with
    # a non-leaf context, proving that the leaf context stuff is a failed virtue
    # ;-( :-D
    b.rebuild("BCBBBB", False, 0, 2, 0)

if __name__ == "__main__":
    test_main()
