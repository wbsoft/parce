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
            singles = []
            rest = []
            optional = False
            for k, n in node.items():
                if k:
                    if len(k) == 1 and not any(n):
                        singles.append(k)
                    else:
                        rest.append((k, n))
                else:
                    optional = True
            
            groups = []
            if singles:
                if len(singles) == 1:
                    groups.append(re.escape(singles[0]))
                else:
                    groups.append('[' + make_charclass(singles) + ']')
            if rest:
                groups.extend(re.escape(k) + ''.join(to_regexp(n)) for k, n in rest)
            if singles and not rest:
                yield groups[0]
            else:
                yield '(?:'
                yield '|'.join(groups)
                yield ')'
            if optional:
                yield '?'

    return ''.join(to_regexp(root))


def make_charclass(chars):
    """Return a string with adjacent characters grouped.
    
    eg ('a', 'b', 'c', 'd', 'f') is turned into '[a-df]'.
    Special characters are properly escaped.
    
    """
    buf = []
    for c in sorted(map(ord, chars)):
        if buf and buf[-1][1] == c-1:
            buf[-1][1] = c
        else:
            buf.append([c, c])
    return ''.join(re.escape(chr(a)) if a == b
                   else re.escape(chr(a)) + '-' + re.escape(chr(b))
                   for a, b in buf)

    
