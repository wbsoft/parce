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
INI file format parsers.

The base parser supports escaped characters and line continuations for values.

"""

__all__ = ('Ini',)

import re

from parce import Language, lexicon, default_action, default_target
from parce.action import Comment, Data, Delimiter, Escape, Name, Operator


class Ini(Language):
    @lexicon
    def root(cls):
        yield r'\[', Delimiter.Section, cls.section
        yield r'[;#]', Comment, cls.comment
        yield r'=', Operator.Assignment, cls.value
        yield default_target, cls.key

    @lexicon
    def section(cls):
        """Parse text between [ ... ]."""
        yield r'\]', Delimiter.Section, -1
        yield default_action, Name.Namespace.Section

    @lexicon
    def key(cls):
        """Yield a Name.Identifier until a '=' (if present)."""
        yield from cls.values(Name.Identifier)

    @lexicon
    def value(cls):
        """Yield a Value until line end (or continuation line)."""
        yield from cls.values(Data)

    @classmethod
    def values(cls, action):
        """Yield name or value contents and give it the specified action."""
        yield r"""\\(?:[\n\\'"0abtrn;#=:]|x[0-9a-fA-F]{4})""", Escape
        yield r"[^\[\\\n;=#:]+", action
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        """Yield a Comment til the end of the line."""
        yield r'$', Comment, -1
        yield from cls.comment_common()


