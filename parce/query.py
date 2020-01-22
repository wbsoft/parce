# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
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
in an XPath-like fashion.

This module supplements the various find_xxx methods of every Context object.
A query starts at the `query` property of a Context object, and yields all the
nodes of that Context.

You can navigate using `children`, `all`, `[n]`, `[n:n]`, (`[n:n:n]`),
`next`, `previous`, `right`, `left`, and `parent`. Use `uniq` to remove double
occurrences of nodes, which can e.g. happen when navigating to the parent of
all nodes.

You can narrow down the search using `tokens`, `contexts`, `('text')` or
`(lexicon)`, `has_not`, `[n]`, `[n:n]`, `[action]`, `[action, action]`,
`startingwith()`, `endingwith()`, `containing()`, `matching()`, `uniq`,
`in_action()`,  and the corresponding `not_` counterparts, and `__getitem__`
and `is_not()`.



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

Endpoint methods, mainly for debugging:

    count()
        Just prints the number of nodes in the result set

    dump()
        dump()s the full result nodes to stdout

    list()
        aggregate the results in a list

    pick(default=None)
        just pick the first result, or a default if no results


Navigating nodes:

    The query itself yields al children of the Context it was started from.
    But using the following methods you can find your way through a tree
    structure. Every method returns a new Query object, having the previous
    one as source of nodes. Most methods are implemented as properties, so
    you don't have to write parentheses.

    all
        yield all descendant nodes, depth-first, in order. First it yields the
        context, then its children.

    children
        yield all the direct children of the current nodes

    parent
        yield the parent of all current nodes. This can yield double
        occurrences of nodes in the list. (Use uniq to fix that.)

    next, previous
        yield the next or previous Token from the current node, if any

    right, left
        yield the right or left sibling of every current node, if any

    [int], __getitem__(int)
        yield the nth child (if available) of each Context node
        (supports negative indices)

    [slice]
        yield from the specified slice of each Context node

    first, last
        yield the first resp. the last child of every Context node.
        Same as [0] or [-1].

    target
        yield the target context for a token, if any. See Token.target().

    source
        yield the source token for a context, if any. See Context.source().


