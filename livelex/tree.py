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
Tree structure of tokens.

This module is highly experimental and tries to establish a tree structure
for tokens, so that is is easy to locate a certain token and reparse a document
from there, and that it is also easy to know when to stop parsing, because the
lexicon stack is the same and the old tokens are still valid.

This module is still completely in flux, don't depend on it right now.

"""


import bisect
import collections


from . import lex
from .action import Action


class NodeMixin:
    __slots__ = ()

    """Methods that are shared by Token and Context."""
    def root(self):
        """Return the root node."""
        root = self
        for root in self.ancestors():
            pass
        return root

    def is_root(self):
        """Return True if this Node has no parent node."""
        return self.parent is None

    def remove_from_parent(self):
        """Remove the context from the parent context and set parent to None."""
        parent = self.parent
        if parent:
            parent.remove(self)
            self.parent = None

    def ancestors(self):
        """Climb the tree up over the parents."""
        node = self.parent
        while node:
            yield node
            node = node.parent

    def common_ancestor(self, other):
        """Return the common ancestor with the Context or Token."""
        ancestors = [self]
        ancestors.extend(self.ancestors())
        if other in ancestors:
            return other
        for n in other.ancestors():
            if n in ancestors:
                return n

    def left_sibling(self):
        """Return the left sibling of this context, if any.

        Does not decend in child nodes or ascend upto the parent.
        Fails if called on the root context.

        """
        i = self.parent.index(self)
        if i:
            return self.parent[i-1]

    def right_sibling(self):
        """Return the left sibling of this context, if any.

        Does not decend in child nodes or ascend upto the parent.
        Fails if called on the root context.

        """
        i = self.parent.index(self)
        if i < len(self.parent) - 1:
            return self.parent[i+1]




class Token(str, NodeMixin):
    __slots__ = "parent", "pos", "text", "action"

    group = None

    def __new__(cls, parent, pos, text, action):
        return str.__new__(cls, text)

    def __init__(self, parent, pos, text, action):
        self.parent = parent
        self.pos = pos
        self.action = action

    def tokens(self):
        """Yield self."""
        yield self

    tokens_bw = tokens

    def forward(self):
        """Yield all Tokens in forward direction.

        Descends into child Contexts, and ascends into parent Contexts.

        """
        context = self
        while context.parent:
            i = context.parent.index(context)
            for n in context.parent[i:]:
                yield from n.tokens()
            context = context.parent

    def backward(self):
        """Yield all Tokens in backward direction.

        Descends into child Contexts, and ascends into parent Contexts.

        """
        context = self
        while context.parent:
            i = context.parent.index(context)
            if i:
                for n in context.parent[i-1::-1]:
                    yield from n.tokens_bw()
            context = context.parent


class GroupToken(Token):
    __slots__ = "group"


class Context(list, NodeMixin):
    __slots__ = "lexicon", "parent"

    def __new__(cls, lexicon, parent):
        return list.__new__(cls)

    def __init__(self, lexicon, parent):
        self.lexicon = lexicon
        self.parent = parent

    def __repr__(self):
        return format(self.lexicon) + super().__repr__()

    def tokens(self):
        """Yield all Tokens, descending into nested Contexts."""
        for n in self:
            yield from n.tokens()

    def tokens_bw(self):
        """Yield all Tokens, descending into nested Contexts, in backward direction."""
        for n in self[::-1]:
            yield from n.tokens_bw()

    def first_token(self):
        """Return our first Token."""
        try:
            n = self[0]
            while isinstance(n, Context):
                n = n[0]
            return n
        except IndexError:
            pass

    def last_token(self):
        """Return our last token."""
        try:
            n = self[-1]
            while isinstance(n, Context):
                n = n[-1]
            return n
        except IndexError:
            pass

    def find_token(self, pos):
        """Return the Token (closest) at position from context."""
        positions = []
        for n in self:
            if isinstance(n, Context):
                n = n.last_token()
            positions.append(n.pos + len(n.text))
        i = bisect.bisect_left(positions, pos)
        if i < len(positions):
            if isinstance(self[i], Context):
                return self[i].find_token(pos)
            return self[i]
        return self.last_token()


class TreeBuilder:
    """Build a tree directly from parsing the text.

    You can either call tree() to build a tree structure from the text,
    or call tokens() to get the tokens immediately.

    """

    def tree(self, root_lexicon, text, pos=0):
        """Return a root Context with all parsed Tokens in nested context lists."""
        root = Context(root_lexicon, None)
        context, pos = self.build(root, text, pos)
        self.unwind(context)
        return root

    def tokens(self, root_lexicon, text, pos=0):
        """Yield all the Tokens from the text.

        The tree is also built, but tokens are yielded immediately.

        """
        current = Context(root_lexicon, None)
        while True:
            for pos, tokens, target in self.parse_context(current, text, pos):
                current.extend(tokens)
                yield from tokens
                if target:
                    current = self.update_context(current, target)
                    break # continue in new context
            else:
                break

    def build(self, context, text, pos=0):
        """Start parsing text in the specified context.

        Return a two-tuple(context, pos) describing where the parsing ends.

        """
        current = context
        while True:
            for pos, tokens, target in self.parse_context(current, text, pos):
                current.extend(tokens)
                if target:
                    current = self.update_context(current, target)
                    break # continue in new context
            else:
                break
        return current, pos

    def parse_context(self, context, text, pos=0):
        """Yield Token instances as long as we are in the current context."""
        for pos, txt, match, action, *target in context.lexicon.parse(text, pos):
            tokens = tuple(self.filter_actions(action, pos, txt, match))
            end = pos + len(txt)
            if txt and tokens:
                if len(tokens) == 1:
                    tokens = Token(context, *tokens[0]),
                else:
                    tokens = tuple(GroupToken(context, *t) for t in tokens)
                    for t in tokens:
                        t.group = tokens
            else:
                tokens = ()
            yield end, tokens, target

    def update_context(self, context, target):
        """Move to another context depending on target."""
        for t in target:
            if isinstance(t, int):
                for pop in range(t, 0):
                    if context.parent:
                        if not context:
                            context.parent.remove(context)
                        context = context.parent
                    else:
                        break
                for push in range(0, t):
                    context = Context(context.lexicon, context)
                    context.parent.append(context)
            else:
                context = Context(t, context)
                context.parent.append(context)
        return context

    def filter_actions(self, action, pos, txt, match):
        """Handle filtering via Action instances."""
        if isinstance(action, Action):
            yield from action.filter_actions(self, pos, txt, match)
        else:
            yield pos, txt, action

    def unwind(self, context):
        """Recursively remove the context from its parent if empty."""
        while context.parent:
            if not context:
                context.parent.remove(context)
            context = context.parent


class Document:
    """Encapsulates a full tokenized text string.

    Everytime the text is modified, only the modified part is retokenized. If
    that changes the lexicon in which the last part (after the modified part)
    starts, that part is also retokenized, until the state (the list of active
    lexicons) matches the state of existing tokens.

    """
    def __init__(self, text="", root_lexicon=None):
        self._text = text
        self._root_lexicon = root_lexicon
        if text and root_lexicon:
            self.retokenize_full()

    def get_text(self):
        """Return all text."""
        return self._text

    def set_text(self, text):
        """Replace all text."""
        self._text = text
        self.retokenize_full()

    def get_root_lexicon(self):
        """Return the currently set root lexicon."""
        return self._root_lexicon

    def set_root_lexicon(self, root_lexicon):
        """Sets the root lexicon to use to tokenize the text."""
        self._root_lexicon = root_lexicon
        self.retokenize_full()

    def retokenize_full(self):
        root = self.get_root_lexicon()
        if root and self._text:
            self.tree = TreeBuilder().tree(root, self._text)
        else:
            self.tree = None

    def modify(self, start, end, text):
        """Modify the text: document[start:end] = text."""
        text = self._text[:start] + text + self._text[end:]

        # TODO: build the state while finding the token
        # start pos:
        token = find(self.tree, start-1)
        # TODO: check if left sibling of token has target None/i.e. originates
        # from one match
        if token:
            startstate = []
            context = token
            while context.parent:
                context = context.parent
                startstate.append(context.lexicon)
            startstate.reverse()
            startpos = token.pos
        else:
            startstate = [self._root_lexicon]
            startpos = 0

        ## we can start lexing at pos, with state

