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


import re


from parce import *

RE_SCHEME_RIGHT_BOUND = r"(?=$|[)\s])"
RE_SCHEME_FRACTION = r"-?\d+/\d+" + RE_SCHEME_RIGHT_BOUND
RE_SCHEME_FLOAT = r"-?((\d+(\.\d*)|\.\d+)(E\d+)?)" + RE_SCHEME_RIGHT_BOUND
RE_SCHEME_NUMBER = (
    r"("
    r"-?\d+|"
    r"#(b[0-1]+|o[0-7]+|x[0-9a-fA-F]+)|"
    r"[-+]inf.0|[-+]?nan.0"
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
        yield RE_SCHEME_FRACTION, Number.Fraction, pop
        yield RE_SCHEME_FLOAT, Number.Float, pop
        yield RE_SCHEME_NUMBER, Number, pop
        if pop == 0:
            yield r"\.(?!\S)", Delimiter.Dot
        yield r"#[tf]\b", Boolean, pop
        yield r"#\\([a-z]+|.)", Character, pop
        yield r'[^()"{}\s]+', cls.get_word_action(), pop

    @lexicon
    def list(cls):
        yield r"\)", Delimiter.CloseParen, -1
        yield from cls.common()

    @lexicon
    def vector(cls):
        yield r"\)", Delimiter.CloseVector, -1
        yield from cls.common()

    @classmethod
    def get_word_action(cls):
        """Return a dynamic action that is chosen based on the text."""
        from . import scheme_words
        return ifmember(scheme_words.keywords, Keyword, Name)

    # -------------- String ---------------------
    @lexicon
    def string(cls):
        yield r'"', String, -1
        yield from cls.string_common()

    @classmethod
    def string_common(cls):
        yield r'\\[\\"]', String.Escape
        yield default_action, String

    # -------------- Comment ---------------------
    @lexicon
    def multiline_comment(cls):
        yield r'!#', Comment, -1
        yield from cls.comment_common()

    @lexicon(re_flags=re.MULTILINE)
    def singleline_comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1


class SchemeLily(Scheme):
    """Scheme used with LilyPond."""
    @lexicon
    def one_arg(cls):
        """Pick one thing and pop back."""
        yield r'\s+', skip
        yield from cls.common(-1)
        yield default_target, -1

    @classmethod
    def common(cls, pop=0):
        from . import lilypond
        yield r"#{", Bracket.LilyPond.Start, pop, lilypond.LilyPond.schemelily
        yield from super().common(pop)

