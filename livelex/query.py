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
An experimental query module.


Using this module you can query the token tree to find tokens and contexts,
based on lexicons and/or actions and text contents. You can chain calls
in a XPath-like fashion.

This module supplements the various find_xxx methods of every Context object.
After iterating the three with this query module, you will probably still
use the other navigational possibilities of the tree structure. Also depending
on the design of the Language structure.

The basic query starts at the `query` property of a Context object, which
selects all the nodes of that Context.

Then you can narrow down the search using `tokens`, `contexts`, `('text')` or
`(lexicon)`, `has_not`, `[n]`, `[n:n]`, `[action]`, `[action, action]`,
`startingwith()`, `endingwith()`, `containing()`, `matching()`, `uniq`,
`in_action()`,  `in_lexicon()`, and the corresponding `not_` counterparts, and
`__getitem__` and `is_not()`.

You can navigate using `children`, `all`, `next`, `prev`, `right`, `left`, and
`parent`.


Examples:

Find all tokens that are the first child of a Context with bla lexicon:

    root.query.all(MyLang.bla)[0]


Find (in Xml) all attributes with name 'name' that are in a <bla> tag:

    root.query.all[Name.Tag]("bla").next('name')


Find all tags containing "hi" in their text nodes:

    root.query.all[Name.Tag].next.next[Text].containing('hi')


Find all comments that have TODO in it:

    root.query.all[Comment].containing('TODO')


A query is a generator, you can iterate over the results. For debugging
purposes, there are also the list(), pick(), count() and dump() methods.

    for attrs in q.all[Name.Tag]('origin').right:
        for atr in attrs.query[Name.Attribute]:
            print(atr)


Summary of the query methods:

For debugging:

    count()
        Just prints the number of results in the result set

    dump()
        dump()s the full result nodes to stdout

    list()
        aggregate the results in a list

    pick()
        just pick the first result, or a default if no results


Selecting nodes:

    all
        select all descandant nodes, depth-first, in order. First it yields the
        context, then its children.

    children
        select all the direct children of the current nodes

    parent
        select the parent of all current nodes. This can yield double
        occurrences of nodes in the list. (Use uniq to fix that.)

    next, prev
        select the next or previous token, if any

    right, left
        select the right or left sibling, if any

    (lexicon), __call__(lexicon)
        select the Contexts with that lexicon

    has_not(lexicon)
        select the Contexts that have a different lexicon

    ("text"), __call__("text")
        select the Tokens with exact that text

    has_not("text")
        select the Tokens that have different text

    startingwith("text"), not_startingwith("text")
        select the Tokens that do start (or not) with the specified text

    endingwith("text"), not_endingwith("text")
        select the Tokens that do end (or not) with the specified text

    containing("text"), not_containing("text")
        select the Tokens that contain (or not) specified text

    matching("regex"), not_matching("regex")
        select the Tokens that match (or not) the specified regular epression
        (using re.search, the expression can match anywhere unless you use
        ^ or $ characters).

    tokens
        select only the tokens

    contexts
        select only the contexts

    range(start=0, end=None)
        select only the nodes that fully fit in the range

    [int], __getitem__(int)
        select the nth child (if available) of each Context node
        (supports negative indices)

    [slice]
        select the specified slice of each Context node

    [action], [action, action<, action> ...]
        select the Tokens that have one of the specified actions

    in_action(*actions)
        select tokens if their action belongs in the realm of one of the
        specified StandardActions

    not_in_action(*actions)
        select tokens whose action does not inherit of one of the specified
        StandardActions

    in_lexicon(*lexicons)
        somewhat supplemental to (), yield the Context nodes if they
        have one of the specified lexicons

    not_in_lexicon(*lexicon)
        select the Context nodes that do not have one of the specified
        lexicons.

    uniq
        Removes double occurrences of Tokens or Contexts, which can happen
        e.g. when selecting the parent of all nodes


"""


import functools
import re
import sys

from .lexicon import BoundLexicon


def query(func):
    """Make a method result (generator) into a new Query object."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        return Query(lambda: func(self, *args, **kwargs))
    return wrapper


def pquery(func):
    """Make a method result into a Query object, and the method a property."""
    return property(query(func))


