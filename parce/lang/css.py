# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2019 by Wilbert Berendsen <info@wilbertberendsen.nl>
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


"""A CSS parser.

https://www.w3.org/TR/css-syntax-3/

We want also to use this parser inside parce, to be able to store default
highlighting formats in css files.

"""

import re

from parce import *


RE_CSS_ESCAPE = r"\\(?:[0-9A-Fa-f]{1,6} ?|.)"
RE_CSS_NUMBER = (
    r"[+-]?"             # sign
    r"(?:\d*\.)?\d+"     # mantisse
    r"([Ee][+-]\d+)?")   # exponent
RE_CSS_IDENTIFIER_LA = r"(?=-?(?:[^\W\d]|\\[0-9A-Fa-f])|--)" # lookahead
RE_CSS_IDENTIFIER = (
    r"(?:-?(?:[^\W\d]+|" + RE_CSS_ESCAPE + r")|--)"
    r"(?:[\w-]+|" + RE_CSS_ESCAPE + r")*")
RE_CSS_AT_KEYWORD = r"@" + RE_CSS_IDENTIFIER


class Css(Language):
    @lexicon
    def root(cls):
        yield from cls.common()

    @classmethod
    def common(cls):
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
        yield r"\{", Delimiter, cls.block
        yield RE_CSS_NUMBER, Number
        yield r"(url)(\()", bygroup(Name, Delimiter), cls.url_function
        yield r"@", Keyword, cls.atrule
        # an ident-token is found using a lookahead pattern, the whole ident-
        # token is in the identifier context
        yield RE_CSS_IDENTIFIER_LA, Name, cls.identifier

    @lexicon
    def block(cls):
        """Contents between { and }."""
        yield r"\}", Delimiter, -1
        yield from cls.style()

    @lexicon
    def style(cls):
        """CSS that would be in a block, but also in a HTML style attribute."""
        yield from cls.common()

    @lexicon
    def atrule(cls):
        """Contents following '@'."""
        yield from cls.identifier()

    @lexicon
    def identifier(cls):
        """An ident-token is always just a context, it contains all parts."""
        yield RE_CSS_ESCAPE, Escape
        yield r"[\w-]+", Name
        yield r"\(", Delimiter, -1, cls.function
        yield default_target, -1

    @lexicon
    def function(cls):
        yield r"\)", Delimiter, -1
        yield from cls.common()

    @lexicon
    def url_function(cls):
        """url(....)"""
        yield r"\)", Delimiter, -1
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
        yield RE_CSS_ESCAPE, Escape
        yield default_action, Literal.Url

    @lexicon
    def dqstring(cls):
        """A double-quoted string."""
        yield r'"', String, -1
        yield from cls.string()

    @lexicon
    def sqstring(cls):
        """A single-quoted string."""
        yield r"'", String, -1
        yield from cls.string()

    @classmethod
    def string(cls):
        """Common rules for string."""
        yield default_action, String
        yield RE_CSS_ESCAPE, String.Escape
        yield r"\\\n", String.Escape
        yield r"\n", Error, -1

    @lexicon
    def comment(cls):
        """A comment."""
        yield r"\*/", Comment, -1
        yield default_action, Comment




