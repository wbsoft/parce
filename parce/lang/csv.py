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
RFC-4180 compliant CSV format
"""

__all__ = ('Csv', 'CsvTransform')

import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.rule import bygroup
from parce.transform import Transform
from parce.util import split_list
import parce.action as a


class Csv(Language):
    """RFC-4180 compliant CSV format."""
    @lexicon
    def root(cls):
        """Split a file in records."""
        yield default_target, cls.record

    @lexicon(re_flags=re.MULTILINE)
    def record(cls):
        """Split a record in escaped (string) and non-escaped fields."""
        yield r'$\n?', skip, -1
        yield r'[^,"\n]+(?=$|,|\n)', a.Name
        yield r'[ \t]*((?:[^,"\s]+[ \t]*)+)?(")', bygroup(a.Invalid, a.String.Start), cls.string
        yield ',', a.Separator

    @lexicon(consume=True)
    def string(cls):
        """Handle a quoted string, escaping doubled quotes inside."""
        yield r'""', a.String.Escape
        yield r'(")[ \t]*([^,"\s]+)?', bygroup(a.String.End, a.Invalid), -1
        yield default_action, a.String


class CsvTransform(Transform):
    r"""Transform for comma-separated values, that creates a list of tuples.

    For example::

        >>> import parce.transform
        >>> parce.transform.transform_text(parce.find('csv'), 'a,b,,c\nd,"",e,"x,y,z"')
        [('a', 'b', None, 'c'), ('d', '', 'e', 'x,y,z')]

    """
    def _interpret(self, token):
        """Reimplement to interpret a text value differently, e.g. a number."""
        return token.text

    def root(self, items):
        """Return the list of records."""
        return [i.obj for i in items]

    def record(self, items):
        """Return the tuple of the fields of one record.

        Adjacent commas yield None, but empty quoted strings (``""``) are
        returned as empty strings.

        """
        return tuple(
            None if not l
            else self._interpret(l[0]) if l[0].is_token
            else l[0].obj
            for l in split_list(items, ','))

    def string(self, items):
        """Return a string comprising the contents of the quoted string.

        Handles doubled quotes inside, and does not add the outer quotes.

        """
        start, end = 0, len(items) - 1
        while items[start].action in (a.Invalid, a.String.Start):
            start += 1
        while end >= start and items[end].action in (a.String.End, a.Invalid):
            end -= 1
        return ''.join(
            '"' if t.action is a.String.Escape
            else t.text
            for t in items[start:end+1])