class Query:
    def __init__(self, gen):
        self._gen = gen

    def __iter__(self):
        return self._gen()

    # end points
    def count(self):
        """Compute the length of the iterable. Don't use this other than for debugging."""
        return sum(1 for _ in self)

    def dump(self):
        """Dump the current selection to the console."""
        for n in self:
            n.dump()

    def list(self):
        """Return the current selection as a list. Only for debugging."""
        return list(self)

    def pick(self, default=None):
        """Pick the first value, or return the default."""
        for n in self:
            return n
        return default

    # navigators
    @pquery
    def children(self):
        """All direct children of the current nodes."""
        for n in self:
            if n.is_context:
                yield from n

    @pquery
    def all(self):
        """All descendants, contexts and their nodes."""
        def innergen(node):
            for n in node:
                yield n
                if n.is_context:
                    yield from innergen(n)
        return innergen(self)

    @pquery
    def parent(self):
        for n in self:
            if n.parent:
                yield n.parent

    @pquery
    def uniq(self):
        """Remove double occurrences. Can happen when you use the parent."""
        seen = set()
        for n in self:
            i = id(n)
            if i not in seen:
                seen.add(i)
                yield n

    @pquery
    def next(self):
        """Yield the next token, if any."""
        for n in self:
            t = n.text_token()
            if t:
                yield t

    @pquery
    def prev(self):
        """Yield the previous token, if any."""
        for n in self:
            t = n.previous_token()
            if t:
                yield t

    @pquery
    def right(self):
        """Yield the right sibling, if any."""
        for n in self:
            n = n.right_sibling()
            if n:
                yield n

    @pquery
    def left(self):
        """Yield the left sibling, if any."""
        for n in self:
            n = n.left_sibling()
            if n:
                yield n

    # selectors
    @query
    def __call__(self, what):
        """Yield token if token has that text, or context if context has that lexicon."""
        if isinstance(what, BoundLexicon):
            for n in self:
                if n.is_context and n.lexicon == what:
                    yield n
        else:
            for n in self:
                if n.is_token and n.text == what:
                    yield n

    @query
    def has_not(self, what):
        """Opposite of __call__()."""
        if isinstance(what, BoundLexicon):
            for n in self:
                if n.is_context and n.lexicon != what:
                    yield n
        else:
            for n in self:
                if n.is_token and n.text != what:
                    yield n

    @query
    def startingwith(self, text):
        """Yield tokens that start with text."""
        for t in self:
            if t.is_token and t.text.startswith(text):
                yield t

    @query
    def not_startingwith(self, text):
        """Yield tokens that don't start with text."""
        for t in self:
            if t.is_token and not t.text.startswith(text):
                yield t

    @query
    def endingwith(self, text):
        """Yield tokens that end with text."""
        for t in self:
            if t.is_token and t.text.endswith(text):
                yield t

    @query
    def not_endingwith(self, text):
        """Yield tokens that don't end with text."""
        for t in self:
            if t.is_token and not t.text.endswith(text):
                yield t

    @query
    def containing(self, text):
        """Yield tokens that contain the specified text."""
        for t in self:
            if t.is_token and text in t.text:
                yield t

    @query
    def not_containing(self, text):
        """Yield tokens that don't contain the specified text."""
        for t in self:
            if t.is_token and text not in t.text:
                yield t

    @query
    def __getitem__(self, key):
        """normal slicing, and you can test for one or more actions."""
        if isinstance(key, int):
            for n in self:
                if n.is_context:
                    if key < 0:
                        key += len(n)
                    if 0 <= key < len(n):
                        yield n[key]
        elif isinstance(key, slice):
            for n in self:
                if n.is_context:
                    yield from n[key]
        elif isinstance(key, tuple):
            for t in self:
                if t.is_token and t.action in key:
                    yield t
        else:
            for t in self:
                if t.is_token and t.action is key:
                    yield t

    @query
    def is_not(self, *actions):
        """The opposite of [action<, action, ...>]."""
        for t in self:
            if t.is_token and t.action not in actions:
                yield t

    @pquery
    def tokens(self):
        """Get only the tokens."""
        for n in self:
            if n.is_token:
                yield n

    @pquery
    def contexts(self):
        """Get only the contexts."""
        for n in self:
            if n.is_context:
                yield n

    @query
    def range(self, start=0, end=None):
        """Yield a restricted set, tokens and/or contexts must fall in start→end"""
        if end is None:
            end = sys.maxsize
        # don't assume the tokens are in source order
        for n in self:
            if n.pos >= start and n.end <= end:
                yield n

    @query
    def matching(self, pattern, flags=0):
        """Yield tokens matching the regular expression (using re.search)."""
        for t in self:
            if t.is_token and re.search(pattern, t.text, flags):
                yield t

    @query
    def not_matching(self, pattern, flags=0):
        """Yield tokens matching the regular expression (using re.search)."""
        for t in self:
            if t.is_token and not re.search(pattern, t.text, flags):
                yield t

    @query
    def in_action(self, *actions):
        """Yield those tokens whose action is or inherits from one of the given actions."""
        for t in self:
            if t.is_token and any(t.action in a for a in actions):
                yield t

    @query
    def not_in_action(self, *actions):
        """Yield those tokens whose action is not and does not inherit from one of the given actions."""
        for t in self:
            if t.is_token and not any(t.action in a for a in actions):
                yield t

    @query
    def in_lexicon(self, *lexicons):
        """Yield those contexts that have one of the specified lexicons."""
        for n in self:
            if n.is_context and n.lexicon in lexicons:
                yield n

    @query
    def not_in_lexicon(self, *lexicons):
        """Yield those contexts that have not any of the specified lexicons."""
        for n in self:
            if n.is_context and n.lexicon not in lexicons:
                yield n


