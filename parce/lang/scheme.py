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
Scheme.

Tries to adhere to the official Scheme syntax, especially the complicated
number syntax. See for more information:

* https://www.gnu.org/software/guile/manual/r5rs.html#Formal-syntax
* https://www.scheme.com/tspl4/grammar.html

"""

__all__ = ('Scheme', 'SchemeLily')

import re


from parce import Language, lexicon, skip, default_action, default_target
from parce.action import *
from parce.rule import *


RE_SCHEME_RIGHT_BOUND = r"(?=$|[()\s;]|#\()"

RE_SCHEME_ID_SPECIAL_INITIAL = r'!$%&*/:<=>?^_~'
RE_SCHEME_ID_INITIAL = r'(?:[^\W\d]|[' + RE_SCHEME_ID_SPECIAL_INITIAL + '])'
RE_SCHEME_ID_SUBSEQUENT = r'[\w' + RE_SCHEME_ID_SPECIAL_INITIAL + '@.+-]'
RE_SCHEME_ID_PECULIAR = r'[-+]|\.{3}'

RE_SCHEME_ID = r'(?:' + \
    RE_SCHEME_ID_PECULIAR + \
    '|' + RE_SCHEME_ID_INITIAL + '(?:' + RE_SCHEME_ID_SUBSEQUENT + ')*' + \
    ')' + RE_SCHEME_RIGHT_BOUND


class Scheme(Language):
    @lexicon
    def root(cls):
        yield from cls.common()

    @classmethod
    def common(cls, pop=0):
        """Yield common stuff. ``pop`` can be set to -1 for one-arg mode."""
        yield r"['`]|,@?", Delimiter.Scheme.Quote
        yield r"\(", Delimiter.OpenParen, pop, cls.list
        yield r"#\(", Delimiter.OpenVector, pop, cls.vector
        yield r'"', String, pop, cls.string
        yield r';', Comment, pop, cls.singleline_comment
        yield r'#!', Comment, pop, cls.multiline_comment

        yield r"#[tTfF]\b", Number.Boolean, pop
        yield r"#\\([a-z]+|.)", Character, pop

        yield r'(#[eEiI])?(#([bBoOxXdD]))', \
            bygroup(Number.Prefix, Number.Prefix), pop, \
            findmember(MATCH[3], (
                ('bB', cls.number(2)),
                ('oO', cls.number(8)),
                ('xX', cls.number(16))), cls.number)
        yield r'#[eEiI]', Number.Prefix, pop, cls.number
        yield r'[-+]inf.0', Number.Infinity, pop, cls.number
        yield r'[-+]nan.0', Number.NaN, pop, cls.number
        yield r'[-+]', Operator.Sign, pop, cls.number
        yield r'(\.?)(\d+)(#*)', bygroup(Number.Dot, Number.Decimal, Number.Special.UnknownDigit), \
            pop, cls.number

        if pop == 0:
            yield r"\.(?!\S)", Delimiter.Dot

    @lexicon(consume=True)
    def list(cls):
        yield r"\)", Delimiter.CloseParen, -1
        yield from cls.common()

    @lexicon(consume=True)
    def vector(cls):
        yield r"\)", Delimiter.CloseVector, -1
        yield from cls.common()

    @classmethod
    def get_word_action(cls):
        """Return a dynamic action that is chosen based on the text."""
        from . import scheme_words
        return ifmember(TEXT, scheme_words.keywords, Keyword, Name)

    # -------------- Number ---------------------
    @lexicon(consume=True, re_flags=re.I)
    def number(self):
        """Decimal numbers, derive with 2 for binary, 8 for octal, 16 for hexadecimal numbers."""
        yield RE_SCHEME_RIGHT_BOUND, None, -1
        _pat = lambda radix: '([{}]+)(#*)'.format('0123456789abcdef'[:radix or 10])
        yield pattern(call(_pat, ARG)), bygroup(
            dselect(ARG, {2: Number.Binary, 8: Number.Octal, 16: Number.Hexadecimal}, Number.Decimal),
            Number.Special.UnknownDigit)
        yield r'[-+]inf.0', Number.Infinity
        yield r'[-+]nan.0', Number.NaN
        yield r'[-+]', Operator.Sign
        yield 'i', Number.Imaginary
        yield ifarg(None, '[esfdl]'), Number.Exponent
        yield ifarg(None, r'\.'), Number.Dot
        yield '@', Separator.Polar
        yield '/', Separator.Fraction
        yield default_action, Number.Invalid

    # -------------- String ---------------------
    @lexicon(consume=True)
    def string(cls):
        yield r'"', String, -1
        yield from cls.string_common()

    @classmethod
    def string_common(cls):
        yield r'\\[\\"|afnrtvb]', String.Escape
        yield default_action, String

    # -------------- Comment ---------------------
    @lexicon(consume=True)
    def multiline_comment(cls):
        yield r'!#', Comment, -1
        yield from cls.comment_common()

    @lexicon(re_flags=re.MULTILINE, consume=True)
    def singleline_comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1


class SchemeLily(Scheme):
    """Scheme used with LilyPond."""
    @lexicon(consume=True)
    def scheme(cls):
        """Pick one thing and pop back."""
        yield r'\s+', skip
        yield from cls.common(cls.argument)
        yield default_target, -1

    @lexicon(consume=True)
    def argument(cls):
        """One Scheme expression."""
        yield default_target, -2

    @classmethod
    def common(cls, pop=0):
        from . import lilypond
        yield r"#{", Bracket.LilyPond.Start, pop, lilypond.LilyPond.schemelily
        yield from super().common(pop)

