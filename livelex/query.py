# -*- coding: utf-8 -*-
#
# This file is part of the livelex Python package.
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


"""
An experimental query module.

"""


import functools
import re
import sys


def query(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        return Query(lambda: func(self, *args, **kwargs))
    return wrapper


def pquery(func):
    return property(query(func))


class Query:
    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        return self.gen()

    # end points
    def count(self):
        """Compute the length of the iterable. Don't use this other than for debugging."""
        return sum(1 for _ in self)

    def dump(self):
        """Dump the current selection to the console."""
        for n in self:
            n.dump()

    def list(self):
        """Return the current selection as a list. Only for debugging."""
        return list(self)

    def pick(self, default=None):
        """Pick the first value, or return the default."""
        for n in self:
            return n
        return default

    # navigators
    @pquery
    def children(self):
        """All direct children of the current nodes."""
        for n in self:
            if n.is_context:
                yield from n

    @pquery
    def all(self):
        """All descendants, contexts and their nodes."""
        def innergen(node):
            for n in node:
                yield n
                if n.is_context:
                    yield from innergen(n)
        return innergen(self)

    @pquery
    def parent(self):
        for n in self:
            if n.parent:
                yield n.parent

    @pquery
    def uniq(self):
        """Remove double occurrences. Can happen when you use the parent."""
        seen = set()
        for n in self:
            i = id(n)
            if i not in seen:
                seen.add(i)
                yield n

    @pquery
    def next(self):
        """Return the next token, if any."""
        for n in self:
            n = n.right_sibling()
            if n:
                if n.is_context:
                    yield n.first_token()
                else:
                    yield n

    @pquery
    def prev(self):
        """Return the previous token, if any."""
        for n in self:
            n = n.left_sibling()
            if n:
                if n.is_context:
                    yield n.last_token()
                else:
                    yield n

    @pquery
    def right(self):
        """Return the right sibling, if any."""
        for n in self:
            n = n.right_sibling()
            if n:
                yield n

    @pquery
    def left(self):
        """Return the left sibling, if any."""
        for n in self:
            n = n.left_sibling()
            if n:
                yield n

    # selectors
    @query
    def __call__(self, text, match=True):
        """('text') matches if token has that text, or not if match is False."""
        if not match:
            for t in self:
                if t.is_token and t.text != text:
                    yield t
        else:
            for t in self:
                if t.is_token and t.text == text:
                    yield t

    @query
    def startingwith(self, text):
        for t in self:
            if t.is_token and t.text.startswith(text):
                yield t

    @query
    def not_startingwith(self, text):
        for t in self:
            if t.is_token and not t.text.startswith(text):
                yield t

    @query
    def endingwith(self, text):
        for t in self:
            if t.is_token and t.text.endswith(text):
                yield t

    @query
    def not_endingwith(self, text):
        for t in self:
            if t.is_token and not t.text.endswith(text):
                yield t

    @query
    def containing(self, text):
        """Yield tokens that contain the specified text."""
        for t in self:
            if t.is_token and text in t.text:
                yield t

    @query
    def not_containing(self, text):
        """Yield tokens that contain the specified text."""
        for t in self:
            if t.is_token and text not in t.text:
                yield t

    @query
    def __getitem__(self, key):
        """normal slicing, and you can test for one or more actions."""
        if isinstance(key, int):
            for n in self:
                if n.is_context and key < len(n):
                    yield n[key]
        elif isinstance(key, slice):
            for n in self:
                if n.is_context:
                    yield from n[key]
        elif isinstance(key, tuple):
            for t in self:
                if t.is_token and t.action in key:
                    yield t
        else:
            for t in self:
                if t.is_token and t.action is key:
                    yield t

    @pquery
    def tokens(self):
        """Get only the tokens."""
        for n in self:
            if n.is_token:
                yield n

    @pquery
    def contexts(self):
        """Get only the contexts."""
        for n in self:
            if n.is_context:
                yield n

    @query
    def action_in(self, *actions):
        """Yield those tokens whose action is or inherits from one of the given actions."""
        for t in self:
            if t.is_token and any(t.action in a for a in actions):
                yield t

    @query
    def lexicon_in(self, *lexicons):
        """Yield those contexts that have one of the specified lexicons."""
        for n in self:
            if n.is_context and n.lexicon in lexicons:
                yield n

    @query
    def range(self, start=0, end=None):
        """Yield a restricted set, tokens and/or contexts must fall in start→end"""
        if end is None:
            end = sys.maxsize
        it = iter(self)
        for n in it:
            if n.pos < start:
                continue
            for n in it:
                if n.end > end:
                    return
                yield n

    @query
    def matching(self, pattern, flags=0):
        """Yield tokens matching the regular expression (using re.search)."""
        for t in self:
            if t.is_token and re.search(pattern, t.text, flags):
                yield t

    @query
    def not_matching(self, pattern, flags=0):
        """Yield tokens matching the regular expression (using re.search)."""
        for t in self:
            if t.is_token and not re.search(pattern, t.text, flags):
                yield t


