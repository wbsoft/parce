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

Finally, a TreeBuilder is used to build() a tree structure from a text, using
a root lexicon.

Using the rebuild() method, TreeBuilder is also capable of regenerating only
part of an existing tree, e.g. when part of a long text is modified through a
text editor. It is smart enough to recognize whether existing tokens before and
after the modified region can be reused or not, and it reuses tokens as much as
possible.

"""


import itertools

from livelex.action import DynamicAction
from livelex.document import AbstractDocument
from livelex.target import DynamicTarget
from livelex.lexicon import BoundLexicon
from livelex import util


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
            for n in parent[index+1:]:
                if n.is_token:
                    yield n
                else:
                    yield from n.tokens()

    def backward(self, upto=None):
        """Yield all Tokens in backward direction.

        Descends into child Contexts, and ascends into parent Contexts.
        If upto is given, does not ascend above that context.

        """
        for parent, index in self.ancestors_with_index(upto):
            if index:
                for n in parent[index-1::-1]:
                    if n.is_token:
                        yield n
                    else:
                        yield from n.tokens_bw()

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
        return copy

    def join(self, context):
        """Add ourselves and all tokens to the right to the context.

        This method assumes that the context has the same parent depth
        as our own, and only makes sense if that parents also have the same
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
        for n in self:
            if n.is_token:
                yield n
            else:
                yield from n.tokens()

    def tokens_bw(self):
        """Yield all Tokens, descending into nested Contexts, in backward direction."""
        for n in self[::-1]:
            if n.is_token:
                yield n
            else:
                yield from n.tokens_bw()

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