Selecting (filtering) nodes:

    These methods filter out current nodes without adding new nodes
    to the selection.

    tokens
        select only the tokens

    contexts
        select only the contexts

    uniq
        Removes double occurrences of Tokens or Contexts, which can happen
        e.g. when selecting the parent of all nodes

    filter(predicate)
        select nodes for which the predicate function returns a value that
        evaluates to True

    map(function)
        call function on every node and yield its results, which should be
        nodes as well.

    is_not
        inverts the meaning of the following query, e.g. is_not.startingwith()

    The following query methods are inverted by `is_not`:

    in_range(start=0, end=None)
        select only the nodes that fully fit in the text range. If preceded
        by `is_not`, selects the nodes that are outside the specified text
        range.

    (lexicon, [lexicon, ...])
        select the Contexts with that lexicon (or one of the lexicons)

    ("text"), ("text", ["text2", ...])
        select the Tokens with exact that text (or one of the texts)

    startingwith("text")
        select the Tokens that start with the specified text

    endingwith("text")
        select the Tokens that end with the specified text

    containing("text")
        select the Tokens that contain specified text

    matching("regex")
        select the Tokens that match the specified regular epression
        (using re.search, the expression can match anywhere unless you use
        ^ or $ characters).

    [action], [action, action<, action> ...]
        select the Tokens that have one of the specified actions

    in_action(*actions)
        select tokens if their action belongs in the realm of one of the
        specified StandardActions

    remove_ancestors
        remove Context nodes from the current node list that have descendants
        in the list.

    remove_descendants
        remove nodes from the current list if any of their ancestors is also
        in the list.


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
    __slots__ = '_gen', '_inv'

    def __init__(self, gen, invert=False):
        self._gen = gen
        self._inv = invert

    def __iter__(self):
        return self._gen()

    @property
    def is_not(self):
        """Invert the next query."""
        return Query(self._gen, not self._inv)

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
        """The parent of every node."""
        for n in self:
            if n.parent:
                yield n.parent

    @pquery
    def first(self):
        """Yield the first node of every context node, same as [0]."""
        for n in self:
            if n and n.is_context:
                yield n[0]

    @pquery
    def last(self):
        """Yield the last node of every context node, same as [-1]."""
        for n in self:
            if n and n.is_context:
                yield n[-1]

    @pquery
    def next(self):
        """Yield the next token, if any."""
        for n in self:
            t = n.text_token()
            if t:
                yield t

    @pquery
    def previous(self):
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

    @pquery
    def target(self):
        """Yield the target Context for every token, if available. See Token.target()."""
        for t in self:
            if t.is_token:
                target = t.target()
                if target:
                    yield target

    @pquery
    def source(self):
        """Yield the source Token for every context, if available. See Context.source()."""
        for n in self:
            if n.is_context:
                source = n.source()
                if source:
                    yield source

    @query
    def map(self, function):
        """Call the function on every node and yield its results, which should be zero or more nodes as well."""
        for n in self:
            yield from function(n)

    # selectors
    @query
    def filter(self, predicate):
        """Yield nodes for which the predicate returns a value that evaluates to True."""
        for n in self:
            if predicate(n):
                yield n

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
    def remove_descendants(self):
        """Remove nodes that have ancestors in the current node list."""
        ids = set(map(id, self))
        for n in self:
            if not any(id(p) in ids for p in n.ancestors()):
                yield n

    @pquery
    def remove_ancestors(self):
        """Remove nodes that have descendants in the current node list."""
        ids = set(map(id, self)) & set(map(id, (p for n in self for p in n.ancestors())))
        for n in self:
            if id(n) not in ids:
                yield n

    # invertible selectors
    @query
    def in_range(self, start=0, end=None):
        """Yield a restricted set, tokens and/or contexts must fall in start→end"""
        if end is None:
            end = sys.maxsize
        # don't assume the tokens are in source order
        if self._inv:
            for n in self:
                if n.end <= start or n.pos >= end:
                    yield n
        else:
            for n in self:
                if n.pos >= start and n.end <= end:
                    yield n

    @query
    def __call__(self, *what):
        """Yield token if token has that text, or context if context has that lexicon."""
        if isinstance(what[0], BoundLexicon):
            for n in self:
                if n.is_context and self._inv ^ (n.lexicon in what):
                    yield n
        else:
            for n in self:
                if n.is_token and self._inv ^ (n.text in what):
                    yield n

    @query
    def startingwith(self, text):
        """Yield tokens that start with text."""
        for t in self:
            if t.is_token and self._inv ^ t.text.startswith(text):
                yield t

    @query
    def endingwith(self, text):
        """Yield tokens that end with text."""
        for t in self:
            if t.is_token and self._inv ^ t.text.endswith(text):
                yield t

    @query
    def containing(self, text):
        """Yield tokens that contain the specified text."""
        for t in self:
            if t.is_token and self._inv ^ (text in t.text):
                yield t

    @query
    def __getitem__(self, key):
        """normal slicing, and you can test for one or more actions."""
        # slicing or itemgetting with integers are not invertible selectors
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
        # handle matching actions, this is invertible by is_not
        elif isinstance(key, tuple):
            for t in self:
                if t.is_token and self._inv ^ (t.action in key):
                    yield t
        else:
            for t in self:
                if t.is_token and self._inv ^ (t.action is key):
                    yield t

    @query
    def matching(self, pattern, flags=0):
        """Yield tokens matching the regular expression (using re.search)."""
        for t in self:
            if t.is_token and self._inv ^ bool(re.search(pattern, t.text, flags)):
                yield t

    @query
    def in_action(self, *actions):
        """Yield those tokens whose action is or inherits from one of the given actions."""
        for t in self:
            if t.is_token and self._inv ^ any(t.action in a for a in actions):
                yield t

