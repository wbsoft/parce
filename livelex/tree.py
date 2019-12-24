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

class NodeMixin:
    """Methods that are shared by Leaf and Node."""
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
        """Remove the node from the parent node and set parent to None."""
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
        """Return the common ancestor with the Node or Leaf."""
        ancestors = [self]
        ancestors.extend(self.ancestors())
        if other in ancestors:
            return other
        for n in other.ancestors():
            if n in ancestors:
                return n

    def left_sibling(self):
        """Return the left sibling of this node, if any.

        Does not decend in child nodes or ascend upto the parent.
        Fails if called on the root node.

        """
        i = self.parent.index(self)
        if i:
            return self.parent[i-1]

    def right_sibling(self):
        """Return the left sibling of this node, if any.

        Does not decend in child nodes or ascend upto the parent.
        Fails if called on the root node.

        """
        i = self.parent.index(self)
        if i < len(self.parent) - 1:
            return self.parent[i+1]




class Leaf(NodeMixin):
    __slots__ = "parent", "pos", "text", "action", "target"

    def __init__(self, parent, token):
        self.parent = parent
        self.pos = token.pos
        self.text = token.text
        self.action = token.action
        self.target = token.target

    def __repr__(self):
        return repr(self.text)

    def leafs(self):
        """Yield self."""
        yield self

    leafs_bw = leafs

    def forward(self):
        """Yield all Leafs in forward direction.

        Descends into child Nodes, and ascends into parent Nodes.

        """
        node = self
        while node.parent:
            i = node.parent.index(node)
            for n in node.parent[i:]:
                yield from n.leafs()
            node = node.parent

    def backward(self):
        """Yield sibling Leafs in backward direction.

        Descends into child Nodes, and ascends into parent Nodes.

        """
        node = self
        while node.parent:
            i = node.parent.index(node)
            if i:
                for n in node.parent[i-1::-1]:
                    yield from n.leafs_bw()
            node = node.parent

    def state_before(self):
        """Reconstruct a state (list of lexicons) right before the Leaf.

        The leaf should not have a target of False, find the first right
        sibling that has a non-False target first.

        """
        state = []
        node = self
        while node.parent:
            node = node.parent
            state.append(node.lexicon)
        state.reverse()
        return state

    def update_state(self, state):
        """Modify the state such as returned by state_before() according to our target."""
        if self.target:
            if self.target.pop:
                del state[self.target.pop:]
            state.extend(self.target.push)

    def state_after(self):
        """Reconstruct a state (list of lexicons) right after this Leaf."""
        state = self.state_before()
        self.update_state(state)
        return state



class Node(list, NodeMixin):
    __slots__ = "lexicon", "parent"

    def __new__(cls, lexicon, parent):
        return list.__new__(cls)

    def __init__(self, lexicon, parent):
        self.lexicon = lexicon
        self.parent = parent

    def __repr__(self):
        return format(self.lexicon) + super().__repr__()

    def leafs(self):
        """Yield all leaf nodes, descending into nested Nodes."""
        for n in self:
            yield from n.leafs()

    def leafs_bw(self):
        """Yield all leaf nodes, descending into nested Nodes, in backward direction."""
        for n in self[::-1]:
            yield from n.leafs_bw()

    def firstleaf(self):
        """Return the first token (Leaf) in node."""
        try:
            node = self[0]
            while isinstance(node, Node):
                node = node[0]
            return node
        except IndexError:
            pass

    def lastleaf(self):
        """Return the last token (Leaf) in node."""
        try:
            node = self[-1]
            while isinstance(node, Node):
                node = node[-1]
            return node
        except IndexError:
            pass

    def find(self, pos):
        """Return the Leaf (closest) at position from node."""
        positions = []
        for n in self:
            if isinstance(n, Node):
                n = n.lastleaf()
            positions.append(n.pos + len(n.text))
        i = bisect.bisect_left(positions, pos)
        if i < len(positions):
            if isinstance(self[i], Node):
                return self[i].find(pos)
            return self[i]
        return self.lastleaf()


def tree(tokens, root_lexicon="root"):
    """Experimental function that puts the tokens in a tree structure.

    The structure consists of nested lists; the first item of each list is the
    lexicon. The other items are the tokens that were generated by rules of
    that lexicon, or child lists.

    """
    root = current = Node(root_lexicon, None)
    stack = [root]
    for t in tokens:
        if t.text:
            current.append(Leaf(current, t))
        if t.target:
            if t.target.pop:
                for i in range(-1, t.target.pop - 1, -1):
                    if stack[i]:
                        stack[i-1].append(stack[i])
                del stack[t.target.pop:]
            for lexicon in t.target.push:
                stack.append(Node(lexicon, stack[-1]))
            current = stack[-1]
    # unwind if we were not back in the root lexicon
    for i in range(len(stack) - 1, 0, -1):
        if stack[i]:
            stack[i-1].append(stack[i])
    return root



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
            self.tree = tree(lex.Lexer(root).tokens(self._text), root)
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
            node = token
            while node.parent:
                node = node.parent
                startstate.append(node.lexicon)
            startstate.reverse()
            startpos = token.pos
        else:
            startstate = [self._root_lexicon]
            startpos = 0

        ## we can start lexing at pos, with state

