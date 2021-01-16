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
Helper functions and classes for the :mod:`~parce.treebuilder` module.

"""


import collections
import itertools

from parce.lexer import Event, Lexer
from parce.tree import Context
from parce.target import TargetFactory


#: encapsulates the return values of :meth:`TreeBuilder.build_new_tree`
BuildResult = collections.namedtuple("BuildResult", "tree start end offset lexicons")

#: encapsulates the return values of :meth:`TreeBuilder.replace_tree`
ReplaceResult = collections.namedtuple("ReplaceResult", "start end lexicons")


class Changes:
    """Store changes that have to be made to a tree.

    This object is used by
    :meth:`~parce.treebuilder.TreeBuilder.get_changes()`. Calling
    :meth:`add()` merges new changes with the existing changes.

    """
    __slots__ = "text", "root_lexicon", "start", "removed", "added"

    def __init__(self):
        self.text = ""
        self.root_lexicon = False   # meaning no change is requested
        self.start = -1          # meaning no text is altered
        self.removed = 0
        self.added = 0

    def __repr__(self):
        changes = []
        if self.root_lexicon != False:
            changes.append("root_lexicon: {}".format(self.root_lexicon))
        if self.start != -1:
            changes.append("text: {} -{} +{}".format(self.start, self.removed, self.added))
        if not changes:
            changes.append("(no changes)")
        return "<Changes {}>".format(', '.join(changes))

    def add(self, text, root_lexicon=False, start=0, removed=None, added=None):
        """Merge new change with existing changes.

        If added and removed are not given, all text after start is
        considered to be replaced.

        """
        if root_lexicon != False:
            self.root_lexicon = root_lexicon
        if removed is None:
            removed = len(self.text) - start
        if added is None:
            added = len(text) - start
        self.text = text
        if self.start == -1:
            # there were no previous changes
            self.start = start
            self.removed = removed
            self.added = added
            return
        # determine the offset for removed and added
        if start + removed < self.start:
            offset = self.start - start - removed
        elif start > self.start + self.added:
            offset = start - self.start - self.added
        else:
            offset = 0
        # determine which part of removed falls inside existing changes
        start = max(start, self.start)
        end = min(start + removed, self.start + self.added)
        offset -= max(0, end - start)
        # set the new values
        self.start = min(self.start, start)
        self.removed += removed + offset
        self.added += added + offset

    def has_changes(self):
        """Return True when there are actually changes."""
        return self.start != -1 or self.root_lexicon != False

    def new_position(self, pos):
        """Return how the current changes would affect an older start."""
        if pos < self.start:
            return pos
        elif pos < self.start + self.removed:
            return self.start + self.added
        return pos - self.removed + self.added


def get_prepared_lexer(tree, text, start):
    """Get a prepared lexer reading from text, positioned at (or before) start.

    Returns the three-tuple (lexer, events, tokens). The events stream is
    returned seperately because the last Event can be pushed back, so it is
    yielded again. The tokens are the last tokens group that remained the same.

    Returns None when no position to start can be found, just start from the
    beginning in this case.

    """
    while start:
        last_token = start_token = find_token_before(tree, start)
        while last_token and last_token.group is not None:
            group = last_token.get_group()
            if group[-1].end <= start:
                break
            last_token = group[0].previous_token()
        if not last_token:
            return
        # go back at most 10 tokens, to the beginning of a group; if we
        # are at the first token just return 0.
        for start_token in itertools.islice(last_token.backward(), 10):
            pass
        while True:
            if start_token.group:
                start_token = start_token.get_group_start()
            # go back further if this is the first token in a context whose
            # lexicon has consume == True
            if start_token.is_first() and start_token.parent.lexicon.consume:
                prev_token = start_token.previous_token()
                if prev_token:
                    start_token = prev_token
                    continue
            break
        start = start_token.pos if start_token.previous_token() else 0
        lexer = get_lexer(start_token) if start else Lexer([tree.lexicon])
        events = lexer.events(text, start)
        # compare the new events with the old tokens; at least one
        # should be the same; if not, go back further if possible
        old_events = events_with_tokens(start_token, last_token)
        prev = None
        for (old, tokens), new in zip(old_events, events):
            if old != new:
                if prev:
                    return lexer, itertools.chain((new,), events), prev
                break
            prev = tokens
        else:
            if prev:
                return lexer, events, prev


def events_with_tokens(start_token, last_token):
    r"""Yield (Event, tokens) tuples for start_token until and including last_token.

    Events are yielded together with token groups (or single tokens in a
    1-length tuple).

    This function is used by :func:`get_prepared_lexer` to compare an existing
    token structure with events originating from a lexer.

    The start_token must be the first of a group, if it is a GroupToken.
    Additionally, it should not be the first token in a context whose lexicon
    has the ``consume`` flag set. But if the start_token is the very first
    token in a tree, it does not matter if it is not in the root context, this
    case is handled gracefully.

    """
    context, start_trail, end_trail = start_token.common_ancestor_with_trail(last_token)
    if context:

        target = TargetFactory()
        get, push, pop = target.get, target.push, target.pop

        def events(nodes):
            stack = []
            i = 0
            n = nodes
            while True:
                z = len(n)
                while i < z:
                    m = n[i]
                    if m.is_context:
                        push(m.lexicon)
                        stack.append(i)
                        i = 0
                        n = m
                        break
                    else:
                        group = m,
                        if m.group is not None:
                            # find the last token in this group
                            for g, j in enumerate(range(i + 1, z), m.group + 1):
                                if n[j].is_context or n[j].group != g:
                                    break
                            else:
                                j = z
                            group = n[i:j]
                        lexemes = tuple((t.pos, t.text, t.action) for t in group)
                        yield Event(get(), lexemes), group
                        i += len(group)
                else:
                    if stack:
                        pop()
                        i = stack.pop() + 1
                        n = n.parent if stack else nodes # slice we started with
                    else:
                        break

        if start_token.is_first() and not start_token.parent.is_root() \
                and not start_token.previous_token():
            # start token is the very first token, but it is not in the root
            # context. So it is a child of a lexicon with consume, or a context
            # that was jumped to via a default target. Build a target from root.
            lexicons = [p.lexicon for p in start_token.ancestors()]
            push(*lexicons[-2::-1])  # reversed, not root

        for context, slice_ in context.slices(start_trail, end_trail, target):
            yield from events(context[slice_])


def get_lexer(token):
    """Get a Lexer initialized at the token's ancestry."""
    lexicons = [p.lexicon for p in token.ancestors()]
    lexicons.reverse()
    return Lexer(lexicons)


def new_tree(token):
    """Return an empty context (and its root) with the same ancestry as the token's."""
    c = n = context = Context(token.parent.lexicon, None)
    for p in token.parent.ancestors():
        n = Context(p.lexicon, None)
        c.parent = n
        n.append(c)
        c = n
    return context, n


def find_token_before(node, pos):
    """A version of :meth:`~parce.tree.Context.find_token_before` that can handle
    empty contexts.

    The new tree built inside :meth:`TreeBuilder.build_new_tree()
    <parce.treebuilder.TreeBuilder.build_new_tree>` can have an empty context
    at the beginning and/or the end. Returns None if there is no token left
    from pos.

    """
    while True:
        i = 0
        hi = len(node)
        while i < hi:
            mid = (i + hi) // 2
            n = node[mid]
            if n.is_context:
                n = n.first_token() or n    # if no first token, just n itself
            if pos < n.end:
                hi = mid
            else:
                i = mid + 1
        if i == 0:
            return
        node = node[i-1]
        if node.is_token:
            return node

