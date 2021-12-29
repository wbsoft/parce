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

A tree consists of Context and Token objects. (Both inherit from the base
class Node, which defines the shared methods and properties.)

A :class:`Context` is a list containing Tokens and other Contexts. A Context is
created when a lexicon becomes active. A Context knows its parent Context and
its lexicon.

A :class:`Token` represents one parsed piece of text. A Token is created when a
rule in the lexicon matches. A Token knows its parent Context, its position in
the text and the action that was specified in the rule.

A Context is always non-empty, except for the root Context, which represents
the root lexicon and can be empty if the document did not generate a single
token.

The tree structure is easy to navigate, no special objects or iterators are
necessary for that. To find a token at a certain position in a context, use
:meth:`Context.find_token` and its relatives. From every node you can iterate
:meth:`~Node.forward` and :meth:`~Node.backward`. Use the methods like
:meth:`~Node.left_siblings` and :meth:`~Node.right_siblings` to traverse the
current context.

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

    @property
    def pwd(self):
        """Show the ancestry, for debugging purposes."""
        nodes = [self]
        nodes.extend(self.ancestors())
        nodes.reverse()
        d = DUMP_STYLES[DUMP_STYLE_DEFAULT]
        for n, node in enumerate(nodes):
            print(''.join((
                d[1] * max(0, n-1),
                d[3] if n else '',
                repr(node),
                " [{}]".format(nodes[n-1].index(node)) if n else '',
            )))

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
                yield from util.tokens(parent[:index], True)

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

    When a pattern rule in a lexicon matches the text, a Token is created. When
    that rule would create more than one Token from a single regular expression
    match, GroupToken objects are created instead, carrying the index of the
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

    Alternatively, you can use the `GroupToken.get_group_*` methods.

    (A GroupToken is just a normal Token otherwise, the reason a subclass was
    created is that the group attribute is unused in by far the most tokens, so
    it does not use any memory. You never need to reference the GroupToken
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

    is_token = True     #: Always True for Token

    def __init__(self, parent, pos, text, action):
        self.parent = parent    #: The Context node to which the token was added
        self.pos = pos          #: The position in the original text
        self.text = text        #: The text of this token
        self.action = action    #: The action specified by the lexicon rule that created the token

    @property
    def end(self):
        """The end position of this token in the original text."""
        return self.pos + len(self.text)

    group = None        #: Always None for Token, an integer for :class:`GroupToken`

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
            elif c1.lexicon is not c2.lexicon:
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
        r = self.range(other)
        if r:
            yield from r.tokens()

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

    def range(self, other):
        """Return a :class:`Range` from this token upto and including the other.

        Returns None if the other :class:`Token` does not belong to the same
        tree.

        """
        context, start_trail, end_trail = self.common_ancestor_with_trail(other)
        if context:
            return Range(context, start_trail, end_trail)


class GroupToken(Token):
    """A Token class that allows setting the `group` attribute.

    For normal Token instances, `group` is a class attribute that is always
    None. For Tokens that belong to a group, i.e. originated from a single
    regular expression match, the `group` attribute is the index of the token
    in the group of tokens that were created together.

    The last token in the group has a negative value, so it can be recognized
    as the last. For example, tokens of a three-group have the indices 0, 1 and
    -2.

    The methods :meth:`get_group`, :meth:`get_group_start` and
    :meth:`get_group_end` can only be reliably used when there are no tokens
    deleted from the tree, and when the tokens really have a parent.

    """
    __slots__ = "group",

    def __init__(self, group, parent, pos, text, action):
        self.group = group  #: The index of this token in a group (negated for the last token in a group)
        super().__init__(parent, pos, text, action)

    def copy(self, parent=None):
        """Return a copy of the Token, but with the specified parent."""
        return type(self)(self.group, parent, self.pos, self.text, self.action)

    @classmethod
    def make_group(cls, parent, lexemes):
        """Create a tuple of GroupTokens for the lexemes."""
        group = tuple(cls(n, parent, *t) for n, t in enumerate(lexemes))
        group[-1].group *= -1
        return group

    def get_group(self):
        """Return the whole group this token belongs to as a list."""
        p = self.parent
        i = j = self.parent_index()
        z = len(p) - 1
        if self.group < 0:
            # we are at the last
            i += self.group
        else:
            i -= self.group
            j += 1
            while j < z and p[j].group > 0:
                j += 1
        return p[i:j+1]

    def get_group_start(self):
        """Return the first token of the group this token belongs to."""
        i = self.parent_index()
        if self.group < 0:
            i += self.group
        else:
            i -= self.group
        return self.parent[i]

    def get_group_end(self):
        """Return the last token of the group this token belongs to."""
        p = self.parent
        i = self.parent_index()
        z = len(p) - 1
        if self.group >= 0:
            i += 1
            while i < z and p[i].group > 0:
                i += 1
        return p[i]


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

    is_context = True   #: Always True for Context

    def __new__(cls, lexicon, parent):
        return list.__new__(cls)

    def __init__(self, lexicon, parent):
        self.lexicon = lexicon  #: The lexicon this context was instantiated with.
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
            return self.lexicon == other
        return other is self

    def __ne__(self, other):
        if isinstance(other, Lexicon):
            return self.lexicon != other
        return other is not self

    @property
    def ls(self):
        """List the contents of this Context, for debugging purposes."""
        for i, n in enumerate(self):
            print("[{}] {}".format(i, repr(n)))

    def copy(self, parent=None):
        """Return a copy of the context, but with the specified parent."""
        # a non-recursive implementation due to Python's recursion limits
        copy = copy_root = type(self)(self.lexicon, parent)
        n = self
        i = 0
        while True:
            z = len(n)
            while i < z:
                m = n[i]
                if m.is_context:
                    copy.append(type(m)(m.lexicon, copy))
                    copy = copy[-1]
                    i = 0
                    n = m
                    break
                else:
                    copy.append(m.copy(copy))
                    i += 1
            else:
                if copy is copy_root:
                    break
                n = n.parent
                copy = copy.parent
                i = len(copy)
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

    def tokens(self, reverse=False):
        """Yield all Tokens, descending into nested Contexts.

        If ``reverse`` is set to True, yield all tokens in backward direction.

        """
        children = reversed if reverse else iter
        stack = []
        gen = children(self)
        while True:
            for n in gen:
                if n.is_token:
                    yield n
                else:
                    stack.append(gen)
                    gen = children(n)
                    break
            else:
                if stack:
                    gen = stack.pop()
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
        """Return the index of our child at (or to the right of) pos.

        Returns -1 if there is no such child.

        """
        i = 0
        hi = l = len(self)
        while i < hi:
            mid = (i + hi) // 2
            n = self[mid]
            if n.end <= pos:
                i = mid + 1
            else:
                hi = mid
        return -1 if i == l else i

    def find_context(self, pos):
        """Return the younghest Context at position (or self)."""
        node = self
        i = self.find(pos)
        if i != -1:
            n = node[i]
            while n.is_context and n.pos <= pos:
                node = n
                n = n[n.find(pos)]
        return node

    def find_token(self, pos):
        """Return the Token at or to the right of position.

        Returns None if there is no such token.

        """
        i = self.find(pos)
        if i != -1:
            n = self[i]
            while n.is_context:
                n = n[n.find(pos)]
            return n

    def find_token_with_trail(self, pos):
        """Return the Token at or to the right of position, and the trail of indices.

        The trail is the list of indices where the token was found. Returns
        (None, None) if there is no such token. Here is an example::

            >>> import parce
            >>> tree = parce.root(parce.find('css'), open('parce/themes/default.css').read())
            >>> tree.find_token_with_trail(600)
            (<Token ' Selected te...ow has focus ' at 566:607 (Comment)>, [21, 0])
            >>> tree[21][0]
            <Token ' Selected te...ow has focus ' at 566:607 (Comment)>

        """
        i = self.find(pos)
        if i != -1:
            n = self[i]
            trail = [i]
            while n.is_context:
                i = n.find(pos)
                n = n[i]
                trail.append(i)
            return n, trail
        return None, None

    def find_left(self, pos):
        """Return the index of our child at or to the left of pos.

        Returns -1 if there is no such child.

        """
        i = 0
        hi = len(self)
        while i < hi:
            mid = (i + hi) // 2
            n = self[mid]
            if n.pos < pos:
                i = mid + 1
            else:
                hi = mid
        return i - 1

    def find_token_left(self, pos):
        """Return the Token at or to the left of position.

        Returns None if there is no such token.

        """
        i = self.find_left(pos)
        if i != -1:
            n = self[i]
            while n.is_context:
                n = n[n.find_left(pos)]
            return n

    def find_token_left_with_trail(self, pos):
        """Return the Token at or to the left of position, and the trail of indices.

        Returns (None, None) if there is no such token.

        """
        i = self.find_left(pos)
        if i != -1:
            n = self[i]
            trail = [i]
            while n.is_context:
                i = n.find_left(pos)
                n = n[i]
                trail.append(i)
            return n, trail
        return None, None

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

    def range(self, start=0, end=None):
        """Return a :class:`Range`.

        The ancestor of the range is the common ancestor of the tokens found at
        start and end (or the context itself if start or end fall outside this
        context). If start is 0 and end is None, the range encompasses the full
        context.

        Returns None if this context is empty.

        """
        return Range.from_tree(self, start, end)


class Range:
    """A Range denotes a range of a tree structure.

    A range is defined by an ancestor context and possibly empty lists pointing
    to the start and end token, if specified. If both trails are not specified,
    the range encompasses the full context.

    """
    def __init__(self, ancestor, start_trail=None, end_trail=None):
        self.ancestor = ancestor                #: The specified ancestor
        self.start_trail = start_trail or []    #: The specified start trail (empty list by default)
        self.end_trail = end_trail or []        #: The specified end trail (empty list by default)

    def __repr__(self):
        return "<{} {} [{}:{}]>".format(type(self).__name__, self.ancestor.lexicon, self.pos, self.end)

    @property
    def pos(self):
        """The position of the first token in our range."""
        n = self.ancestor
        for i in self.start_trail:
            n = n[i]
        return n.pos

    @property
    def end(self):
        """The end position of the last token in our range."""
        n = self.ancestor
        for i in self.end_trail:
            n = n[i]
        return n.end

    @classmethod
    def from_tree(cls, tree, start=0, end=None):
        """Create a Range.

        The ancestor is the common ancestor of the tokens found at start and
        end (or the tree itself if start or end fall outside the range of the
        tree). If start is 0 and end is None, the range encompasses the full
        tree.

        Returns None if the tree is empty.

        """
        if not tree:
            return # empty
        context = tree
        if end is not None and end < tree.end:
            if end <= start:
                return
            end_trail = tree.find_token_left_with_trail(end)[1]
            if not end_trail:
                return
        else:
            end_trail = []
        if start > 0:
            start_trail = tree.find_token_with_trail(start)[1]
            if not start_trail:
                return
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
        return cls(context, start_trail, end_trail)

    def slices(self, target_factory=None):
        """Yield (context, slice) tuples.

        The yielded slices include the tokens at the end of start and end
        trail.

        If you specify a ``target_factory``, it should be a
        :class:`~.target.TargetFactory` object, and it will be updated along
        with the yielded slices.

        """
        if self.start_trail:
            start = self.start_trail[0]
            if len(self.start_trail) > 1:
                ancestors = []
                n = self.ancestor[start]
                for i in self.start_trail[1:]:
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
        if self.end_trail:
            end = self.end_trail[0]
            if len(self.end_trail) == 1:
                yield self.ancestor, slice(start, end + 1)    # include end token
            else:
                yield self.ancestor, slice(start, end)
                n = self.ancestor[end]
                for end in self.end_trail[1:-1]:
                    target_factory and target_factory.push(n.lexicon)
                    yield n, slice(end)
                    n = n[end]
                target_factory and target_factory.push(n.lexicon)
                yield n, slice(self.end_trail[-1] + 1)   # include end token
        else:
            yield self.ancestor, slice(start, None)

    def tokens(self):
        """Yield all tokens in this range.

        The first and last tokens may overlap with the start and end positions.

        """
        for context, slice_ in self.slices():
            yield from util.tokens(context[slice_])



def make_tokens(lexemes, parent=None):
    """Factory returning a tuple of one or more :class:`Token` instances for
    the lexemes.

    The ``lexemes`` argument is an iterable of three-tuples like the
    ``lexemes`` in an :class:`~parce.lexer.Event` namedtuple defined in the
    :mod:`~parce.lexer` module. If there is more than one lexeme,
    :class:`GroupToken` instances are created.

    The specified ``parent`` context is set as parent, if given.

    """
    if len(lexemes) > 1:
        return GroupToken.make_group(parent, lexemes)
    else:
        return Token(parent, *lexemes[0]),


