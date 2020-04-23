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
Tom's Obvious, Minimal Language.
https://github.com/toml-lang/toml
"""

import re


from parce import *


class Toml(Language):
    @lexicon
    def root(cls):
        yield from cls.values()

    @classmethod
    def values(cls):
        yield r'"""', String, cls.string_multiline_basic
        yield r'"', String, cls.string_basic
        yield r"(''')(\n)?", bygroup(String, Whitespace), cls.string_multiline_literal
        yield r"'", String, cls.string_literal
        yield r'0[oO](?:_?[0-7])+', Number
        yield r'0[bB](?:_?[01])+', Number
        yield r'0[xX](?:_?[0-9a-fA-F])+', Number
        yield r'[-+]?\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)+)?(?:[eE][-+]\d(?:_?\d)*)?', Number
        yield r"[-+]?\b(?:inf|nan)\b", Number
        yield r"\b(?:true|false)\b", Name.Constant

    @lexicon
    def string_multiline_basic(cls):
        yield r'(""")([^\s,}]*)', bygroup(String, Invalid), -1
        yield r'\\\s+', Whitespace
        yield r'\\(?:["\\bfnrt]|u[0-9a-fA-F]{4})', String.Escape
        yield r'\\.', String.Invalid
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def string_basic(cls):
        yield r'(")([^\s,}]*)', bygroup(String, Invalid), -1
        yield r'\\(?:["\\bfnrt]|u[0-9a-fA-F]{4})', String.Escape
        yield r'\\.', String.Invalid
        yield r'[^"]*?$', String.Invalid
        yield default_action, String

    @lexicon
    def string_multiline_literal(cls):
        yield r"(''')([^\s,}]*)", bygroup(String, Invalid), -1
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def string_literal(cls):
        yield r"(')([^\s,}]*)", bygroup(String, Invalid), -1
        yield r"[^']*?$", String.Invalid
        yield default_action, String


