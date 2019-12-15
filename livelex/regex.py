# -*- coding: utf-8 -*-
#
# This file is part of the livelex Python module.
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
Helper objects to construct regular expressions.

"""


import re


class RegexBuilder:
    """Base class for objects that build a regular expression."""
    def pattern(self):
        raise NotImplementedError
    

class Words(RegexBuilder):
    """Creates a regular expression from a list of words."""
    def __init__(self, words, prefix="", suffix=""):
        self.words = words
        self.prefix = prefix
        self.suffix = suffix
    
    def build(self):
        return self.prefix + words2regexp(self.words) + self.suffix


def words2regexp(words):
    """Convert the word list to an optimized regular expression."""
    
    # make a trie structure
    root = {}
    for w in words:
        d = root
        for c in w:
            d = d.setdefault(c, {})
        d[None] = True  # end

    # concatenate characters that have no branches
    def concat(node):
        for key, node in node.items():
            if key:
                while len(node) == 1:
                    k, n = next(iter(node.items()))
                    if k:
                        key += k
                        node = n
                    else:
                        node[None] = True
                        break
                else:
                    node = dict(concat(node))
            yield key, node
    root = dict(concat(root))

    def to_regexp(node):
        if len(node) == 1:
            for k, n in node.items():
                if k:
                    yield re.escape(k)
                    yield from to_regexp(n)
        else:
            groups = []
            optional = False
            for k, n in node.items():
                if k:
                    groups.append((k, n))
                else:
                    optional = True
            if len(groups) == 1 and len(groups[0][0]) == 1:
                yield re.escape(groups[0][0])
            else:
                yield '(?:'
                yield '|'.join(re.escape(k) + ''.join(to_regexp(n)) for k, n in groups)
                yield ')'
            if optional:
                yield '?'

    return ''.join(to_regexp(root))

