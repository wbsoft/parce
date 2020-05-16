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
Test various transformations.
"""

import sys
sys.path.insert(0, '.')

import parce.transform


def transform_file(filename, root_lexicon=None, transform=None):
    s = open(filename).read()
    if root_lexicon is None:
        root_lexicon = parce.find(filename=filename, contents=s)
    return parce.transform.transform_text(root_lexicon, s, transform)

JSON_RESULT = \
{'background': 'background.png',
 'comment': 'JSON example',
 'contents': [{'path': '/Applications', 'type': 'link', 'x': 449, 'y': 320},
              {'path': '../dist/Frescobaldi.app',
               'type': 'file',
               'x': 188,
               'y': 320},
              {'path': '../README.txt', 'type': 'file', 'x': 100, 'y': 70},
              {'path': '../ChangeLog.txt', 'type': 'file', 'x': 100, 'y': 185},
              {'path': '../COPYING.txt', 'type': 'file', 'x': 540, 'y': 70}],
 'icon-size': 80,
 'title': 'Frescobaldi'}



def test_main():

    result = transform_file('tests/lang/example.json')
    assert result == JSON_RESULT


if __name__ == "__main__":
    test_main()

