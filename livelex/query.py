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


import sys


class Query:
    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        return self.gen()

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

    @property
    def children(self):
        """All direct children of the current nodes."""
        def gen():
            for n in self:
                if n.is_context:
                    yield from n
        return Query(gen)

    @property
    def all(self):
        """All descendants, contexts and their nodes."""
        def gen():
            def innergen(node):
                for n in node:
                    yield n
                    if n.is_context:
                        yield from innergen(n)
            return innergen(self)
        return Query(gen)

    @property
    def parent(self):
        def gen():
            for n in self:
                if n.parent:
                    yield n.parent
        return Query(gen)

    @property
    def uniq(self):
        """Remove double occurrences. Can happen when you use the parent."""
        seen = set()
        def gen():
            for n in self:
                i = id(n)
                if i not in seen:
                    seen.add(i)
                    yield n
        return Query(gen)

    @property
    def next(self):
        """Return the next token, if any."""
        def gen():
            for n in self:
                n = n.right_sibling()
                if n:
                    if n.is_context:
                        yield n.first_token()
                    else:
                        yield n
        return Query(gen)

    @property
    def prev(self):
        """Return the previous token, if any."""
        def gen():
            for n in self:
                n = n.left_sibling()
                if n:
                    if n.is_context:
                        yield n.last_token()
                    else:
                        yield n
        return Query(gen)

    @property
    def right(self):
        """Return the right sibling, if any."""
        def gen():
            for n in self:
                n = n.right_sibling()
                if n:
                    yield n
        return Query(gen)

    @property
    def left(self):
        """Return the left sibling, if any."""
        def gen():
            for n in self:
                n = n.left_sibling()
                if n:
                    yield n
        return Query(gen)

    # selectors
    def __call__(self, text, match=True):
        """('text') matches if token has that text, or not if match is False."""
        if not match:
            def gen():
                for t in _tokens(self):
                    if t.is_token and t.text != text:
                        yield t
        else:
            def gen():
                for t in _tokens(self):
                    if t.is_token and t.text == text:
                        yield t
        return Query(gen)

    def __getitem__(self, key):
        """normal slicing, and you can test for one or more actions."""
        if isinstance(key, int):
            def gen():
                for n in self:
                    if n.is_context and key < len(n):
                        yield n[key]
        elif isinstance(key, slice):
            def gen():
                for n in self:
                    if n.is_context:
                        yield from n[key]
        elif isinstance(key, tuple):
            def gen():
                for t in self:
                    if t.is_token and t.action in key:
                        yield t
        else:
            def gen():
                for t in self:
                    if t.is_token and t.action is key:
                        yield t
        return Query(gen)

    @property
    def tokens(self):
        """Get only the tokens."""
        def gen():
            for n in self:
                if n.is_token:
                    yield n
        return Query(gen)

    @property
    def contexts(self):
        """Get only the contexts."""
        def gen():
            for n in self:
                if n.is_context:
                    yield n
        return Query(gen)

    def lex(self, *lexicons):
        """Yield those contexts that have one of the specified lexicons."""
        def gen():
            for n in self:
                if n.is_context and n.lexicon in lexicons:
                    yield n
        return Query(gen)

    def range(self, start=0, end=None):
        """Yield a restricted set, tokens and/or contexts must fall in start→end"""
        if end is None:
            end = sys.maxsize
        def gen():
            it = iter(self)
            for n in it:
                if n.pos < start:
                    continue
                for n in it:
                    if n.end > end:
                        return
                    yield n
        return Query(gen)

