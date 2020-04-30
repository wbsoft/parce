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
from parce.unicharclass import categories
from .javascript_words import *


RE_JS_IDENT_STARTCHAR = r'$_' + ''.join(map(categories.get, ['Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl']))
RE_JS_IDENT_CHAR = RE_JS_IDENT_STARTCHAR + '\u200c\u200d' + ''.join(map(categories.get, ['Mn', 'Mc', 'Nd', 'Pc']))
RE_JS_ESCAPE_CHAR = r'\\u[0-9a-fA-F]{4}'
RE_JS_IDENT_TOKEN = _I_ = fr'(?:[{RE_JS_IDENT_STARTCHAR}]|{RE_JS_ESCAPE_CHAR})' \
                fr'(?:[{RE_JS_IDENT_CHAR}]+|{RE_JS_ESCAPE_CHAR})*'



class JavaScript(Language):
    @lexicon
    def root(cls):
        yield r"'", String.Start, cls.string("'")
        yield r'"', String.Start, cls.string('"')
        yield '//', Comment, cls.singleline_comment
        yield r'/\*', Comment.Start, cls.multiline_comment
        yield fr'(const|let|var)\s+({_I_})\b', bygroup(Keyword, Name.Variable.Definition)
        yield fr'(function)\s+({_I_})\b', bygroup(Keyword, Name.Function.Definition)
        yield fr'(new)\s+({_I_})\b', bygroup(Keyword, Name.Class.Definition)
        yield words(JAVASCRIPT_KEYWORDS, prefix=r'\b', suffix=r'\b'), Keyword
        yield words(JAVASCRIPT_DECLARATORS, prefix=r'\b', suffix=r'\b'), Keyword
        yield words(JAVASCRIPT_RESERVED_KEYWORDS, prefix=r'\b', suffix=r'\b'), Keyword.Reserved
        yield words(JAVASCRIPT_CONSTANTS, prefix=r'\b', suffix=r'\b'), Name.Constant
        yield words(JAVASCRIPT_BUILTINS, prefix=r'\b', suffix=r'\b'), Name.Builtin
        yield words(JAVASCRIPT_PROTOTYPES, prefix=r'\b', suffix=r'\b'), Name.Builtin
        yield fr'(\.)\s*({_I_})\b(?:\s*([\(\[]))?', bygroup(Delimiter,
                mapgroup(3, {'(': Name.Method}, Name.Attribute), Delimiter), \
            mapgroup(3, {'(': cls.call, '[': cls.index})
        yield fr'({_I_})\b(?:\s*([\(\[]))?', bygroup(
                mapgroup(2, {'(': Name.Function}, Name.Variable), Delimiter), \
            mapgroup(2, {'(': cls.call, '[': cls.index})
        yield fr'{_I_}\b', bytext(str.isupper, Name.Variable, Name.Class)
        ## numerical values (recently, underscore support inside numbers was added)
        yield '0[oO](?:_?[0-7])+', Number
        yield '0[bB](?:_?[01])+', Number
        yield '0[xX](?:_?[0-9a-fA-F])+', Number
        yield r'(?:\.\d(?:_?\d)*|\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?)(?:[eE][-+]\d(?:_?\d)*)?', Number
        yield r'\{', Bracket.Start, cls.scope
        yield r'\[', Bracket.Start, cls.array
        yield r'\(', Delimiter, cls.paren

    @lexicon
    def scope(cls):
        yield r'\}', Bracket.End, -1
        yield from cls.root

    @lexicon
    def call(cls):
        """name(...) syntax."""
        yield r'\)', Delimiter, -1
        yield from cls.root

    @classmethod
    def expression(cls):
        """Stuff between ( ) or [ ]"""
        yield r'\{', Bracket.Start, cls.object
        yield from cls.root

    @lexicon
    def object(cls):
        """An object (dictionary) { ... }."""
        yield r'[:,]', Separator
        yield r'\}', Bracket.End, -1
        yield from cls.expression()

    @lexicon
    def array(cls):
        """An array [ ... ]."""
        yield r'[,]', Separator
        yield r'\]', Bracket.End, -1
        yield from cls.expression()

    @lexicon
    def paren(cls):
        """An array [ ... ]."""
        yield r'[,]', Separator
        yield r'\)', Delimiter, -1
        yield from cls.expression()

    @lexicon
    def index(cls):
        """name[...] syntax."""
        yield r'\]', Delimiter, -1
        yield from cls.root

    @lexicon
    def string(cls):
        yield arg(), String.End, -1
        yield (r'''\\(?:[0"'\\nrvtbf]'''
            r'|x[a-fA-F0-9]{2}'
            r'|u\d{4}'
            r'|u\{[a-fA-F0-9]{1,5}\})'), String.Escape
        yield default_action, String

    #------------------ comments -------------------------
    @lexicon(re_flags=re.MULTILINE)
    def singleline_comment(cls):
        yield '$', None, -1
        yield from cls.comment_common()

    @lexicon
    def multiline_comment(cls):
        yield r'\*/', Comment.End, -1
        yield from cls.comment_common()

