# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2019-2020 by Wilbert Berendsen <info@wilbertberendsen.nl>
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


r"""
Query the tree using the `query` property.

Using this module you can query the token tree to find tokens and contexts,
based on lexicons and/or actions and text contents. You can chain calls
in an XPath-like fashion.

This module supplements the various find_xxx methods of every Context object.
A query starts at the `query` property of a Context or Token object, and
initially yields just that object.

You can navigate using `children`, `all`, `first`, `last`, `[n]`, `[n:n]`,
`[n:n:n]`, `next`, `previous`, `right`, `left`, `right_siblings`,
`left_siblings`, `map()`, `parent` and `ancestors`. Use `uniq` to remove
double occurrences of nodes, which can e.g. happen when navigating to the
parent of all nodes.

You can narrow down the search using `tokens`, `contexts`, `remove_ancestors`,
`remove_descendants`, `slice()` and `filter()`.

You can search for tokens using `('text')` or `(lexicon)`, `startingwith()`,
`endingwith()`, `containing()`, `matching()`, `action()` or `in_action()`. The
special prefix `is_not` inverts the query, so `query.is_not.containing("bla")`
yields Tokens that do not contain the text "bla".


Examples:

Find all tokens that are the first child of a Context with bla lexicon::

    root.query.all(MyLang.bla)[0]


Find (in Xml) all attributes with name 'name' that are in a <bla> tag::

    root.query.all.action(Name.Tag)("bla").next('name')


Find all tags containing "hi" in their text nodes::

    root.query.all.action(Name.Tag).next.next.action(Text).containing('hi')


Find all comments that have TODO in it::

    root.query.all.action(Comment).containing('TODO')


Find all "\\version" tokens in the root context, that have a "2" in the version
string after it::

    (t for t in root.query.children('\\version')
        if any(t.query.next.target.children.containing('2')))

Which could also be written as::

    root.query.children('\\version').filter(
        lambda t: any(t.query.next.target.children.containing('2')))


A query is a generator, you can iterate over the results::

    for attrs in q.all.action(Name.Tag)('origin').right:
        for atr in attrs.query.action(Name.Attribute):
            print(atr)


For debugging purposes, there are also the ``list()``, ``pick()``, ``count()``
and ``dump()`` methods::

    root.query.all.action(Name.Tag)("img").count() # number of "img" tags
    root.query.all.action(Name.Tag)("img").list()  # list of all "img" tag name tokens


Note that a (partial) query can be reused, it simply restarts the iteration
over the results. The above could also be written as::

    q = root.query.all.action(Name.Tag)("img")
    q.count()   # number of "img" tags
    q.list()    # list of all "img" tag name tokens


A query resolves to False if there is no single result::

    if token.query.ancestors(LilyPond.header):
        do_something() # the token is a descendant of a LilyPond.header context


You can also directly instantiate a Query object for a list of nodes, if you
want to query those in one go::

    q = Query.from_nodes(nodes)



Summary of the query methods:
-----------------------------

Endpoint methods (some are mainly for debugging):

:meth:`~Query.count`,
:meth:`~Query.dump`,
:meth:`~Query.list`,
:meth:`~Query.pick`,
:meth:`~Query.pick_last`,
:meth:`~Query.range` and
:meth:`~Query.delete`.


Navigating nodes:
^^^^^^^^^^^^^^^^^

The query itself just yields the node it was started from. But using the
following methods you can find your way through a tree structure. Every method
returns a new Query object, having the previous one as source of nodes. Most
methods are implemented as properties, so you don't have to write parentheses.

:attr:`~Query.all`,
:attr:`~Query.children`,
:attr:`~Query.parent`,
:attr:`~Query.ancestors`,
:attr:`~Query.next`,
:attr:`~Query.previous`,
:attr:`~Query.forward`,
:attr:`~Query.backward`,
:attr:`~Query.right`,
:attr:`~Query.left`,
:attr:`~Query.right_siblings`,
:attr:`~Query.left_siblings`,
:attr:`[n] <Query.__getitem__>`,
:attr:`[n:m] <Query.__getitem__>`,
:attr:`~Query.first`,
:attr:`~Query.last`, and
:meth:`~Query.map`,


Selecting (filtering) nodes:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These methods filter out current nodes without adding new nodes
to the selection:

:attr:`~Query.tokens`,
:attr:`~Query.contexts`,
:attr:`~Query.uniq`,
:attr:`~Query.remove_ancestors`,
:attr:`~Query.remove_descendants`,
:meth:`~Query.slice` and
:meth:`~Query.filter`.

The special :attr:`~Query.is_not` operator inverts the meaning of the
next query, e.g.::

    n.query.all.is_not.startingwith("text")

The following query methods can be inverted by prepending `is_not`:

:meth:`~Query.len`,
:meth:`~Query.in_range`,
:meth:`(lexicon) <Query.__call__>`,
:meth:`(lexicon, lexicon2, ...) <Query.__call__>`,
:meth:`("text") <Query.__call__>`,
:meth:`("text", "text2", ...) <Query.__call__>`,
:meth:`~Query.startingwith`,
:meth:`~Query.endingwith`,
:meth:`~Query.containing`,
:meth:`~Query.matching`,
:meth:`~Query.action` and
:meth:`~Query.in_action`.

There is a subtle difference between `action` and `in_action`: with the
first, the action should exactly match, with the latter the tokens are
selected when the action exactly matches, or is a descendant of the given
action.

"""


