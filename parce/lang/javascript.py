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
Parse JavaScript.

"""

import re

from parce import *
from .javascript_words import *


class JavaScript(Language):
    @lexicon
    def root(cls):
        yield r"'", String.Start, cls.string("'")
        yield r'"', String.Start, cls.string('"')
        yield '//', Comment, cls.singleline_comment
        yield r'/\*', Comment.Start, cls.multiline_comment
        yield words(JAVASCRIPT_KEYWORDS, prefix=r'\b', suffix=r'\b'), Keyword
        yield words(JAVASCRIPT_RESERVED_KEYWORDS, prefix=r'\b', suffix=r'\b'), Keyword.Reserved
        yield words(JAVASCRIPT_CONSTANTS, prefix=r'\b', suffix=r'\b'), Name.Constant
        yield words(JAVASCRIPT_BUILTINS, prefix=r'\b', suffix=r'\b'), Name.Builtin

    @lexicon
    def string(cls):
        yield arg(), String.End, -1
        yield (r'''\\(?:[0"'\\nrvtbf]'''
            r'|x[a-fA-F0-9]{2}'
            r'|u\d{4}'
            r'|u\{[a-fA-F0-9]{1,5}\})'), String.Escape
        yield default_action, String

    #------------------ comments -------------------------
    @lexicon
    def singleline_comment(cls):
        yield '$', None, -1
        yield from cls.comment_common()

    @lexicon
    def multiline_comment(cls):
        yield r'\*/', Comment.End, -1
        yield from cls.comment_common()

