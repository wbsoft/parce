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
Parse Python.

"""

import re


from parce import *


RE_PYTHON_IDENTIFIER = _I_ = r'[^\W\d]\w*'
RE_PYTHON_HORIZ_SPACE = _S_ = r'[^\S\n]'


class Python(Language):
    @lexicon(re_flags=re.MULTILINE)
    def root(cls):
        yield r'^\s+($|(?=#))?', ifgroup(1, Whitespace, Whitespace.Indent)
        yield fr'(class\b){_S_}*({_I_})', bygroup(Keyword, Name.Class), cls.classdef
        yield fr'(def\b){_S_}*({_I_})', bygroup(Keyword, Name.Function), cls.funcdef
        yield from cls.common()

    @classmethod
    def common(cls):
        yield r'#', Comment, cls.comment
        yield r'\[', Delimiter, cls.list
        yield r'\(', Delimiter, cls.tuple

    @lexicon
    def funcdef(cls):
        """A function definition."""
        yield r'\(', Delimiter, cls.signature
        yield r':', Delimiter.Indent, -1
        yield r'#', Comment, -1, cls.comment

    @lexicon
    def signature(cls):
        """A function signature."""
        yield r'\)', Delimiter, -1
        yield from cls.common()

    @lexicon
    def classdef(cls):
        """A class definition."""
        yield r'\(', Delimiter, cls.bases
        yield ":", Delimiter.Indent, -1
        yield r'#', Comment, -1, cls.comment

    @lexicon
    def bases(cls):
        """The base classes in a class definition."""
        yield r'\)', Delimiter, -1
        yield from cls.common()

    ## ----- item types -------------
    @lexicon
    def list(cls):
        """A python list."""
        yield r'\]', Delimiter, -1
        yield from cls.common()

    @lexicon
    def tuple(cls):
        """A python tuple."""
        yield r'\)', Delimiter, -1
        yield from cls.common()

    ## ------- comments -------------
    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1

