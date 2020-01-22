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
types, a concept borrowed from pygments. An example:

    >>> Comment = StandardAction("Comment")
    >>> Literal = StandardAction("Literal")
    >>> String = Literal.String
    >>> String.DoubleQuotedString
    Literal.String.DoubleQuotedString
    >>> String.SingleQuotedString
    Literal.String.SingleQuotedString

StandardAction instances support iteration and membership methods.
Iteration yields the instance ifself and then the parents:

    >>> for i in String.DoubleQuoted:
    ...     print(i)
    ...
    Literal.String.DoubleQuoted
    Literal.String
    Literal

And the `in` operator returns True when a standard action belongs to another
one, i.e. the other one is one of the ancestors of the current action:

    >>> String.DoubleQuotedString in String
    True
    >>> Literal in String
    False

Finally, the `&` operator returns the common ancestor, if any.

This module defines the following pre-defined standard actions:

    Whitespace = action.StandardAction("Whitespace")
    Text = action.StandardAction("Text")

    Escape = action.StandardAction("Escape")
    Keyword = action.StandardAction("Keyword")
    Name = action.StandardAction("Name")
    Literal = action.StandardAction("Literal")
    Delimiter = action.StandardAction("Delimiter")
    Comment = action.StandardAction("Comment")
    Error = action.StandardAction("Error")

    Verbatim= Literal.Verbatim
    String = Literal.String
    Number = Literal.Number
    Builtin = Name.Builtin
    Variable = Name.Variable

(This list may be out of date, see __init__.py for the exact list.)


DynamicAction
=============

If an instance of DynamicAction is encountered in a rule, its filter_actions()
method is called to yield a (pos, text action) tuple. Normally the
filter_actions() method simply calls back the filter_actions() method of the
lexer with the new action, which could again be an Action instance.

Nesting is possible in most cases, only some actions require the match object
to be present; and such actions can't be used as default action, or inside
subgroup_actions.

A DynamicAction object always holds all actions it is able to return in the
actions attribute. This is done so that it is possible to know all actions a
Language can generate beforehand, and e.g. translate all the actions in a
Language to other objects, which could even be methods or functions.

SubgroupAction
--------------

A SubgroupAction looks at subgroups in the regular expression match and
returns the same amount of tokens as there are subgroups, using the specified
action for every subgroup.

For example, the rule:

    "(0x)([0-9a-f]+)", SubgroupAction(Number.Prefix, Number.Hexadecimal)

    yields two tokens in case of a match, one for "0x" and the other for the
    other group of the match.

TextAction and MatchAction
--------------------------

Those expect a preficate function as the first argument, and one or more
actions as further arguments.

The predicate is run if the rule matches, for TextAction with the text
as argument, and for MatchAction with the match object as argument. The
return value is the index of the action to pick. False and True count as
0 and 1 respectively.

A _SkipAction() is stored in the module variable `skip` and causes the rule
to silently ignore the matched text.

"""


class StandardAction:
    """Factory for standard action singletons."""
    _parent = None
    def __init__(self, name):
        self._name = name

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError("{} has no attribute {}".format(self, repr(name)))
        new = type(self)(name)
        new._parent = self
        setattr(self, name, new)
        return new

    def __repr__(self):
        return ".".join(reversed([n._name for n in self]))

    def __iter__(self):
        node = self
        while node:
            yield node
            node = node._parent

    def __contains__(self, other):
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


class DynamicAction:
    """Base class for dynamic action objects.

    All actions a DynamicAction object can yield are in the actions attribute.

    """
    def __init__(self, *actions):
        self.actions = actions

    def filter_actions(self, lexer, pos, text, match):
        raise NotImplementedError


class SubgroupAction(DynamicAction):
    """Yield actions from subgroups in a match.

    There should be the same number of subgroups in the regular expression as
    there are action attributes given to __init__().

    """
    def filter_actions(self, lexer, pos, text, match):
        for i, action in enumerate(self.actions, match.lastindex + 1):
            yield from lexer.filter_actions(action, match.start(i), match.group(i), None)


class PredicateAction(DynamicAction):
    """Base class expecting a predicate function and actions."""
    def __init__(self, predicate, *actions):
        self.predicate = predicate
        super().__init__(*actions)

    def index(self, text, match):
        raise NotImplementedError

    def filter_actions(self, lexer, pos, text, match):
        index = self.index(text, match)
        action = self.actions[index]
        yield from lexer.filter_actions(action, pos, text, match)


class MatchAction(PredicateAction):
    """Expects a function as argument that is called with the match object.

    The function should return the index indicating the action to return.
    The function may also return True or False, which are regarded as 1 or 0,
    respectively.

    """
    def index(self, text, match):
        return self.predicate(match)


class TextAction(PredicateAction):
    """Expects a function as argument that is called with the matched text.

    The function should return the index indicating the action to return.
    The function may also return True or False, which are regarded as 1 or 0,
    respectively.

    """
    def index(self, text, match):
        return self.predicate(text)


class SkipAction(DynamicAction):
    """A DynamicAction that yields nothing."""
    def filter_actions(self, lexer, pos, text, match):
        yield from ()

