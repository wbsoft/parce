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


"""
This module defines StandardAction.

A StandardAction is a singleton object. Acessing an attribute (without
underscore) creates that attribute as a new instance, with the current instance
as _parent.

This way a new action type can be created that shares its parent with other
types, a concept borrowed from pygments. An example::

    >>> Comment = StandardAction("Comment")
    >>> Literal = StandardAction("Literal")
    >>> String = Literal.String
    >>> String.DoubleQuotedString
    Literal.String.DoubleQuotedString
    >>> String.SingleQuotedString
    Literal.String.SingleQuotedString

StandardAction instances support iteration and membership methods.
Iteration yields the instance ifself and then the parents::

    >>> for i in String.DoubleQuoted:
    ...     print(i)
    ...
    Literal.String.DoubleQuoted
    Literal.String
    Literal

And the :keyword:`in` operator returns True when a standard action belongs to
another one, i.e. the other one is one of the ancestors of the current action::

    >>> String.DoubleQuotedString in String
    True
    >>> Literal in String
    False

The :keyword:`in` operator also works with a string::

    >>> 'String' in Literal.String.DoubleQuoted
    True
    >>> 'Literal' in String
    True

The last one could be surprising, but String is defined as ``Literal.String``::

    >>> String
    Literal.String

Finally, the `&` operator returns the common ancestor, if any::

    >>> String & Number
    Literal
    >>> String & Text
    >>>

See for the full list of pre-defined standard actions :doc:`stdactions`.


"""


import threading

# we use a global lock for standardaction creation, it seems overkill
# to me to equip every instance with one.
_lock = threading.Lock()

_toplevel_actions = {}       # store the "root" actions


class StandardAction:
    """Factory for standard action singletons."""
    def __new__(cls, name, parent=None):
        d = parent.__dict__ if parent else _toplevel_actions
        with _lock:
            try:
                return d[name]
            except KeyError:
                new = d[name] = object.__new__(cls)
                new._name = name
                new._parent = parent
                return new

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError("{} has no attribute {}".format(self, repr(name)))
        return type(self)(name, self)

    def __repr__(self):
        return ".".join(reversed([n._name for n in self]))

    def __iter__(self):
        node = self
        while node:
            yield node
            node = node._parent

    def __contains__(self, other):
        if isinstance(other, str):
            return any(t._name == other for t in self)
        return any(t is self for t in other)

    def __and__(self, other):
        ancestors = frozenset(other)
        for t in self:
            if t in ancestors:
                return t

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

