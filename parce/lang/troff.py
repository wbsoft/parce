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

__all__ = ('Troff',)

import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import (
        Comment, Delimiter, Name, Number, Operator, String, Text)
from parce.rule import bygroup


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
        yield r'([-+]?(?:\d+(?:\.\d*)?)|\.\d+)([ciPpmMnuvsf])?', bygroup(Number, Name.Unit)
        yield r'[-+*/%=<>&:!()]|[=<>]=', Operator
        yield r'[<>]\?|;', Operator # GNU extension
        yield default_action, Text

    @lexicon
    def name(cls):
        """The name of a request, handle some special preprocessor macros."""
        yield r'lilypond\b', Name.Identifier.Preprocessed, -1, cls.preprocess_lilypond
        yield r'[^\W\d]\w*\b', Name.Identifier, -1
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def string(cls):
        """String in request arguments."""
        yield r'$', None, -1
        yield r'"', String, -1
        yield from cls.escapes(String)
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield r'$', None, -1
        yield from cls.comment_common()

    @lexicon
    def preprocess_lilypond(cls):
        """If "start" is found, go to LilyPond, otherwise back to the request context."""
        yield r'[ \t]*(start)\b', bygroup(Name.Command), -2, cls.lilypond, cls.request
        yield default_target, -1 # back to request

    @lexicon(re_flags=re.MULTILINE)
    def lilypond(cls):
        """Stuff between .lilypond start and .lilypond end."""
        from .lilypond import LilyPond
        yield r"^(['.])[ \t]*(lilypond) +(end)\b", \
            bygroup(Delimiter.Request, Name.Identifier.Preprocessed, Name.Command), \
            -1
        yield from LilyPond.root

    @classmethod
    def escapes(cls, escape_base=Text):
        # escapes (man 7 groff)
        yield r'\\["#]', Comment, cls.comment
        # prevent interpreting request after continuation line
        yield r"(\\\n)([.'])?", bygroup(escape_base.Escape, Text)
        # single char escapes
        yield r"\\[\\'`_.%! 0|^&)/,~:{}acdeEprtu-]", escape_base.Escape
        # escapes expecting single, two-char or bracketed arg
        yield r"\\[\*$fFgkmMnVY](?:\[[^\]\n]*\]|\(..|.)", escape_base.Escape
        # \s
        yield r"\\s[-+]?(?:\d|\([-+]?\d\d|\[[\d+-]+\]|'[\d+-]+')", escape_base.Escape
        # escapes expecting a single-quoted argument
        yield r"\\[AbBCDlLnoRsSvwxXZ](?:'[^'\n]*')?", escape_base.Escape
        # \(<xx> or \[<xxxx>]
        yield r"\\(?:\[[^\]\n]*\]|\(..)", escape_base.Escape
        # undefined (last resort)
        yield r"\\", escape_base.Escape

