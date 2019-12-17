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
    words, suffix = common_suffix(words)
    root = make_trie(words)

    def to_regexp(node, reverse=False):
        if reverse:
            combine = lambda *strings: ''.join(strings[::-1])
        else:
            combine = lambda *strings: ''.join(strings)
        
        if len(node) == 1:
            for k, n in node.items():
                if k:
                    return combine(re.escape(k), to_regexp(n, reverse))
                return ''
        else:
            seen = []
            keys = []
            optional = ''
            
            # group the nodes if they have the same leaf node
            for k, n in node.items():
                if k:
                    try:
                        i = seen.index(n)
                    except ValueError:
                        i = len(seen)
                        seen.append(n)
                        keys.append([k])
                    else:
                        keys[i].append(k)
                else:
                    optional = '?'

            groups = []
            for keys, node in zip(keys, seen):
                # make a regexp from the keys
                if len(keys) == 1:
                    rx = re.escape(keys[0])
                else:
                    if all(len(k) == 1 for k in keys):
                        rx = '[' + make_charclass(keys) + ']'
                    elif not reverse:
                        rx = to_regexp(make_trie(keys, True), True)
                    elif not any(node):
                        groups.extend((re.escape(k), '') for k in keys)
                        continue
                    else:
                        rx = '(?:' + '|'.join(map(re.escape, keys)) + ')'
                groups.append((rx, to_regexp(node, reverse, True) if any(node) else ""))

            if not groups:
                return ''
            elif len(groups) == 1:
                rx, nrx = groups[0]
                if not nrx:
                    if rx.startswith('['):
                        return rx + optional
                    elif len(rx) == 1 or (len(rx) == 2 and rx.startswith('\\')):
                        return rx + optional
                if optional:
                    return '(?:' + combine(rx, nrx) + ')' + optional
                return combine(rx, nrx)
            rx = '|'.join(combine(rx, nrx) for rx, nrx in groups)
            return '(?:' + rx + ')' + optional

    rx = to_regexp(root)
    return ('(?:' + rx + ')' + suffix) if suffix else rx
        


def make_charclass(chars):
    """Return a string with adjacent characters grouped.
    
    eg ('a', 'b', 'c', 'd', 'f') is turned into '[a-df]'.
    Special characters are properly escaped.
    
    """
    buf = []
    for c in sorted(map(ord, chars)):
        if buf and buf[-1][1] == c - 1:
            buf[-1][1] = c
        else:
            buf.append([c, c])
    return ''.join(re.escape(chr(a)) if a == b else
                   re.escape(chr(a) + chr(b)) if a == b - 1 else
                   re.escape(chr(a)) + '-' + re.escape(chr(b))
                   for a, b in buf)


def make_trie(words, reverse=False):
    """Return a dict-based radix trie structure from a list of words.
    
    If reverse is set to True, the trie is made in backward direction,
    from the end of the words.
    
    """
    if reverse:
        chars = lambda word: word[::-1]
        add = lambda k1, k2: k2 + k1
    else:
        chars = lambda word: word
        add = lambda k1, k2: k1 + k2
    
    root = {}
    for w in words:
        d = root
        for c in chars(w):
            d = d.setdefault(c, {})
        d[None] = True  # end

    # merge characters that are the only child with their parents
    def merge(node):
        for key, node in node.items():
            if key:
                while len(node) == 1:
                    k, n = next(iter(node.items()))
                    if k:
                        key = add(key, k)
                        node = n
                    else:
                        break
                else:
                    node = dict(merge(node))
            yield key, node

    return dict(merge(root))


def common_suffix(words):
    """Return (words, suffix), where suffix is the common suffix.
    
    If there is no common suffix, words is unchanged, and suffix is an
    empty string. If there is a common suffix, that is chopped of the returned
    words.
    
    """
    suffix = ""
    d = make_trie(words, reverse=True)
    if len(d) == 1:
        suffix = d.popitem()[0]
        i = -len(suffix)
        words = [word[:i] for word in words]
    return words, suffix

