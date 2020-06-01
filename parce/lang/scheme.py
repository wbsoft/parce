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
"""

__all__ = ('Scheme', 'SchemeLily')

import re


from parce import Language, lexicon, skip, default_action, default_target
from parce.action import (
    Bracket, Character, Comment, Delimiter, Keyword, Name, Number, String)
from parce.rule import TEXT, bygroup, ifmember, gselect

RE_SCHEME_RIGHT_BOUND = r"(?=$|[)\s])"
RE_SCHEME_NUMBER = (r"(#[eEiI])?(#d)?("             # #e, #i and/or #d prefix
    r"([-+]?(?:(?:\d+(?:\.\d*)|\.\d+)(?:[eE]\d+)?))"# float
    r"|[-+]?\d+(?:(/\d+)|())"                       # fraction, int
    r"|#(?:([bB][-+]?[0-1]+)"                       # binary
        r"|([oO][-+]?[0-7]+)"                       # octal
        r"|([xX][-+]?[0-9a-fA-F]+))"                # hexadecimal
    r"|[-+](?:([iI][nN][fF])|([nN][aA][nN]))\.0"    # inf, NaN
    r")" + RE_SCHEME_RIGHT_BOUND
)

class Scheme(Language):
    @lexicon
    def root(cls):
        yield from cls.common()

    @classmethod
    def common(cls, pop=0):
        """Yield common stuff. ``pop`` can be set to -1 for one-arg mode."""
        yield r"['`,]", Delimiter.Scheme.Quote
        yield r"\(", Delimiter.OpenParen, pop, cls.list
        yield r"#\(", Delimiter.OpenVector, pop, cls.vector
        yield r'"', String, pop, cls.string
        yield r';', Comment, pop, cls.singleline_comment
        yield r'#!', Comment, pop, cls.multiline_comment
        yield RE_SCHEME_NUMBER, bygroup(
            Number.Prefix, Number.Prefix,
            gselect(None, None, None,
                Number.Float, Number.Fraction, Number.Int,
                Number.Binary, Number.Octal, Number.Hexadecimal,
                Number.Infinity, Number.NaN)), pop
        if pop == 0:
            yield r"\.(?!\S)", Delimiter.Dot
        yield r"#[tTfF]\b", Number.Boolean, pop
        yield r"#\\([a-z]+|.)", Character, pop
        yield r'[^()"{}\s]+', cls.get_word_action(), pop

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

    # -------------- String ---------------------
    @lexicon(consume=True)
    def string(cls):
        yield r'"', String, -1
        yield from cls.string_common()

    @classmethod
    def string_common(cls):
        yield r'\\[\\"]', String.Escape
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

