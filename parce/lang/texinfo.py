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

import re

from parce import *


class Texinfo(Language):

    @lexicon
    def root(cls):
        yield r'@[@{}. ]', Escape
        yield r'''@['",=^`~](\{[a-zA-Z]\}|[a-zA-Z]\b)''', Escape
        yield r'@c(?:omment)?\b', Comment, cls.singleline_comment
        yield r'@ignore\b', Comment, cls.multiline_comment
        yield r'@verbatim\b', Keyword.Verbatim, cls.verbatim
        yield r'(@[a-zA-Z]+)(?:(\{)(\})?)?', bygroup(
                ifgroup(2, ifgroup(3, Name.Symbol, Name.Function), Name.Command),
                Bracket.Start,
                Bracket.End), \
            ifgroup(2, ifgroup(3, (), cls.brace))

    @lexicon
    def brace(cls):
        yield r'\}', Bracket.End, -1
        yield from cls.root

    @lexicon
    def verbatim(cls):
        yield r'(@end)[ \t]+(verbatim)\b', bygroup(Keyword, Keyword.Verbatim), -1
        yield default_action, Verbatim

    #---------- comments ------------------------
    @lexicon(re_flags=re.MULTILINE)
    def singleline_comment(cls):
        yield '$', None, -1
        yield from cls.comment_common()

    @lexicon
    def multiline_comment(cls):
        yield r'@end\s+ignore\b', Comment, -1
        yield from cls.comment_common()

