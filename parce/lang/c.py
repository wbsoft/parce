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
Parse C.

"""

__all__ = ('C',)

import re

from parce import Language, lexicon, default_action, default_target, skip
from parce.action import *
from parce.rule import *

# support C/C++ UCN
RE_C_IDENT_ESCAPE = _E_ = r'\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}'
RE_C_IDENT_START  = fr'[^\W\d]|\$|{_E_}'
RE_C_IDENT_CONT   = fr'[\w$]|{_E_}'
RE_C_IDENT = r'(?:{})(?:{})*'.format(RE_C_IDENT_START, RE_C_IDENT_CONT)

RE_C_NUMBER = (r'[-+]?(?:'
    r'0(?:([oO]?[0-7]+)'                            # 1 octal
        r'|([bB][01]+)'                             # 2 binary
        r'|([xX][0-9a-fA-F]+))'                     # 3 hexadecimal
    r'|((?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)'  # 4 decimal
    r')'
)


class C(Language):
    @lexicon
    def root(cls):
        """All C language constructs."""
        yield r'(struct|union|enum)\b', Keyword, cls.class_name
        yield words(C_TYPES, suffix=r'\b'), Name.Type
        yield words(C89_WORDS + C99_WORDS + C11_WORDS, suffix=r'\b'), Keyword
        yield '"', String.Start, cls.string
        yield fr'({RE_C_IDENT})\s*(\()?', ifgroup(2,
            (bygroup(using(cls._func_name), Delimiter), cls.arguments),
             bygroup(using(cls._variable_name)))
        yield '//', Comment, cls.singleline_comment
        yield r'/\*', Comment.Start, cls.multiline_comment
        yield r'\{', Bracket.Start, cls.compound
        yield '#', Delimiter.Preprocessed, cls.macro
        yield r'\(', Delimiter.Start, cls.paren
        yield r';', Delimiter
        yield RE_C_NUMBER, gselect(Number.Octal, Number.Binary, Number.Hexadecimal, Number.Decimal)
        yield r',', Delimiter.Separator
        yield r'(?:[*/%+&\-|]|<<|>>)=', Operator.Assignment
        yield r'\+\+?|--?|\*\*?|<[=<]?|>[=>]?|&&?|\|\|?|[=!]=|[~!/%^?:]', Operator
        yield r'=', Operator.Assignment

    @lexicon
    def compound(cls):
        """Stuff between ``{`` ... ``}``."""
        yield r'\}', Bracket.End, -1
        yield from cls.root

    @lexicon
    def paren(cls):
        """Stuff between ``(`` ... ``)``."""
        yield r'\)', Delimiter, -1
        yield from cls.root

    @lexicon
    def arguments(cls):
        """Stuff between ``name(`` ... ``)``."""
        yield r'\)', Delimiter, -1
        yield from cls.root

    @lexicon
    def class_name(cls):
        """The class name after struct, union or enum."""
        yield RE_C_IDENT, using(cls._class_name), -1
        yield r'\s+', skip
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def string(cls):
        """A double-quoted string."""
        yield r'"', String.End, -1
        yield r'\\["\\nrbtfav?]', String.Escape
        yield RE_C_IDENT_ESCAPE, String.Escape
        yield r'\\.', String.Invalid
        yield r'[^"]*?$', String.Invalid, -1
        yield default_action, String

    @lexicon
    def macro(cls):
        """Stuff after ``#``."""
        yield r'include\b', Keyword.Preprocessed
        yield '"', String.Start, cls.string
        yield r'<.*?>', String.Template
        yield r'[ \t]', skip
        yield default_target, -1

    # these lexicons are used to split escaped parts out of long
    # var/class/funcnames

    @lexicon
    def _class_name(cls):
        yield RE_C_IDENT_ESCAPE, Escape
        yield default_action, Name.Class

    @lexicon
    def _func_name(cls):
        yield RE_C_IDENT_ESCAPE, Escape
        yield default_action, Name.Function

    @lexicon
    def _variable_name(cls):
        yield RE_C_IDENT_ESCAPE, Escape
        yield default_action, Name.Variable

    #------------------ comments -------------------------
    @lexicon(re_flags=re.MULTILINE)
    def singleline_comment(cls):
        yield '$', None, -1
        yield from cls.comment_common()

    @lexicon
    def multiline_comment(cls):
        yield r'\*/', Comment.End, -1
        yield from cls.comment_common()




# source: https://en.wikipedia.org/wiki/C_(programming_language)
C_TYPES = (
    "int", "bool", "char", "long", "double", "float", "signed", "unsigned",
    "short",
)

C89_WORDS = (
    "auto", "break", "case", "const", "continue", "default", "do", "double",
    "else", "enum", "extern", "for", "goto", "if", "register", "return",
    "sizeof", "static", "struct", "switch", "typedef", "union", "void",
    "volatile", "while",
)

C99_WORDS = (
    "_Bool", "_Complex", "_Imaginary", "inline",
)

C11_WORDS = (
    "_Alignas", "_Alignof", "_Atomic", "_Generic", "_Noreturn",
    "_Static_assert", "_Thread_local",
)

