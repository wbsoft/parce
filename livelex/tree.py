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

"""


import bisect
import collections


class Leaf:
    __slots__ = "parent", "pos", "text", "action", "target"

    def __init__(self, parent, token):
        self.parent = parent
        self.pos = token.pos
        self.text = token.text
        self.action = token.action
        self.target = token.target

    def __repr__(self):
        return repr(self.text)


class Node(list):
    __slots__ = "lexicon", "parent"

    def __new__(cls, lexicon, parent):
        return list.__new__(cls)

    def __init__(self, lexicon, parent):
        self.lexicon = lexicon
        self.parent = parent

    def __repr__(self):
        return format(self.lexicon) + super().__repr__()




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


def firstleaf(node):
    """Return the first token (Leaf) in node."""
    while node and isinstance(node, Node):
        node = node[0]
    return node


def lastleaf(node):
    """Return the last token (Leaf) in node."""
    while node and isinstance(node, Node):
        node = node[-1]
    return node


def find(node, pos):
    """Return the leaf closest at position from node."""
    positions = []
    for n in node:
        if isinstance(n, Node):
            n = lastleaf(n)
        positions.append(n.pos + len(n.text))
    i = bisect.bisect_left(positions, pos)
    if i < len(positions):
        if isinstance(node[i], Node):
            return find(node[i], pos)
        return node[i]
    return lastleaf(node)


def state(leaf):
    """Reconstruct a state (list of lexicons) from the Leaf.

    The leaf should not have a target of False, find the first right
    sibling that has a non-False target first.

    """
    state = []
    node = leaf
    while node.parent:
        node = node.parent
        state.append(node.lexicon)
    state.reverse()
    if leaf.target:
        if leaf.target.pop:
            del state[leaf.target.pop:]
        state.extend(leaf.target.push)
    return state