class TreeBuilder:
    """Build a tree directly from parsing the text.

    After calling build() or rebuild(), three instance variables are set:

        start, end:
            indicate the region the tokens were changed. After build(), start
            is always 0 and end = len(text), but after rebuild(), these values
            indicate the range that was actually re-tokenized.

        lexicons:
            the list of open lexicons (excluding the root lexicons) at the end
            of the document. This way you can see in which lexicon parsing
            ended.

    No other variables or state are kept, so if you don't need the above
    information anymore, you can throw away the TreeBuilder after use.

    """

    start = 0
    end = 0
    lexicons = ()

    def tree(self, root_lexicon, text):
        """Convenience method returning a new tree with all tokens."""
        root = Context(root_lexicon, None)
        self.build(root, text)
        return root

    def build(self, context, text):
        """Tokenize the full text, starting in the given context.

        Sets three instance variables start, end, lexicons). Start and end
        are always 0 and len(text), respectively. lexicons is a list of the
        lexicons that were not closed at the end of the text. (If the parser
        ended in the root context, the list is empty.)

        """
        pos = 0
        while True:
            for pos, tokens, target in self.parse_context(context, text, pos):
                context.extend(tokens)
                if target:
                    context = self.update_context(context, target)
                    break # continue in new context
            else:
                break
        self.unwind(context)
        self.start, self.end = 0, len(text)

    def rebuild(self, tree, text, start, removed, added):
        """Tokenize the modified part of the text again and update the tree.

        Sets, just like build(), three instance variables start, end, lexicons,
        describing the region in the thext the tokens were changed. This range
        can be larger than (start, start + added).

        The text is the new text; start is the position where characters were
        removed and others added. The removed and added arguments are integers,
        describing how many characters were removed and added.

        This method finds the place we can start parsing again, and when the
        end of the modified region is reached, automatically recognizes when
        the rest of the tokens can be reused. When old tokens at the end are
        reused, the lexicons instance variable is not reset, the existing
        value is still relevant in that case.

        """
        # manage end, and record if there is text after the modified part (tail)
        end = start + removed
        tail = start + added < len(text)

        # we may be able to use existing tokens for the start if start > 0
        head = start > 0

        # record the position change for tail tokens that maybe are reused
        offset = added - removed

        # find the last token before the modified part, we will start parsing
        # before that token. If there are no tokens, we just start at 0.
        # At least go back to just before a newline, if possible.
        if head:
            i = text.rfind('\n', 0, start)
            start_token = tree.find_token_before(i) if i > -1 else None
            if not start_token:
                start_token = tree.find_token_before(start)
                if start_token:
                    # go back some more tokens, you never know a longer match
                    # could be made. In very particular cases a longer token
                    # could be found. (That's why we tried to go back to a
                    # newline.)
                    for start_token in itertools.islice(start_token.backward(), 10):
                        pass
            if start_token:
                # don't start in the middle of a group, as they originate from
                # one single regexp match
                if start_token.group:
                    start_token = start_token.group[0]
            else:
                head = False

        # If there remains text after the modified part,
        # we try to reuse the old tokens
        if tail:
            # find the first token after the modified part
            end_token = tree.find_token_after(end)
            if not end_token:
                tail = False

        if not head and not tail:
            # nothing can be reused
            tree.clear()
            self.build(tree, text)
            return

        if head:
            # make a short list of tokens from the start_token to the place
            # we want to parse. We copy them because some might get moved to
            # the tail tree. If they were not changed, we can adjust the
            # modified region.
            start_tokens = [start_token.copy()]
            for t in start_token.forward():
                start_tokens.append(t.copy())
                if t.end > start:
                    break
            start_token_index = 0

        if tail:
            # make a subtree structure starting with this end_token
            tail_tree = end_token.split()
            tail_gen = ((t, t.pos + offset)
                for t in tail_tree.tokens()
                    if not t.group or (t.group and t is t.group[0]))
            # store the new position the first tail token would get
            for tail_token, tail_pos in tail_gen:
                break
            else:
                tail = False

        # remove the start token and all tokens to the right
        if head:
            start_parse = start_token.pos
            context = start_token.parent
            if not tail or start_token is not end_token:
                start_token.cut()
        else:
            start_parse = 0
            context = tree
            context.clear()

        # start parsing
        pos = start_parse
        done = False
        while not done:
            for pos, tokens, target in self.parse_context(context, text, pos):
                if tokens:
                    if head:
                        # move start_parse if the tokens before start didn't change
                        if (start_token_index + len(tokens) <= len(start_tokens) and
                            all(new.equals(old)
                                for old, new in zip(start_tokens[start_token_index:], tokens))):
                            start_parse = pos
                            start_token_index += len(tokens)
                        else:
                            start_parse = tokens[0].pos
                            head = False    # stop looking further
                    if tail:
                        if tokens[0].pos > tail_pos:
                            for tail_token, tail_pos in tail_gen:
                                if tail_pos >= tokens[0].pos:
                                    break
                            else:
                                tail = False
                        if (tokens[0].pos == tail_pos
                                and tokens[0].state_matches(tail_token)):
                            # we can attach the tail here.
                            if offset:
                                # adjust the pos of the old tail tokens.
                                # We don't use tail_token.forward() because
                                # it uses parent_index() which depends on sorted
                                # pos values
                                tail_token.cut_left()
                                for t in tail_tree.tokens():
                                    t.pos += offset
                            # add the old tokens to the current context
                            tail_token.join(context)
                            end_parse = tail_pos
                            done = True
                            break
                    context.extend(tokens)
                if target:
                    context = self.update_context(context, target)
                    break # continue with new context
            else:
                end_parse = pos
                self.unwind(context)
                break
        self.start, self.end = start_parse, end_parse

    def unwind(self, context):
        """Recursively remove the context from its parent if empty.

        Leaves the list of lexicons that were left open in the `lexicons`
        attribute. When parsing ended in the root context, that list is empty.

        """
        self.lexicons = []
        while context.parent:
            self.lexicons.append(context.lexicon)
            if not context:
                del context.parent[-1]
            context = context.parent

    def parse_context(self, context, text, pos):
        """Yield Token instances as long as we are in the current context."""
        for pos, txt, match, action, *target in context.lexicon.parse(text, pos):
            if txt:
                if isinstance(action, DynamicAction):
                    tokens = tuple(action.filter_actions(self, pos, txt, match))
                    if len(tokens) == 1:
                        tokens = Token(context, *tokens[0]),
                    else:
                        tokens = tuple(_GroupToken(context, *t) for t in tokens)
                        for t in tokens:
                            t.group = tokens
                else:
                    tokens = Token(context, pos, txt, action),
            else:
                tokens = ()
            if target and isinstance(target[0], DynamicTarget):
                target = target[0].target(match)
            yield pos + len(txt), tokens, target

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
        """Handle filtering via DynamicAction instances."""
        if isinstance(action, DynamicAction):
            yield from action.filter_actions(self, pos, txt, match)
        elif txt:
            yield pos, txt, action

