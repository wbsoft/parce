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


import itertools
import reprlib
import weakref

from parce import util
from parce import query
from parce.lexicon import Lexicon


DUMP_STYLES = {
    "ascii":   (" | ", "   ", " |-", " `-"),
    "round":   (" │ ", "   ", " ├╴", " ╰╴"),
    "square":  (" │ ", "   ", " ├╴", " └╴"),
    "double":  (" ║ ", "   ", " ╠═", " ╚═"),
    "thick":   (" ┃ ", "   ", " ┣╸", " ┗╸"),
    "flat":    ("│", " ", "├", "╰"),
}

DUMP_STYLE_DEFAULT = "round"


class Node:
    """Methods that are shared by Token and Context."""
    __slots__ = ('__weakref__',)

    is_token = False
    is_context = False

    @property
    def parent(self):
        """The parent Context (or None; uses a weak reference)."""
        return self._parent()

    @parent.setter
    def parent(self, parent):
        """Set the parent (to a Context or None)."""
        self._parent = weakref.ref(parent) if parent is not None else lambda: None

    @parent.deleter
    def parent(self):
        """Set the parent to None."""
        self._parent = lambda: None

    def dump(self, file=None, style=None, depth=0):
        """Display a graphical representation of the node and its contents.

        The file object defaults to stdout, and the style to "round". You can
        choose any style that's in the ``DUMP_STYLES`` dictionary.

        """
        i = 2
        d = DUMP_STYLES[style or DUMP_STYLE_DEFAULT]
        prefix = []
        node = self
        for _ in range(depth):
            prefix.append(d[i + int(node.is_last())])
            node = node.parent
            i = 0
        print("".join(reversed(prefix)) + repr(self), file=file)
        if self.is_context:
            for n in self:
                n.dump(file, style, depth + 1)

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

    def is_ancestor_of(self, node):
        """Return True if this Node is an ancestor of the other Node."""
        for n in node.ancestors():
            if n is self:
                return True
        return False

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
        ancestors = []
        if self.is_context:
            ancestors.append(self)
        ancestors.extend(self.ancestors())
        if other.is_context and other in ancestors:
            return other
        for n in other.ancestors():
            if n in ancestors:
                return n

    def depth(self):
        """Return the number of ancestors."""
        return sum(1 for n in self.ancestors())

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
            yield from util.tokens(parent[index+1:])

    def backward(self, upto=None):
        """Yield all Tokens in backward direction.

        Descends into child Contexts, and ascends into parent Contexts.
        If upto is given, does not ascend above that context.

        """
        for parent, index in self.ancestors_with_index(upto):
            if index:
                yield from util.tokens_bw(parent[index-1::-1])

    @property
    def query(self):
        """Query this node in different ways; see the :mod:`~parce.query` module."""
        def gen():
            yield self
        return query.Query(gen)

    def delete(self):
        """Remove this node from its parent.

        If the parent would become empty, it is removed too.
        Returns the first non-empty ancestor.

        """
        for parent, index in self.ancestors_with_index():
            del parent[index]
            if len(parent):
                return parent


