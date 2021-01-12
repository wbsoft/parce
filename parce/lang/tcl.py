# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2021-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Tcl (Tool Command Language)

"""

__all__ = ('Tcl',)

import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import Comment, Delimiter, Escape, Name, String, Text
from parce.rule import bygroup, ifgroup


class Tcl(Language):
    """Tool command language."""

    @classmethod
    def values(cls):
        yield r'\[', Delimiter, cls.command
        yield r'"', String, cls.quoted
        yield r'\{', Delimiter.Bracket, cls.braced
        yield r'(\$(?:[0-9a-zA-Z_]|::+)+)(\()?', \
            bygroup(Name.Variable, Delimiter), ifgroup(2, cls.index)
        yield r'\${.*?\}', Name.Variable
        yield r'\\(?:[0-7]{1,3}|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|.)', Escape
        yield r'^\s*(#)', bygroup(Comment), cls.comment

    @lexicon(re_flags=re.MULTILINE)
    def root(cls):
        yield from cls.values()
        yield r'[^\s\\\{\[\$\']\S*', Text.Word

    @lexicon(re_flags=re.MULTILINE)
    def command(cls):
        yield r'\]', Delimiter, -1
        yield from cls.root

    @lexicon
    def quoted(cls):
        yield r'"', String, -1
        yield r'\[', Delimiter, cls.command
        yield from cls.values()
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def braced(cls):
        yield r'\}', Delimiter.Bracket, -1
        yield from cls.root

    @lexicon(re_flags=re.MULTILINE)
    def index(cls):
        """Index of a variable reference like $name(index)."""
        yield r'\)', Delimiter, -1
        yield from cls.root

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield r'$', None, -1
        yield from cls.comment_common()

