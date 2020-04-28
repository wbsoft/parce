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
Parse various troff dialects, most notably groff.
https://www.gnu.org/software/groff/

"""


import re

from parce import *


class Troff(Language):
    @lexicon(re_flags=re.MULTILINE)
    def root(cls):
        yield r"^(['.])[ \t]*", bygroup(Delimiter.Request), cls.request, cls.name
        yield from cls.escapes()
        yield default_action, Text

    @lexicon(re_flags=re.MULTILINE)
    def request(cls):
        yield from cls.escapes()
        yield r'\n', skip, -1
        yield r' (")', bygroup(String), cls.string
        yield default_action, Text

    @lexicon
    def name(cls):
        """The name of a request."""
        yield r'[^\W\d]\w*\b', Name.Identifier, -1
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def string(cls):
        """String in request arguments."""
        yield r'$', None, -1
        yield r'"', String, -1
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield r'$', None, -1
        yield from cls.comment_common()

    @classmethod
    def escapes(cls):
        # escapes (man 7 groff)
        yield r'\\["#]', Comment, cls.comment
        # prevent interpreting request after continuation line
        yield r"(\\\n)([.'])?", bygroup(Escape, Text)
        # single char escapes
        yield r"\\[\\'`_.%! 0|^&)/,~:{}acdeEprtu-]", Escape
        # escapes expecting single, two-char or bracketed arg
        yield r"\\[\*$fFgkmMnVYs](?:\[[^\]\n]*\]|\(..|.)", Escape
        # escapes expecting a single-quoted argument
        yield r"\\[AbBCDlLnoRsSvwxXZ](?:'[^'\n]*')?", Escape
        # \(<xx> or \[<xxxx>]
        yield r"\\(?:\[[^\]\n]*\]|\(..)", Escape
        # undefined (last resort)
        yield r"\\", Escape