import collections
import functools
import itertools
import re
import sys

from .lexicon import Lexicon


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
    """A Query navigates and filters a node tree.

    A Query is instantiated either by calling :attr:`Token.query
    <parce.tree.Node.query>` or :attr:`Context.query <parce.tree.Node.query>`,
    or by calling :meth:`Query.from_nodes` on a list of nodes (tokens and/or
    contexts).

    """
    __slots__ = '_gen', '_inv'

    def __init__(self, gen, invert=False):
        self._gen = gen
        self._inv = invert

    def __iter__(self):
        return self._gen()

    @classmethod
    def from_nodes(cls, nodes):
        """Create a Query object querying a list of nodes in one go."""
        return cls(lambda: iter(nodes))

    # end points
    def __bool__(self):
        """Return True if there is at least one result."""
        for n in self:
            return True
        return False

    def count(self):
        """Compute the length of the iterable."""
        return sum(1 for _ in self)

    def dump(self, file=None):
        """Dump the current selection to the console (or to file)."""
        for n in self:
            n.dump(file)

    def list(self):
        """Return the current selection as a list. Mainly for debugging."""
        return list(self)

    def pick(self, default=None):
        """Pick the first value, or return the default."""
        for n in self:
            return n
        return default

    def pick_last(self, default=None):
        """Pick the last value, or return the default."""
        for default in self:
            pass
        return default

    def range(self):
        """Return the text range as a tuple (pos, end).

        The ``pos`` is the lowest pos of the nodes in the current set, and
        ``end`` is the highest end of the nodes.  If the result set is empty,
        (-1, -1) is returned.

        """
        pos = end = -1
        nodes = iter(self)
        for n in nodes:
            pos = n.pos
            end = n.end
            for n in nodes:
                pos = min(pos, n.pos)
                end = max(end, n.end)
        return pos, end

    def delete(self):
        """Delete all selected nodes from their parents.

        Internally calls ``uniq`` and ``remove_descendants``, so that no
        unnecessary deletes are done. If a context would become empty, that
        context itself is deleted instead of all its children (except for the
        root of course). Returns the number of nodes that were deleted.

        """
        d = collections.defaultdict(list)
        for n in self.uniq.remove_descendants:
            d[n.parent].append(n)
        count = 0
        # deleting a root context makes no sense, clear it in that case
        roots = d.get(None)
        if roots:
            for root in roots:
                count += len(root)
                root.clear()
            del d[None]
        # if a parent looses all children, remove itself too
        while True:
            remove = [parent
                for parent, nodes in d.items()
                    if len(nodes) == len(parent) and parent.parent is not None]
            if not remove:
                break
            for n in remove:
                del d[n]
                d[n.parent].append(n)
        # be sure nodes to delete are sorted on pos
        for l in d.values():
            l.sort(key=lambda n: n.pos)
            count += len(l)
        for parent, nodes in d.items():
            n = nodes[0]
            i = 0 if n is parent[0] else n.parent_index()
            slices = [[i, i+1]]
            for n in nodes[1:]:
                if n is parent[i+1]:
                    i += 1
                    slices[-1][1] += 1
                else:
                    i = n.parent_index()
                    slices.append([i, i+1])
            for i, j in reversed(slices):
                del parent[i:j]
        return count

    # navigators
    @query
    def __getitem__(self, key):
        """Get the specified item or items of every context node.

        Note that the result nodes always form a flat iterable. No IndexError
        will be raised if an index would be out of range for any node.

        """
        # slicing or itemgetting with integers are not invertible selectors
        if isinstance(key, slice):
            for n in self:
                if n.is_context:
                    yield from n[key]
        else:
            for n in self:
                if n.is_context:
                    if key < 0:
                        key += len(n)
                    if 0 <= key < len(n):
                        yield n[key]

    @pquery
    def children(self):
        """All direct children of the current nodes."""
        for n in self:
            if n.is_context:
                yield from n

    @pquery
    def all(self):
        """All descendants, contexts and their nodes."""
        def innergen(n):
            stack = []
            j = 0
            while True:
                for i in range(j, len(n)):
                    m = n[i]
                    yield m
                    if m.is_context:
                        stack.append(i)
                        j = 0
                        n = m
                        break
                else:
                    if stack:
                        n = n.parent
                        j = stack.pop() + 1
                    else:
                        break
        for n in self:
            yield n
            if n.is_context:
                yield from innergen(n)

    @pquery
    def alltokens(self):
        """Shortcut for all.tokens."""
        for n in self:
            if n.is_token:
                yield n
            else:
                yield from n.tokens()

    @pquery
    def allcontexts(self):
        """Shortcut for all.contexts."""
        def innergen(n):
            stack = []
            j = 0
            while True:
                for i in range(j, len(n)):
                    m = n[i]
                    if m.is_context:
                        yield m
                        stack.append(i)
                        j = 0
                        n = m
                        break
                else:
                    if stack:
                        n = n.parent
                        j = stack.pop() + 1
                    else:
                        break
        for n in self:
            if n.is_context:
                yield n
                yield from innergen(n)

    @pquery
    def parent(self):
        """Yield the parent of every node.

        This can lead to many double occurrences of the same node in the
        result set; use :attr:`~Query.uniq` to fix that.

        """
        for n in self:
            if n.parent:
                yield n.parent

    @pquery
    def ancestors(self):
        """Yield the ancestor contexts of every node."""
        for n in self:
            yield from n.ancestors()

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
            t = n.next_token()
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
    def forward(self):
        """Yield Tokens in forward direction."""
        for n in self:
            yield from n.forward()

    @pquery
    def backward(self):
        """Yield Tokens in backward direction."""
        for n in self:
            yield from n.backward()

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
    def right_siblings(self):
        """Yield the right siblings, if any."""
        for n in self:
            yield from n.right_siblings()

    @pquery
    def left_siblings(self):
        """Yield the left siblings, if any."""
        for n in self:
            yield from n.left_siblings()

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
        """Remove double occurrences of the same node from the result set.

        This can happen e.g. when you find the parent of multiple nodes.

        """
        seen = set()
        for n in self:
            i = id(n)
            if i not in seen:
                seen.add(i)
                yield n

    @query
    def slice(self, *args):
        """Slice the full result set, using :py:func:`itertools.islice`.

        This can help narrowing down the result set. For example::

            root.query.all("blaat").slice(1).right_siblings.slice(3) ...

        will continue the query with only the first occurrence of a token
        "blaat", and then look for at most three right siblings. If the
        slice(1) were not there, all the right siblings would become one
        large result set because you wouldn't know how many tokens "blaat"
        were matched.

        """
        yield from itertools.islice(self, *args)

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

    @property
    def is_not(self):
        """Invert the next query."""
        return type(self)(self._gen, not self._inv)

    # invertible selectors
    @query
    def len(self, min_length, max_length=None):
        """Only yield contexts, with min_length, or with length between min and max."""
        if max_length is None:
            for n in self:
                if n.is_context and self._inv ^ (len(n) == min_length):
                    yield n
        else:
            for n in self:
                if n.is_context and self._inv ^ (min_length <= len(n) <= max_length):
                    yield n

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
        """Yield token if token has that text, or context if context has that lexicon.

        You can even mix the types if you'd need to::

            for n in tree.query.all("%", Lang.comment):
                # do something

        yields tokens that are a percent sign and contexts that have the
        Lang.comment lexicon.

        """
        for n in self:
            if self._inv ^ (n in what):
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
    def matching(self, pattern, flags=0):
        """Yield tokens matching the regular expression.

        :func:`re.search` is used, so the expression can match anywhere
        unless you use ^ or $ characters).

        """
        search = re.compile(pattern, flags).search
        for t in self:
            if t.is_token and self._inv ^ bool(search(t.text)):
                yield t

    @query
    def action(self, *actions):
        """Yield those tokens whose action *is* one of the given actions."""
        for t in self:
            if t.is_token and self._inv ^ (t.action in actions):
                yield t

    @query
    def in_action(self, *actions):
        """Yield those tokens whose action *is or inherits from* one of the given actions."""
        for t in self:
            if t.is_token and self._inv ^ any(t.action in a for a in actions):
                yield t

