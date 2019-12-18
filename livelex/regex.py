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
Helper objects to construct regular expressions.

"""


import re


class Pattern:
    """Base class for objects that build a regular expression."""
    def build(self):
        raise NotImplementedError


class Words(Pattern):
    """Creates a regular expression from a list of words."""
    def __init__(self, words, prefix="", suffix=""):
        self.words = words
        self.prefix = prefix
        self.suffix = suffix

    def build(self):
        expr = words2regexp(self.words)
        if self.prefix or self.suffix:
            return self.prefix + '(?:' + expr + ')' + self.suffix
        return expr


def words2regexp(words):
    """Convert the word list to an optimized regular expression."""
    words, suffix = common_suffix(words)
    root = make_trie(words)
    r = trie_to_regexp_tuple(root)
    if suffix:
        r += (suffix,)
    return build_regexp(r)


def trie_to_regexp_tuple(node, reverse=False):
    """Converts the trie node to a tuple of regular expression parts.

    A part is either a plain string expression or a frozenset instance.
    A frozenset instance denotes a group of alternative expressions, and
    consists of plain string expressions or other tuples. If None is also
    present in the frozenset, the expression is optional.

    """
    if reverse:
        combine = lambda r1, r2: r2 + r1
    else:
        combine = lambda r1, r2: r1 + r2

    if len(node) == 1:
        for k, n in node.items():
            if k:
                return combine((k,), trie_to_regexp_tuple(n, reverse))
            return ()
    else:
        seen = []
        keys = []
        groups = set()

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
                groups.add(None)    # means optional group, may end here

        for keys, node in zip(keys, seen):
            if len(keys) == 1:
                if not any(node):
                    groups.add(keys[0])
                else:
                    groups.add(combine((keys[0],), trie_to_regexp_tuple(node, reverse)))
            else:
                if not reverse:
                    # try to optimize the keys backwards
                    r = trie_to_regexp_tuple(make_trie(keys, True), True)
                    if r == (frozenset(keys),) and not any(node):
                        groups.update(keys)
                        continue
                elif not any(node):
                    groups.update(keys)
                    continue
                else:
                    r = (frozenset(keys),)
                groups.add(combine(r, trie_to_regexp_tuple(node, reverse)))
        return groups.pop() if len(groups) == 1 else (frozenset(groups),)


def build_regexp(r):
    """Convert a tuple to a full regular expression pattern string.

    The tuple is described in the trie_to_regexp_tuple() function doc string.

    """
    def get_items(r):
        """Yield regexp items from tuple r in tuples (item, mincount, maxcount).

        An item is either a string like "aa", or a two-tuple(exprs,
        tuples), where exprs is a set of plain strings, and tuples a set of
        tuples that were inside a frozenset. The mincount and maxcount are
        integers and describe the minimal or maximal required count of
        matches.

        """
        for item in r:
            if isinstance(item, str):
                yield item, 1, 1
            else:
                # item is a frozenset
                mincount = 1
                exprs = set()
                tuples = set()
                for k in item:
                    if isinstance(k, str):
                        exprs.add(k)
                    elif isinstance(k, tuple):
                        tuples.add(k)
                    elif k is None:
                        mincount = 0
                # just one expression and no subgroups?
                if len(exprs) == 1 and not tuples:
                    yield exprs.pop(), mincount, 1
                else:
                    item = (exprs, tuples)
                    # optimize for the case of only one subgroup
                    # remove otherwise empty parent group if possible
                    if not exprs and len(tuples) == 1:
                        # there is only one subexpression in the group
                        r = next(iter(tuples))
                        items = merge_items(r)
                        # if our group has no qualifier, just yield the subgroup
                        if mincount:
                            yield from items
                        # if we are optional, check if the qualifier of the subgroup
                        # can be altered. Possible when mincount <= 1.
                        elif len(items) == 1 and items[0][1] <= 1:
                            item, _, maxcount = items[0]
                            yield item, 0, maxcount
                        else:
                            yield item, mincount, 1
                    else:
                        yield item, mincount, 1

    def merge_items(r):
        """Read items-tuples such as yielded by get_items().

        Returns a list of the same items, merging where possible adjacent
        items that are the same. Every list entry is a three-tuple(item,
        mincount, maxcount); where an item is either a string like "aa", or
        a two-tuple(exprs, tuples).

        """
        items = []
        for item, mincount, maxcount in get_items(r):
            if items and items[-1][0] == item:
                items[-1][1] += mincount
                items[-1][2] += maxcount
            else:
                items.append([item, mincount, maxcount])
        return items

    items = merge_items(r)

    # now really construct the regexp string for each item
    enclosegroup = len(items) > 1
    result = []
    for item, mincount, maxcount in items:
        # qualifier to use
        if mincount == 1 and maxcount == 1:
            qualifier = ''
        elif mincount == 0 and maxcount == 1:
            qualifier = "?"
        elif mincount == maxcount:
            qualifier = "{{{0}}}".format(maxcount)
        else:
            qualifier = "{{{0},{1}}}".format(mincount or '', maxcount or '')
        # make the rx
        if isinstance(item, str):
            rx = re.escape(item)
        else:
            exprs, tuples = item
            # separate single characters from longer strings
            chars, strings = set(), set()
            for k in exprs:
                (chars if len(k) == 1 else strings).add(k)
            group = []
            if chars:
                if len(chars) == 1:
                    group.append(re.escape(next(iter(chars))))
                else:
                    group.append('[' + make_charclass(chars) + ']')
            if strings:
                group.extend(map(re.escape, sorted(strings)))
            if tuples:
                group.extend(map(build_regexp, tuples))
            if chars and not strings and not tuples:
                rx = group[0]
            else:
                rx = '|'.join(group)
                if enclosegroup or qualifier:
                    rx = '(?:' + rx + ')'
        result.append(rx + qualifier)
    return ''.join(result)


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

