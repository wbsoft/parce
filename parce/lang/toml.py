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

__all__ = ('Toml',)

import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import (
    Bracket, Comment, Delimiter, Invalid, Literal, Number, Name, Operator,
    Separator, String, Whitespace)
from parce.rule import TEXT, bygroup, call, select


# https://tools.ietf.org/html/rfc3339#section-5.6
RE_FULL_DATE = r"\d{4}-\d\d-\d\d"
RE_PARTIAL_TIME = r"\d\d:\d\d:\d\d(?:\.\d+)?"
RE_TIME_NUMOFFSET = r"[+-]\d\d:\d\d"
RE_TIME_OFFSET = r"(?:[zZ]|" + RE_TIME_NUMOFFSET + ")"
RE_FULL_TIME = RE_PARTIAL_TIME + RE_TIME_OFFSET + '?' # offset may be omitted
RE_DATE_TIME = RE_FULL_DATE + "[ tT]" + RE_FULL_TIME

RE_HEX = r'0[xX](?:_?[0-9a-fA-F])+'
RE_OCT = r'0[oO](?:_?[0-7])+'
RE_BIN = r'0[bB](?:_?[01])+'
RE_DEC = r'[-+]?\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)+)?(?:[eE][-+]?\d(?:_?\d)*)?'


class Toml(Language):
    @lexicon
    def root(cls):
        yield '#', Comment, cls.comment
        yield r'(\[\[)(?:[ \t]*(\.))?', bygroup(Bracket, Invalid), cls.array_table
        yield r'(\[)(?:[ \t]*(\.))?', bygroup(Bracket, Invalid), cls.table
        yield r'=[^\n#]*', Invalid
        yield r'\.[^\n#]*', Invalid
        yield r'\s+', skip
        yield default_target, cls.key

    @lexicon
    def table(cls):
        yield r'(?:(\.)[ \t]*)?(\])([^\n#]*)', \
            bygroup(Invalid, Bracket, select(call(str.isspace, TEXT), Invalid, skip)), -1
        yield from cls.keys()

    @lexicon
    def array_table(cls):
        yield r'(?:(\.)[ \t]*)?(\]\])([^\n#]*)', \
            bygroup(Invalid, Bracket, select(call(str.isspace, TEXT), Invalid, skip)), -1
        yield from cls.keys()

    @lexicon(re_flags=re.MULTILINE)
    def key(cls):
        yield '#', Comment, -1, cls.comment
        yield r'=', Operator.Assignment, -1, cls.value
        yield from cls.keys()

    @lexicon(re_flags=re.MULTILINE)
    def value(cls):
        yield '#', Comment, -1, cls.comment
        yield r'$', None, -1
        yield from cls.values()

    @classmethod
    def keys(cls):
        yield r'[A-Za-z0-9_-]+', Name.Variable
        yield r'''(\.)(?=[ \t]*[\}\],'"A-Za-z0-9_-])''', Delimiter.Dot
        yield r'"', String, cls.string_basic
        yield r"'", String, cls.string_literal
        yield r'[ \t]+', skip
        yield r'[^\s#=\]]+', Invalid

    @classmethod
    def values(cls):
        yield '#', Comment, cls.comment
        yield r'\[', Bracket, cls.array
        yield r'\{', Bracket, cls.inline_table
        yield r'"""', String, cls.string_multiline_basic
        yield r'"', String, cls.string_basic
        yield r"(''')(\n)?", bygroup(String, Whitespace), cls.string_multiline_literal
        yield r"'", String, cls.string_literal
        yield RE_DATE_TIME, Literal.Timestamp
        yield RE_FULL_DATE, Literal.Timestamp
        yield RE_FULL_TIME, Literal.Timestamp
        yield RE_OCT, Number
        yield RE_BIN, Number
        yield RE_HEX, Number
        yield RE_DEC, Number
        yield r"[-+]?\b(?:inf|nan)\b", Number
        yield r"\b(?:true|false)\b", Name.Constant
        yield r'\S+', Invalid

    @lexicon
    def array(cls):
        yield r'(\])([^,}#\n\]]*)', bygroup(Bracket, select(call(str.isspace, TEXT), Invalid, skip)), -1
        yield r',', Separator
        yield from cls.values()

    @lexicon
    def inline_table(cls):
        yield '#', Comment, cls.comment
        yield r'\}', Bracket, -1
        yield r'=', Operator.Assignment.Invalid
        yield r'\s+', skip
        yield default_target, cls.inline_key

    @lexicon
    def inline_key(cls):
        yield r'=', Operator.Assignment, -1, cls.inline_value
        yield r'\}', Bracket.Invalid, -1
        yield from cls.keys()

    @lexicon
    def inline_value(cls):
        yield '#', Comment, cls.comment
        yield r'\}', Bracket, -2
        yield r',', Separator, -1
        yield from cls.values()

    @lexicon
    def string_multiline_basic(cls):
        yield r'(""")([^\s,}#\]]*)', bygroup(String, Invalid), -1
        yield r'\\\s+', Whitespace
        yield r'\\(?:["\\bfnrt]|u[0-9a-fA-F]{4})', String.Escape
        yield r'\\.', String.Invalid
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def string_basic(cls):
        yield r'(")([^\s,}#\]=]*)', bygroup(String, Invalid), -1
        yield r'\\(?:["\\bfnrt]|u[0-9a-fA-F]{4})', String.Escape
        yield r'\\.', String.Invalid
        yield r'[^"]*?$', String.Invalid, -1
        yield default_action, String

    @lexicon
    def string_multiline_literal(cls):
        yield r"(''')([^\s,}#\]]*)", bygroup(String, Invalid), -1
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def string_literal(cls):
        yield r"(')([^\s,}#\]=]*)", bygroup(String, Invalid), -1
        yield r"[^']*?$", String.Invalid, -1
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1

