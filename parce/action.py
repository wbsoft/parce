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
The action module defines two distinct base classes for actions.

StandardAction is the base class for fixed standard actions, and DynamicAction
is the base class for objects that yield actions based on the matched text.

In a parce rule, an action may be any object, e.g. a method, number or string
literal. So it is not necessary that you use the provided standard actions. The
dynamic actions can also be used with your own actions, and you can also
inherit from DynamicAction if you want.

These standard actions are intended to help create a uniform handling of
actions across multiple languages and lexicons.


StandardAction
==============

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


DynamicAction
=============

If an instance of DynamicAction is encountered in a rule, its replace()
method is called to yield a (pos, text action) tuple. Sometimes the
replace() method simply calls back the filter_actions() method of the
lexer with the new action, which could again be a DynamicAction instance or
another dynamic rule item.

Nesting is possible in most cases, only some actions require the match object
to be present; and such actions can't be used as default action, or inside
subgroup actions.

A DynamicAction object always holds all actions it is able to return in its
itemlists attribute. This is done so that it is possible to know all actions a
Language can generate beforehand, and e.g. translate all the actions in a
Language to other objects, which could even be methods or functions.

"""


import threading


from .rule import ActionItem


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


class DynamicAction(ActionItem):
    """Base class for dynamic action objects.

    All actions a DynamicAction object can yield are in the first item
    of the ``itemlists`` attribute.

    """
    def __init__(self, *actions):
        super().__init__(actions)

    def replace(self, lexer, pos, text, match):
        raise NotImplementedError()


class SubgroupAction(DynamicAction):
    """Yield actions from subgroups in a match.

    A SubgroupAction looks at subgroups in the regular expression match and
    returns the same amount of tokens as there are subgroups, using the specified
    action for every subgroup.

    For example, the rule::

        "(0x)([0-9a-f]+)", SubgroupAction(Number.Prefix, Number.Hexadecimal)

    yields two tokens in case of a match, one for "0x" and the other for the
    other group of the match.

    There should be the same number of subgroups in the regular expression as
    there are action attributes given to __init__().

    """
    def replace(self, lexer, pos, text, match):
        for i, action in enumerate(self.itemlists[0], match.lastindex + 1):
            yield from lexer.filter_actions(action, match.start(i), match.group(i), match)


class DelegateAction(DynamicAction):
    """This action uses a lexicon to parse the text.

    All tokens are yielded as one group, flattened, ignoring the tree
    structure, so this is not efficient for large portions of text, as the
    whole region is parsed again on every modification.

    But it can be useful when you want to match a not too large text blob first
    that's difficult to capture otherwise, and then lex it with a lexicon that
    does (almost) not enter other lexicons.

    """
    def __init__(self, lexicon):
        super().__init__(lexicon)

    def replace(self, lexer, pos, text, match):
        """Use our lexicon to parse the matched text."""
        lexicon = self.itemlists[0][0]
        sublexer = type(lexer)([lexicon])
        for e in sublexer.events(text):
            for p, txt, action in e.tokens:
                yield pos + p, txt, action


class SkipAction(DynamicAction):
    """A DynamicAction that yields nothing.

    A SkipAction() is stored in the module variable ``skip`` and causes the rule
    to silently ignore the matched text.

    """
    def replace(self, lexer, pos, text, match):
        yield from ()