class Token(Node):
    """A Token instance represents a lexed piece of text.

    A token has the following attributes:

    `parent`:
        the Context node to which the token was added
    `pos`:
        the position of the token in the original text
    `end`:
        the end position of the token in the original text
    `text`:
        the text of the token
    `action`:
        the action specified by the lexicon rule that created the token

    When a pattern rule in a lexicon matches the text, a Token is created. When
    that rule would create more than one Token from a single regular expression
    match, _GroupToken objects are created instead, carrying the index of the
    token in the group in the `group` attribute. The `group` attribute is
    readonly None for normal tokens.

    GroupTokens are thus always adjacent in the same context. If you want to
    retokenize text starting at some position, be sure you are at the start of
    a grouped token, e.g.::

        t = ctx.find_token(45)
        if t.group:
            for t in t.left_siblings():
                if not t.group:
                    break
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
    token's text in another string::

        s = "blabla {}".format(token)

    A token always has a parent, and that parent is always a Context instance.

    """

    __slots__ = "_parent", "pos", "text", "action"

    is_token = True
    group = None

    def __init__(self, parent, pos, text, action):
        self.parent = parent
        self.pos = pos
        self.text = text
        self.action = action

    def copy(self, parent=None):
        """Return a copy of the Token, but with the specified parent."""
        return type(self)(parent, self.pos, self.text, self.action)

    def equals(self, other):
        """Return True if the other Token has the same ``text`` and ``action``
        attributes and the same context ancestry (see also
        :meth:`state_matches`).

        Note that the ``pos`` attribute is not compared.

        """
        return (self.text == other.text
                and self.action == other.action
                and self.state_matches(other))

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

    def __repr__(self):
        text = reprlib.repr(self.text)
        return "<Token {} at {}:{} ({})>".format(text, self.pos, self.end, self.action)

    def __hash__(self):
        return Node.__hash__(self)

    def __eq__(self, other):
        if isinstance(other, str):
            return other == self.text
        return other is self

    def __ne__(self, other):
        if isinstance(other, str):
            return other != self.text
        return other is not self

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

    def forward_until_including(self, other):
        """Yield all tokens starting with us and upto and including the other."""
        context, start_trail, end_trail = self.common_ancestor_with_trail(other)
        if context:
            for context, slice_ in context.slices(start_trail, end_trail):
                yield from util.tokens(context[slice_])

    def common_ancestor_with_trail(self, other):
        """Return a three-tuple(context, trail_self, trail_other).

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
        if other.pos > self.pos:
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
        if node.group is not None:
            node = get_group_end(node)
        while node.parent:
            r = node.right_sibling()
            if r:
                if r.is_context:
                    return r
                return
            node = node.parent


class _GroupToken(Token):
    """A Token class that allows setting the `group` attribute."""
    __slots__ = "group",

    def __init__(self, group, parent, pos, text, action):
        self.group = group
        super().__init__(parent, pos, text, action)

    def copy(self, parent=None):
        """Return a copy of the Token, but with the specified parent."""
        return type(self)(self.group, parent, self.pos, self.text, self.action)


class Context(list, Node):
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

    You can quickly find tokens in a context, based on text::

        if "bla" in context:
            # etc

    Or child contexts, based on lexicon::

        if MyLanguage.lexicon in context:
            # etc

    And if you want to know which token is on a certain position in the text,
    use e.g.::

        context.find_token(45)

    which, using a bisection algorithm, quickly returns the token, which
    might be in any sub-context of the current context.

    """
    __slots__ = "lexicon", "_parent"

    is_context = True

    def __new__(cls, lexicon, parent):
        return list.__new__(cls)

    def __init__(self, lexicon, parent):
        self.lexicon = lexicon
        self.parent = parent

    def __repr__(self):
        pos, end = self.pos, self.end
        if pos == end:
            pos = end = "?" # both are 0 in this case: empty Context
        name = self.lexicon and repr(self.lexicon)
        children = "child" if len(self) == 1 else "children"
        return "<Context {} at {}-{} ({} {})>".format(
            name, pos, end, len(self), children)

    def __hash__(self):
        return Node.__hash__(self)

    def __eq__(self, other):
        if isinstance(other, Lexicon):
            return other.equals(self.lexicon)
        return other is self

    def __ne__(self, other):
        if isinstance(other, Lexicon):
            return not other.equals(self.lexicon)
        return other is not self

    def copy(self, parent=None):
        """Return a copy of the context, but with the specified parent."""
        # a non-recursive implementation due to Python's recursion limits
        copy = copy_root = type(self)(self.lexicon, parent)
        stack = []
        i = 0
        n = self
        while True:
            z = len(n)
            while i < z:
                m = n[i]
                if m.is_context:
                    copy.append(type(m)(m.lexicon, copy))
                    copy = copy[-1]
                    stack.append(i)
                    i = 0
                    n = m
                    break
                elif m.group is not None:
                    for g, j in enumerate(range(i + 1, z), m.group + 1):
                        if n[j].is_context or n[j].group is None or n[j].group < g:
                            copy.extend(node.copy(copy) for node in n[i:j])
                            i = j
                            break
                    else:
                        copy.append(m.copy(copy))
                        i += 1
                else:
                    copy.append(m.copy(copy))
                    i += 1
            else:
                if stack:
                    copy = copy.parent
                    n = n.parent
                    i = stack.pop() + 1
                else:
                    break
        return copy_root

    @property
    def pos(self):
        """Return the position or our first token. Returns 0 if empty."""
        try:
            node = self[0]
            while node.is_context:
                node = node[0]
            return node.pos
        except IndexError:
            return 0

    @property
    def end(self):
        """Return the end position or our last token. Returns 0 if empty."""
        try:
            node = self[-1]
            while node.is_context:
                node = node[-1]
            return node.end
        except IndexError:
            return 0

    def height(self):
        """Return the height of the tree (the longest distance to a descendant)."""
        if not self:
            return 0
        stack = []
        height = 0
        i = 0
        n = self
        while True:
            for i in range(i, len(n)):
                m = n[i]
                if m.is_context:
                    stack.append(i)
                    height = max(height, len(stack))
                    i = 0
                    n = m
                    break
            else:
                if stack:
                    n = n.parent
                    i = stack.pop() + 1
                else:
                    return height + 1

    def tokens(self):
        """Yield all Tokens, descending into nested Contexts."""
        stack = []
        i = 0
        n = self
        while True:
            for i in range(i, len(n)):
                m = n[i]
                if m.is_token:
                    yield m
                else:
                    stack.append(i)
                    i = 0
                    n = m
                    break
            else:
                if stack:
                    n = n.parent
                    i = stack.pop() + 1
                else:
                    break

    def tokens_bw(self):
        """Yield all Tokens, descending into nested Contexts, in backward direction."""
        stack = []
        n = self
        i = len(n)
        while True:
            for i in range(i - 1, -1, -1):
                m = n[i]
                if m.is_token:
                    yield m
                else:
                    stack.append(i)
                    n = m
                    i = len(n)
                    break
            else:
                if stack:
                    n = n.parent
                    i = stack.pop()
                else:
                    break

    def first_token(self):
        """Return our first Token."""
        try:
            node = self[0]
            while node.is_context:
                node = node[0]
            return node
        except IndexError:
            pass

    def last_token(self):
        """Return our last token."""
        try:
            node = self[-1]
            while node.is_context:
                node = node[-1]
            return node
        except IndexError:
            pass

    def find(self, pos):
        """Return the index of our child at pos."""
        i = 0
        hi = len(self)
        while i < hi:
            mid = (i + hi) // 2
            n = self[mid]
            if n.pos >= pos:
                hi = mid
            elif n.end <= pos:
                i = mid + 1
            else:
                hi = mid
        return min(i, len(self) - 1)

    def find_token(self, pos):
        """Return the Token at or to the right of position."""
        n = self[self.find(pos)]
        while n.is_context:
            n = n[n.find(pos)]
        return n

    def find_token_with_trail(self, pos):
        """Return the Token at or to the right of position, and the trail of indices."""
        i = self.find(pos)
        n = self[i]
        trail = [i]
        while n.is_context:
            i = n.find(pos)
            n = n[i]
            trail.append(i)
        return n, trail

    def find_left(self, pos):
        """Return the index of our child at or to the left of pos."""
        i = 0
        hi = len(self)
        while i < hi:
            mid = (i + hi) // 2
            n = self[mid]
            if n.pos < pos:
                i = mid + 1
            else:
                hi = mid
        return max(0, i - 1)

    def find_token_left(self, pos):
        """Return the Token at or to the left of position."""
        n = self[self.find_left(pos)]
        while n.is_context:
            n = n[n.find_left(pos)]
        return n

    def find_token_left_with_trail(self, pos):
        """Return the Token at or to the left of position, and the trail of indices."""
        i = self.find_left(pos)
        n = self[i]
        trail = [i]
        while n.is_context:
            i = n.find_left(pos)
            n = n[i]
            trail.append(i)
        return n, trail

    def find_token_after(self, pos):
        """Return the first token completely right from pos.

        Returns None if there is no token right from pos.

        """
        node = self
        while True:
            i = 0
            hi = l = len(node)
            while i < hi:
                mid = (i + hi) // 2
                n = node[mid]
                if n.is_context:
                    n = n.last_token()
                if n.pos < pos:
                    i = mid + 1
                else:
                    hi = mid
            if i >= l:
                return
            node = node[i]
            if node.is_token:
                return node

    def find_token_before(self, pos):
        """Return the last token completely left from pos.

        Returns None if there is no token left from pos.

        """
        node = self
        while True:
            i = 0
            hi = len(node)
            while i < hi:
                mid = (i + hi) // 2
                n = node[mid]
                if n.is_context:
                    n = n.first_token()
                if pos < n.end:
                    hi = mid
                else:
                    i = mid + 1
            if i == 0:
                return
            node = node[i-1]
            if node.is_token:
                return node

    def tokens_range(self, start=0, end=None):
        """Yield all tokens (that completely fill this text range if specified).

        The first and last tokens may overlap with the start and end positions.

        """
        for context, slice_ in self.context_slices(start, end):
            yield from util.tokens(context[slice_])

    def context_slices(self, start=0, end=None):
        """Yield (context, slice) tuples to yield tokens from.

        Yield the tokens using the context[slice] notation. The first and
        last tokens that would be yielded from the iterables may overlap with
        the start and end positions.

        """
        context, start_trail, end_trail = self.context_trails(start, end)
        if context:
            yield from context.slices(start_trail, end_trail)

    def context_trails(self, start=0, end=None):
        """Return a three-tuple(context, start_trail, end_trail).

        This can be used to denote a range of the tree structure in slices. The
        returned context is the common ancestor of the tokens found at start
        and end (or the current node if start or end fall outside the range of
        the node). The trails are (possibly empty) lists of indices pointing to
        the start and end token, if any.

        """
        if not self:
            return None, None, None  # empty
        context = self
        if end is not None and end < self.end:
            if end <= start:
                return None, None, None
            end_trail = self.find_token_left_with_trail(end)[1]
        else:
            end_trail = []
        if start > 0:
            start_trail = self.find_token_with_trail(start)[1]
            if end_trail:
                # find the youngest common ancestor
                for n, (i, j) in enumerate(zip(start_trail, end_trail)):
                    if i != j or context[i].is_token:
                        break
                    context = context[i]
                if n:
                    del start_trail[:n]
                    del end_trail[:n]
        else:
            start_trail = []
        return context, start_trail, end_trail

    def slices(self, start_trail, end_trail, target_factory=None):
        """Yield from the current context (context, slice) tuples.

        ``start_trail`` and ``end_trail`` both are lists of indices that
        point to descendant tokens of this context. The yielded slices
        include these tokens.

        If you specify a ``target_factory``, it should be a TargetFactory
        object, and it will be updated along with the yielded slices.

        """
        if start_trail:
            start = start_trail[0]
            if len(start_trail) > 1:
                ancestors = []
                n = self[start]
                for i in start_trail[1:]:
                    ancestors.append((n, i))
                    n = n[i]
                yield ancestors[-1][0], slice(i, None) # include start token
                for p, i in ancestors[-2::-1]:
                    target_factory and target_factory.pop()
                    yield p, slice(i + 1, None)
                target_factory and target_factory.pop()
                start += 1
        else:
            start = 0
        if end_trail:
            end = end_trail[0]
            if len(end_trail) == 1:
                yield self, slice(start, end + 1)    # include end token
            else:
                yield self, slice(start, end)
                n = self[end]
                for end in end_trail[1:-1]:
                    target_factory and target_factory.push(n.lexicon)
                    yield n, slice(end)
                    n = n[end]
                target_factory and target_factory.push(n.lexicon)
                yield n, slice(end_trail[-1] + 1)   # include end token
        else:
            yield self, slice(start, None)

    def source(self):
        """Return the first Token, if any, when going to the left from this context.

        The returned token is the one that created us, that this context the
        target is for. If the token is member of a group, the first group member
        is returned.

        """
        prev = None
        for token in self.backward():
            if not token.group:
                return token
            if prev and token.group >= prev.group:
                return prev
            prev = token


