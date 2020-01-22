# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
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
This module defines the tree structure a text is parsed into.

A tree consists of Context and Token objects.

A Context is a list containing Tokens and other Contexts. A Context is created
when a lexicon becomes active. A Context knows its parent Context and its
lexicon.

A Token represents one parsed piece of text. A Token is created when a rule in
the lexicon matches. A Token knows its parent Context, its position in the text
and the action that was specified in the rule.

The root Context is always one, and it represents the root lexicon. A Context
is always non-empty, except for the root Context, which is empty if the
document did not generate a single token.

The tree structure is very easy to navigate, no special objects or iterators
are necessary for that.

To find a token at a certain position in a context, use find_token() and its
relatives. From every token you can iterate forward() and backward(). Use the
methods like left_siblings() and right_siblings() to traverse the current
context.

See also the documentation for Token and Context.

"""


import sys
import itertools

from parce import util
from parce import query


class NodeMixin:
    """Methods that are shared by Token and Context."""
    __slots__ = ()

    is_token = False
    is_context = False

    def parent_index(self):
        """Return our index in the parent.

        This is recommended above using parent.index(self), because this method
        finds our index using a binary search on position, while the latter
        is a linear search, which is certainly slower with a large number of
        children.

        """
        p = self.parent
        pos = self.pos
        lo = 0
        hi = len(p)
        while lo < hi:
            mid = (lo + hi) // 2
            n = p[mid]
            if n.pos < pos:
                lo = mid + 1
            elif n is self:
                return mid
            else:
                hi = mid
        return lo

    def dump(self, depth=0):
        """Prints a nice graphical representation, for debugging purposes."""
        prefix = (" ╰╴" if self.is_last() else " ├╴") if depth else ""
        node = self
        for i in range(depth - 1):
            node = node.parent
            prefix = ("   " if node.is_last() else " │ ") + prefix
        print(prefix + repr(self))

    def root(self):
        """Return the root node."""
        root = self
        for root in self.ancestors():
            pass
        return root

    def is_root(self):
        """Return True if this Node has no parent node."""
        return self.parent is None

    def is_last(self):
        """Return True if this Node is the last child of its parent.

        Fails if called on the root element.

        """
        return self.parent[-1] is self

    def is_first(self):
        """Return True if this Node is the first child of its parent.

        Fails if called on the root element.

        """
        return self.parent[0] is self

    def ancestors(self, upto=None):
        """Climb the tree up over the parents.

        If upto is given and it is one of the ancestors, stop after yielding
        that ancestor. Otherwise iteration stops at the root node.

        """
        node = self.parent
        if upto and upto.parent is not None:
            p = upto.parent
            while node is not None and node is not p:
                yield node
                node = node.parent
        else:
            while node is not None:
                yield node
                node = node.parent

    def ancestors_with_index(self, upto=None):
        """Yield the ancestors(upto), and the index of each node in the parent."""
        n = self
        for p in self.ancestors(upto):
            yield p, n.parent_index()
            n = p

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
        """Return the left sibling of this node, if any.

        Does not descend in child nodes or ascend upto the parent.
        Fails if called on the root node.

        """
        if self.parent[0] is not self:
            i = self.parent_index()
            return self.parent[i-1]

    def right_sibling(self):
        """Return the right sibling of this node, if any.

        Does not descend in child nodes or ascend upto the parent.
        Fails if called on the root node.

        """
        if self.parent[-1] is not self:
            i = self.parent_index()
            return self.parent[i+1]

    def left_siblings(self):
        """Yield the left siblings of this node in reverse order, if any.

        Does not descend in child nodes or ascend upto the parent.
        Fails if called on the root node.

        """
        if self.parent[0] is not self:
            i = self.parent_index()
            yield from self.parent[i-1::-1]

    def right_siblings(self):
        """Yield the right siblings of this node, if any.

        Does not descend in child nodes or ascend upto the parent.
        Fails if called on the root node.

        """
        if self.parent[-1] is not self:
            i = self.parent_index()
            yield from self.parent[i+1:]

    def next_token(self):
        """Return the following Token, if any."""
        for t in self.forward():
            return t

    def previous_token(self):
        """Return the preceding Token, if any."""
        for t in self.backward():
            return t

    def forward(self, upto=None):
        """Yield all Tokens in forward direction.

        Descends into child Contexts, and ascends into parent Contexts.
        If upto is given, does not ascend above that context.

        """
        for parent, index in self.ancestors_with_index(upto):
            yield from tokens(parent[index+1:])

    def backward(self, upto=None):
        """Yield all Tokens in backward direction.

        Descends into child Contexts, and ascends into parent Contexts.
        If upto is given, does not ascend above that context.

        """
        for parent, index in self.ancestors_with_index(upto):
            if index:
                yield from tokens_bw(parent[index-1::-1])


class Token(NodeMixin):
    """A Token instance represents a lexed piece of text.

    A token has the following attributes:

    `parent`: the Context node to which the token was added
    `pos`:    the position of the token in the original text
    `end`:    the end position of the token in the original text
    `text`:   the text of the token
    `action`: the action specified by the lexicon rule that created the token

    When a pattern rule in a lexicon matches the text, a Token is created.
    When that rule would create more than one Token from a single regular
    expression match, _GroupToken objects are created instead, carrying the
    tuple of all instances in the `group` attribute. The `group` attribute is
    readonly None for normal tokens.

    GroupTokens are thus always adjacent in the same context. If you want to
    retokenize text starting at some position, be sure you are at the start of
    a grouped token, e.g.::

        t = ctx.find_token(45)
        if t.group:
            t = t.group[0]
        pos = t.pos

    (A _GroupToken is just a normal Token otherwise, the reason a subclass was
    created is that the group attribute is unused in by far the most tokens, so
    it does not use any memory. You never need to reference the _GroupToken
    class; just test the group attribute if you want to know if a token belongs
    to a group that originated from a single match.)

    When iterating over the children of a Context (which may be Context or
    Token instances), you can use the `is_token` attribute to determine whether
    the node child is a token, which is easier than to call `isinstance(t,
    Token)` each time.

    From a token, you can iterate `forward()` or `backward()` to find adjacent
    tokens. If you only want to stay in the current context, use the various
    sibling methods, such as `right_sibling()`.

    By traversing the `ancestors()` of a token or context, you can find which
    lexicons created the tokens.

    You can compare a Token instance with a string. Instead of::

        if token.text == "bla":
            do_something()

    you can do::

        if token == "bla":
            do_something()

    You can call `len()` on a token, which returns the length of the token's
    text attribute, and you can use the string format method to embed the
    token's text in another string:

        s = "blabla {}".format(token)

    A token always has a parent, and that parent is always a Context instance.

    """

    __slots__ = "parent", "pos", "text", "action"

    is_token = True
    group = None

    def __init__(self, parent, pos, text, action):
        self.parent = parent
        self.pos = pos
        self.text = text
        self.action = action

    def copy(self):
        """Return a shallow copy.

        The parent still points to the parent of the original.

        """
        return type(self)(self.parent, self.pos, self.text, self.action)

    def equals(self, other):
        """Return True if other has same pos, text and action and state."""
        return (self.pos == other.pos
                and self.text == other.text
                and self.action == other.action
                and self.state_matches(other))

    def __repr__(self):
        text = util.abbreviate_repr(self.text[:31])
        return "<Token {} at {}:{} ({})>".format(text, self.pos, self.end, self.action)

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.text
        return super().__eq__(other)

    def __ne__(self, other):
        if isinstance(other, str):
            return other != self.text
        return super().__ne__(other)

    def __format__(self, formatstr):
        return self.text.__format__(formatstr)

    def __len__(self):
        return len(self.text)

    @property
    def end(self):
        return self.pos + len(self.text)

    def forward_including(self, upto=None):
        """Yield all tokens in forward direction, including self."""
        yield self
        yield from self.forward(upto)

    def backward_including(self, upto=None):
        """Yield all tokens in backward direction, including self."""
        yield self
        yield from self.backward(upto)

    def cut(self):
        """Remove this token and all tokens to the right from the tree."""
        for parent, index in self.ancestors_with_index():
            del parent[index+1:]
        del self.parent[-1] # including ourselves

    def cut_left(self):
        """Remove all tokens to the left from the tree."""
        for parent, index in self.ancestors_with_index():
            del parent[:index]

    def split(self):
        """Split off a new tree, starting with this token.

        The new tree has the same ancestor structure as the current. This token
        and all tokens to the right are moved to the new tree and removed from
        the current one. The new tree's root element is returned.

        """
        parent = self.parent
        node = firstchild = self
        for p, i in self.ancestors_with_index():
            copy = Context(p.lexicon, None)
            copy.append(firstchild)
            if node is not p[-1]:
                s = slice(i + 1, None)
                for n in p[s]:
                    n.parent = copy
                copy.extend(p[s])
                del p[s]
            firstchild.parent = copy
            firstchild = copy
            node = p
        del parent[-1]
        # remove empty context in the old tree
        while not parent and parent.parent:
            parent = parent.parent
            del parent[-1]
        return copy

    def join(self, context):
        """Add ourselves and all tokens to the right to the context.

        This method assumes that the context has the same parent depth
        as our own, and only makes sense if those parents also have the same
        lexicon, i.e. the our state matches the target context (and that
        the pos attribute of the tokens is adjusted).

        The nodes are not removed from their former parents, just the parent
        attribute is changed.

        """
        context.append(self)
        node = self
        c = context
        for p, i in self.ancestors_with_index():
            if node is not p[-1]:
                siblings = p[i+1:]
                for n in siblings:
                    n.parent = c
                c.extend(siblings)
            node = p
            c = c.parent
        self.parent = context

    def state_matches(self, other):
        """Return True if the other Token has the same lexicons in the ancestors."""
        if other is self:
            return True
        for c1, c2 in zip(self.ancestors(), other.ancestors()):
            if c1 is c2:
                return True
            elif c1.lexicon != c2.lexicon:
                return False
        return c1.parent is None and c2.parent is None

    def common_ancestor_with_trail(self, other):
        """Return (context, trail_self, trail_other).

        The context is the common ancestor such as returned by common_ancestor,
        if any. trail_self is a tuple of indices from the common ancestor upto
        self, and trail_other is a tuple of indices from the same ancestor upto
        the other Token.

        If there is no common ancestor, all three are None. But normally,
        all nodes share the root context, so that will normally be the upmost
        common ancestor.

        """
        if other is self:
            i = self.parent_index()
            return self.parent, (i,), (i,)
        s_ancestors, s_indices = zip(*self.ancestors_with_index())
        o_indices = []
        for n, i in other.ancestors_with_index():
            o_indices.append(i)
            try:
                s_i = s_ancestors.index(n)
            except ValueError:
                continue
            return n, s_indices[s_i::-1], o_indices[::-1]
        return None, None, None

    def target(self):
        """Return the first context directly to the right of this Token.

        The context should be the right sibling of the token, or of any of its
        ancestors. If the token is part of a group, the context is found
        immediately next to the last member of the group. The found context may
        also be a child of the grand-parents of this token, in case the target
        popped contexts first.

        In all cases, the returned context is the one started by the target
        in the lexicon rule that created this token.

        """
        node = self
        if node.group:
            node = node.group[-1]
        while node.parent:
            r = node.right_sibling()
            if r:
                if r.is_context:
                    return r
                return
            node = node.parent


class _GroupToken(Token):
    """A Token class that allows setting the `group` attribute."""
    __slots__ = "group"


class Context(list, NodeMixin):
    """A Context represents a list of tokens and contexts.

    The lexicon that created the tokens is in the `lexicon` attribute.

    If a pattern rule jumps to another lexicon, a sub-Context is created and
    tokens are added there. If that lexicon pops back to the current one, new
    tokens can appear after the sub-context. (So the token that caused the jump
    to the sub-context normally preceeds the context it created.)

    A context has a `parent` attribute, which can point to an enclosing
    context. The root context has `parent` None.

    When iterating over the children of a Context (which may be Context or
    Token instances), you can use the `is_context` attribute to determine
    whether the node child is a context, which is easier than to call
    `isinstance(node, Context)` each time.

    You can quickly find tokens in a context::

        if "bla" in context:
            # etc

    And if you want to know which token is on a certain position in the text,
    use e.g.::

        context.find_token(45)

    which, using a bisection algorithm, quickly returns the token, which
    might be in any sub-context of the current context.

    """
    __slots__ = "lexicon", "parent"

    is_context = True

    def __new__(cls, lexicon, parent):
        return list.__new__(cls)

    def __init__(self, lexicon, parent):
        self.lexicon = lexicon
        self.parent = parent

    def copy(self):
        """Return a copy of this Context node, with copies of all the children.

        The parent of the copy is None.

        """
        copy = type(self)(self.lexicon, None)
        for n in self:
            c = n.copy()
            c.parent = copy
            copy.append(c)
        return copy

    def __repr__(self):
        pos, end = self.pos, self.end
        if pos is None:
            pos = end = "?"
        name = self.lexicon and self.lexicon.name()
        return "<Context {} at {}-{} ({} children)>".format(
            name, pos, end, len(self))

    def dump(self, depth=0):
        """Prints a nice graphical representation, for debugging purposes."""
        super().dump(depth)
        for n in self:
            n.dump(depth + 1)

    @property
    def pos(self):
        """Return the position or our first token. Returns None if empty."""
        for t in self.tokens():
            return t.pos

    @property
    def end(self):
        """Return the end position or our last token. Returns None if empty."""
        for t in self.tokens_bw():
            return t.end

    def tokens(self):
        """Yield all Tokens, descending into nested Contexts."""
        yield from tokens(self)

    def tokens_bw(self):
        """Yield all Tokens, descending into nested Contexts, in backward direction."""
        yield from tokens_bw(self[::-1])

    def first_token(self):
        """Return our first Token."""
        for t in self.tokens():
            return t

    def last_token(self):
        """Return our last token."""
        for t in self.tokens_bw():
            return t

    def find_token(self, pos):
        """Return the Token at or to the right of position."""
        i = 0
        hi = len(self)
        while i < hi:
            mid = (i + hi) // 2
            n = self[mid]
            if n.is_context:
                n = n.last_token()
            if n.end <= pos:
                i = mid + 1
            else:
                hi = mid
        if i < len(self):
            if self[i].is_context:
                return self[i].find_token(pos)
            return self[i]
        return self.last_token()

    def find_token_left(self, pos):
        """Return the Token at or to the left of position."""
        i = 0
        hi = len(self)
        while i < hi:
            mid = (i + hi) // 2
            n = self[mid]
            if n.is_context:
                n = n.first_token()
            if n.pos < pos:
                i = mid + 1
            else:
                hi = mid
        if i > 0:
            i -= 1
            if self[i].is_context:
                return self[i].find_token_left(pos)
            return self[i]
        return self.first_token()

    def find_token_after(self, pos):
        """Return the first token completely right from pos.

        Returns None if there is no token right from pos.

        """
        i = 0
        hi = len(self)
        while i < hi:
            mid = (i + hi) // 2
            n = self[mid]
            if n.is_context:
                n = n.last_token()
            if n.pos < pos:
                i = mid + 1
            else:
                hi = mid
        if i < len(self):
            if self[i].is_context:
                return self[i].find_token_after(pos)
            return self[i]

    def find_token_before(self, pos):
        """Return the last token completely left from pos.

        Returns None if there is no token left from pos.

        """
        i = 0
        hi = len(self)
        while i < hi:
            mid = (i + hi) // 2
            n = self[mid]
            if n.is_context:
                n = n.first_token()
            if pos < n.end:
                hi = mid
            else:
                i = mid + 1
        if i > 0:
            i -= 1
            if self[i].is_context:
                return self[i].find_token_before(pos)
            return self[i]

    def tokens_range(self, start, end=None):
        """Yield all tokens in this text range. Use from the root Context."""
        if not self:
            return  # empty
        start_token = self.find_token(start) if start else self.first_token()
        if end is None or end >= self.end:
            yield from start_token.forward_including()
            return
        if start_token.end >= end:
            yield start_token
            return
        end_token = self.find_token_left(end)
        if end_token is start_token:
            yield start_token
            return
        if end_token.pos > start_token.pos:
            # all this is just to avoid a pos comparison on *each* token
            # which is faster for large ranges of tokens
            context, trail_start, trail_end = start_token.common_ancestor_with_trail(end_token)
            # yield start token and then climb down the tree
            yield start_token
            p = start_token.parent
            for i in trail_start[:0:-1]:
                yield from tokens(p[i+1:])
                p = p.parent
            # yield intermediate tokens
            yield from tokens(context[trail_start[0]+1:trail_end[0]])
            # then climb up the tree for the end token
            node = context[trail_end[0]]
            for i in trail_end[1:]:
                yield from tokens(node[:i])
                node = node[i]
            yield node  # == end_token

    def source(self):
        """Return the first Token, if any, when going to the left from this context.

        The returned token is the one that created us, that this context the
        target is for. If the token is member of a group, the first group member
        is returned.

        """
        node = self
        for parent in node.ancestors():
            n = node.left_sibling()
            if n:
                while n:
                    if n.is_token:
                        if n.group:
                            n = n.group[0]
                        return n
                    n = n[-1]
                return
            node = parent

    @property
    def query(self):
        """Query this node in different ways; see the query module."""
        def gen():
            yield self
        return query.Query(gen)


def tokens(nodes):
    """Helper to yield tokens from the iterable of nodes."""
    for n in nodes:
        if n.is_token:
            yield n
        else:
            yield from n.tokens()


def tokens_bw(nodes):
    """Helper to yield tokens from the iterable in backward direction.

    Make sure nodes is already in backward direction.

    """
    for n in nodes:
        if n.is_token:
            yield n
        else:
            yield from n.tokens_bw()


