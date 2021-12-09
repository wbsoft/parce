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

__all__ = ('Ini', 'IniTransform')

import re

from parce import Language, lexicon, default_action, default_target
from parce.action import (
    Bracket, Comment, Data, Delimiter, Escape, Name, Operator,
)
from parce.transform import Transform


class Ini(Language):
    @lexicon
    def root(cls):
        yield r'\[', Bracket.Start, cls.section
        yield r'[;#]', Comment, cls.comment
        yield r'=', Operator.Assignment, cls.value
        yield default_target, cls.key

    @lexicon
    def section(cls):
        """Parse text between [ ... ]."""
        yield r'\]', Bracket.End, -1
        yield default_action, Name.Namespace

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
        yield r"""\\(?:[\n\\'"0abtrn;#=:]|[xX][0-9a-fA-F]{4})""", Escape
        yield r"[^\[\\\n;=#:]+", action
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        """Yield a Comment til the end of the line."""
        yield r'$', Comment, -1
        yield from cls.comment_common()


class IniTransform(Transform):
    """Transform for the Ini language definition.

    Strips whitespace around keys and values, and handles escaped characters.
    If a value is absent, None is stored.

    """
    def root(self, items):
        """Return a dict, section names are the keys.

        Toplevel keys are in the ``None`` entry.

        """
        result = {}
        d = result[None] = {}
        i, z = 0, len(items)
        while i < z:
            if items.peek(i, "section"):
                result[items[i].obj] = d = {}
            elif items.peek(i, "key", Operator.Assignment):
                key = items[i].obj
                value = None
                if items.peek(i + 2, "value"):
                    value = items[i+2].obj
                    i += 1
                d[key] = value
                i += 1
            i += 1
        # delete toplevel dict if empty
        if not result[None]:
            del result[None]
        return result

    def section(self, items):
        """Return the name of the section."""
        if items.peek(-1, Bracket.End):
            items.pop()
        return self.values(items)

    def key(self, items):
        """Return the key name."""
        return self.values(items)

    def value(self, items):
        """Return the value."""
        return self.values(items)

    def values(self, items):
        """Return a string, handling escaped characters, stripping spaces."""
        result = []
        if items:
            # de-tokenize
            items = [t.text for t in items]
            # strip whitespace, but not from escapes
            if not items[0].startswith('\\'):
                items[0] = items[0].lstrip(' \t')
            if not items[-1].startswith('\\'):
                items[-1] = items[-1].rstrip(' \t')
            # unescape
            for t in items:
                if t.startswith('\\'):
                    t = chr(int(t[2:], 16)) if t[1] in ('x', 'X') else t[1]
                result.append(t)
        return ''.join(result)

    comment = None


