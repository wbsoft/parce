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
Test the regex module.
"""

## find parce

import sys
sys.path.insert(0, '.')

import re

from parce.regex import *
from parce.lang import lilypond_words
from parce.lang import scheme_words

to_string_tests = (
    ('abcs', True),
    ('sd.sd', False),
    ('^edt', False),
    ('test$', False),
    ('[cd]fg', False),
    (r'\[cd\]fg', True),
    (r'a{2,3}', False),
    (r'abc\N{SPACE}', True),
    (r'(1)23456\1', False),
    (r'a\023b', True),
    (r'a\028b', True),
)

def check_word_list(words):
    rx = re.compile(words2regexp(words))
    for w in words:
        assert rx.fullmatch(w)


def test_main():
    """Write stuff to test here."""

    check_word_list(lilypond_words.all_pitch_names)
    check_word_list(scheme_words.keywords)

    for expr, result in to_string_tests:
        assert bool(to_string(expr)) is result


if __name__ == "__main__":
    test_main()

