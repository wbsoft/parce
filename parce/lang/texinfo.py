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
Parse GNU Texinfo.

https://www.gnu.org/software/texinfo/

"""

__all__ = ('Texinfo',)

import re

from parce import Language, lexicon, default_action
from parce.action import (
    Bracket, Comment, Delimiter, Escape, Keyword, Name, Verbatim, Text)
from parce.rule import bygroup, ifgroup


class Texinfo(Language):

    @lexicon
    def root(cls):
        yield r'@[@{}. ]', Escape
        yield r'''@['",=^`~](\{[a-zA-Z]\}|[a-zA-Z]\b)''', Escape
        yield r'@c(?:omment)?\b', Comment, cls.singleline_comment
        yield r'@ignore\b', Comment, cls.multiline_comment
        yield r'@verbatim\b', Keyword.Verbatim, cls.verbatim
        yield r'@html', Keyword, cls.html
        yield r'(@lilypond)\b(?:(\[)([^\n\]]*)(\]))?(\{)?', bygroup(
            Name.Function, Bracket, Name.Property, Bracket, Bracket.Start), \
            ifgroup(5, cls.lilypond_brace, cls.lilypond_block)
        yield r'(@[a-zA-Z]+)(?:(\{)(\})?)?', bygroup(
                ifgroup(2, ifgroup(3, Name.Symbol, Name.Function), Name.Command),
                Bracket.Start,
                Bracket.End), \
            ifgroup(2, ifgroup(3, (), cls.brace))
        yield default_action, Text

    @lexicon
    def brace(cls):
        yield r'\}', Bracket.End, -1
        yield from cls.root

    @lexicon
    def verbatim(cls):
        yield r'(@end)[ \t]+(verbatim)\b', bygroup(Keyword, Keyword.Verbatim), -1
        yield default_action, Verbatim

    @lexicon
    def html(cls):
        from .html import Html
        yield r'(@end)[ \t]+(html)\b', bygroup(Keyword, Keyword), -1
        yield from Html.root

    @lexicon
    def lilypond_block(cls):
        from .lilypond import LilyPond
        yield r'(@end)[ \t]+(lilypond)\b', bygroup(Keyword, Name.Function), -1
        yield from LilyPond.root

    @lexicon
    def lilypond_brace(cls):
        from .lilypond import LilyPond
        yield r'\}', Bracket.End, -1
        yield from LilyPond.root

    #---------- comments ------------------------
    @lexicon(re_flags=re.MULTILINE)
    def singleline_comment(cls):
        yield '$', None, -1
        yield from cls.comment_common()

    @lexicon
    def multiline_comment(cls):
        yield r'@end\s+ignore\b', Comment, -1
        yield from cls.comment_common()

