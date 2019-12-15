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
    root = {}
    for w in words:
        d = root
        for c in w:
            d = d.setdefault(c, {})
        d[None] = True  # end

    def concat(node):
        new = {}
        for key, node in node.items():
            if key:
                if len(node) > 1:
                    node = concat(node)
                else:
                    while len(node) == 1:
                        k, n = next(iter(node.items()))
                        if k:
                            key += k
                            node = n
                        else:
                            node[None] = True
                            break
            new[key] = node
        return new

    root = concat(root)
    
    def to_regexp(node):
        if len(node) == 1:
            for k, v in node.items():
                if k:
                    yield re.escape(k)
                    yield from to_regexp(v)
        else:
            yield '(?:'
            closeparen = ')'
            separator = ""
            for k, v in node.items():
                if k:
                    yield separator
                    separator = '|'
                    yield re.escape(k)
                    yield from to_regexp(v)
                else:
                    closeparen = ')?'
            yield closeparen

    return ''.join(to_regexp(root))

