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
    """Methods that are shared by Token and Context."""
    __slots__ = ()

    is_token = False
    is_context = False

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

    def ancestors(self):
        """Climb the tree up over the parents."""
        node = self.parent
        while node is not None:
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

        Does not descend in child nodes or ascend upto the parent.
        Fails if called on the root context.

        """
        # avoid expensive list.index() if not necessary
        if self.parent[0] is not self:
            i = self.parent.index(self)
            return self.parent[i-1]

    def right_sibling(self):
        """Return the right sibling of this context, if any.

        Does not descend in child nodes or ascend upto the parent.
        Fails if called on the root context.

        """
        if self.parent[-1] is not self:
            i = self.parent.index(self)
            return self.parent[i+1]

    def left_siblings(self):
        """Yield the left siblings of this context in reverse order, if any.

        Does not descend in child nodes or ascend upto the parent.
        Fails if called on the root context.

        """
        if self.parent[0] is not self:
            i = self.parent.index(self)
            yield from self.parent[i-1::-1]

    def right_siblings(self):
        """Yield the right siblings of this context, if any.

        Does not descend in child nodes or ascend upto the parent.
        Fails if called on the root context.

        """
        if self.parent[-1] is not self:
            i = self.parent.index(self)
            yield from self.parent[i+1:]


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
    expression match, GroupToken objects are created instead, carrying the
    tuple of all instances in the `group` attribute. The `group` attribute is
    readonly None for normal tokens.

    GroupTokens are thus always adjacent in the same context. If you want to
    retokenize text starting at some position, be sure you are at the start of
    a grouped token, e.g.::

        t = ctx.find_token(45)
        if t.group:
            t = t.group[0]
        pos = t.pos

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

    def __repr__(self):
        return "<Token {} at {} ({})>".format(repr(self.text), self.pos, self.action)

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

    def tokens(self):
        """Yield self."""
        yield self

    tokens_bw = tokens

    def forward(self):
        """Yield all Tokens in forward direction.

        Descends into child Contexts, and ascends into parent Contexts.

        """
        node = self
        while node.parent:
            for n in node.right_siblings():
                yield from n.tokens()
            node = node.parent

    def backward(self):
        """Yield all Tokens in backward direction.

        Descends into child Contexts, and ascends into parent Contexts.

        """
        node = self
        while node.parent:
            for n in node.left_siblings():
                yield from n.tokens_bw()
            node = node.parent

    def forward_including(self):
        """Yield all tokens in forward direction, including self."""
        yield self
        yield from self.forward()

    def backward_including(self):
        """Yield all tokens in backward direction, including self."""
        yield self
        yield from self.backward()

    def cut_right(self):
        """Remove this token and all tokens to the right from the tree."""
        node = self
        while node.parent:
            i = node.parent.index(node)
            del node.parent[i+1:]
            node = node.parent
        del self.parent[-1] # including ourselves

    def split_right(self):
        """Split off a new tree, starting with this token."""
        parent = self.parent
        node = self
        firstchild = self
        while node.parent:
            context = node.parent
            copy = Context(context.lexicon, None)
            copy.append(firstchild)
            s = slice(context.index(node) + 1, None)
            for n in context[s]:
                n.parent = copy
            copy.extend(context[s])
            del context[s]
            firstchild.parent = copy
            firstchild = copy
            node = context
        del parent[-1]
        return copy

    def state_matches(self, other):
        """Return True if the other Token has the same lexicons in the ancestors."""
        if other is self:
            return True
        for c1, c2 in zip(self.ancestors(), other.ancestors()):
            if c1.lexicon != c2.lexicon:
                return False
        return c1.parent is None and c2.parent is None


class GroupToken(Token):
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

    def __repr__(self):
        first, last = self.first_token(), self.last_token()
        if first and last:
            pos, end = first.pos, last.end
        else:
            pos = end = "?"
        return "<Context {} at {}-{} ({} children)>".format(
            self.lexicon.name(), pos, end, len(self))

    def dump(self, depth=0):
        """Prints a nice graphical representation, for debugging purposes."""
        super().dump(depth)
        for n in self:
            n.dump(depth + 1)

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
            while n.is_context:
                n = n[0]
            return n
        except IndexError:
            pass

    def last_token(self):
        """Return our last token."""
        try:
            n = self[-1]
            while n.is_context:
                n = n[-1]
            return n
        except IndexError:
            pass

    def find_token(self, pos):
        """Return the Token (closest) at position from context."""
        positions = []
        for n in self:
            if n.is_context:
                n = n.last_token()
            positions.append(n.end)
        i = bisect.bisect_left(positions, pos+1)
        if i < len(positions):
            if self[i].is_context:
                return self[i].find_token(pos)
            return self[i]
        return self.last_token()


class TreeBuilder:
    """Build a tree directly from parsing the text."""

    def tree(self, root_lexicon, text):
        """Return a root Context with all parsed Tokens in nested context lists."""
        root = Context(root_lexicon, None)
        context, pos = self.build(root, text)
        self.unwind(context)
        return root

    def build(self, context, text):
        """Start parsing text in the specified context.

        Return a two-tuple(context, pos) describing where the parsing ends.

        """
        pos = 0
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

    def parse_context(self, context, text, pos):
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
                            del context.parent[-1]
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
                del context.parent[-1]
            context = context.parent


class Document:
    """Encapsulates a full tokenized text string.

    Everytime the text is modified, only the modified part is retokenized. If
    that changes the lexicon in which the last part (after the modified part)
    starts, that part is also retokenized, until the state (the list of active
    lexicons) matches the state of existing tokens.

    """
    def __init__(self, root_lexicon=None, text=""):
        self._text = text
        self._root_lexicon = root_lexicon
        self._modified_range = None
        if root_lexicon:
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
        if root:
            self.tree = TreeBuilder().tree(root, self._text)
            self._modified_range = True
        else:
            self.tree = None
            self._modified_range = None

    def tokens(self, start=0, end=None):
        """Yield all tokens from start to end if given."""
        t = self.tree.find_token(start) if start else None
        gen = t.forward_including() if t else self.tree.tokens()
        if end is None or end >= len(self._text):
            yield from gen
        else:
            for t in gen:
                if t.pos >= end:
                    break
                yield t

    def modified_tokens(self):
        """Yield all the tokens that were changed in the last update."""
        if self._modified_range is True:
            return self.tree.tokens()
        elif self._modified_range is not None:
            start, end = self._modified_range
            return self.tokens(start, end)

    def modify(self, start, end, text):
        """Modify the text: document[start:end] = text."""
        # manage end, and record if there is text after the modified part (tail)
        if end is None or end >= len(self._text):
            end = len(self._text)
            tail = False
        else:
            tail = True
        # optimize for some cases, detect whether the text actually changes
        if (start > end or (start == end and not text) or
            (start + len(text) == end and self._text[start:end] == text)):
            self._modified_range = None
            return
        elif start == 0 and not tail:
            self.retokenize_full()
            return
        # record the position change for tail tokens that can be reused
        offset = len(text) - end + start
        # modify the stored text string so we can start parsing
        text = self._text = self._text[:start] + text + self._text[end:]
        # find the last token before the modified part, we will start parsing
        # before that token. If there are no tokens, we just start at 0.
        start_token = self.tree.find_token(start - 1)
        if start > 0 and start_token:
            if start_token.group:
                start_token = start_token.group[0]
            start = min(start, start_token.pos)
            context = start_token.parent
        else:
            start = 0
            context = self.tree

        # If there remains text after the modified part, make a list of the
        # (old) positions of the tokens
        if start_token and tail:
            # find the first token after the modified part
            end_token = self.tree.find_token(end)
            if end_token.pos < end:
                for end_token in end_token.forward():
                    if end_token.pos >= end:
                        break
            end = end_token.pos
            # make a subtree structure starting with this end_token
            tail = end_token.split_right()
            # store the old positions of the tokens
            tail_tokens = []
            for t in tail.tokens():
                if not t.group or (t.group and t is t.group[0]):
                    # only pick the first of grouped tokens
                    tail_tokens.append(t)
            tail_positions = [t.pos for t in tail_tokens]
            tail = bool(tail_tokens)
        else:
            tail = False

        # remove the start token and all tokens to the right
        if start > 0 and start_token:
            if start_token is not end_token:
                start_token.cut_right()
        else:
            context.clear()

        # start parsing
        pos = start
        b = TreeBuilder()
        done = False
        while not done:
            for pos, tokens, target in b.parse_context(context, text, pos):
                if tail and tokens:
                    oldpos = tokens[0].pos - offset
                    if oldpos >= end:
                        index = bisect.bisect_left(tail_positions, oldpos)
                        if index >= len(tail_positions):
                            tail = False
                        elif (tail_positions[index] == oldpos
                                and tokens[-1].state_matches(tail_tokens[index])):
                            # we can attach the tail here.
                            # first adjust the positions of all old tokens
                            if offset:
                                for t in tail_tokens[index:]:
                                    t.pos += offset
                            # add the old tokens to the current context
                            tail_token = tail_node = tail_tokens[index]
                            context.append(tail_token)
                            c = context
                            while tail_node.parent:
                                for n in tail_node.right_siblings():
                                    c.append(n)
                                    n.parent = c
                                tail_node = tail_node.parent
                                c = c.parent
                            tail_token.parent = context
                            end = tail_token.pos
                            done = True
                            break
                        elif index > 10:  # prevent deleting too often
                            del tail_positions[:index]
                            del tail_tokens[:index]
                context.extend(tokens)
                if target:
                    context = b.update_context(context, target)
                    break # continue with new context
            else:
                end = pos
                break
        b.unwind(context)
        self._modified_range = start, end


