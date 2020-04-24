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
Test proper functioning of all examples in the ./lang directory.
"""

EXAMPLES_DIRECTORY = "tests/lang/"

import glob
import os
import sys

sys.path.insert(0, ".")

import parce


def get_examples():
    """Return a list of all example documents in tests/lang/example.*."""
    pattern = os.path.join(EXAMPLES_DIRECTORY, "example*.*")
    return glob.glob(pattern)


def test_main():
    for filename in get_examples():
        print("Testing:", filename)
        text = open(filename).read()    # TODO encoding?
        root_lexicon = parce.find(filename=filename, contents=text)
        assert root_lexicon
        print("Root lexicon: {}, result tree:".format(root_lexicon))
        parce.root(root_lexicon, text).dump()


if __name__ == "__main__":
    test_main()