def make_tokens(event, parent=None):
    """Factory returning a tuple of one or more Token instances for the event.

    The event is an Event namedtuple defined in the mod:`~parce.lexer` module.
    If the event contains more than one token, _GroupToken instances are
    created.

    """
    if len(event.tokens) > 1:
        return tuple(_GroupToken(n, parent, *t) for n, t in enumerate(event.tokens))
    else:
        return Token(parent, *event.tokens[0]),


def get_group(token):
    """For a token that belongs to a group, return the whole group as a list."""
    p = token.parent
    i = j = token.parent_index()
    while i and p[i].group > 0 and p[i-1].is_token and p[i-1].group is not None and p[i-1].group < p[i].group:
        i -= 1
    z = len(p)
    j += 1
    while j < z and p[j].is_token and p[j].group and p[j].group > p[j-1].group:
        j += 1
    return p[i:j]


def get_group_start(token):
    """For a token that belongs to a group, return the first token of the group."""
    p = token.parent
    i = token.parent_index()
    while i and p[i].group > 0 and p[i-1].is_token and p[i-1].group is not None and p[i-1].group < p[i].group:
        i -= 1
    return p[i]


def get_group_end(token):
    """For a token that belongs to a group, return the last token of the group."""
    p = token.parent
    j = token.parent_index() + 1
    z = len(p)
    while j < z and p[j].is_token and p[j].group and p[j].group > p[j-1].group:
        j += 1
    return p[j-1]


