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
Replacable rule item objects.

In planning/sketching phase, will replace current rule.py items.


Items:

``ARG``
    represents the lexicon argument
``MATCH``
    represents the match object of a regular expression match
``MATCH(n)``
    represents the text in a subgroup of the match (subgroups start with 1)
``MATCH(n)[s]``
    represents a slice of the text in a subgroup (fails if the group is None)
``TEXT``
    represents the matched text
``TEXT[s]``
    represents a slice of the matched text


``call(callable, *arguments)``
    gets the result of calling callable with zero or more arguments


these are RuleItem types(allowed in toplevel a rule)

``choose(index, *items)``
    chooses the item pointed to by the value in index. When an item ends up in
    a rule; it is unrolled when it is a list.
``target(value, *lexicons)``
    has a special handling: if the value is an integer, return it (pop or push
    value). If it is a two-tuple(index, arg): derive the lexicon at index with
    arg.

these survive evaluating, although the *pre*-evaluation process may alter their
attributes:

``pattern(value)``
    only allowed as the first item in a rule; is expected to create a string
    or None, causing the rule to be skipped.

``ActionItem(*items)``

"""


class EvaluationError(Exception):
    """Raised when an attribute is missing in the evaluation namespace."""
    pass


class Item:
    """Base class for any replacable rule item."""
    __slots__ = ()

    def __getitem__(self, n):
        return call(_get_item, self, n)

    def evaluate(self, ns):
        """Evaluate in namespace dict.

        The namespace has 'text', 'arg' and/or 'match; attributes.
        If one that it needed is not there, EvaluationError is raised.

        The default implementation returns self.

        """
        return self


    def pre_evaluate(self, ns):
        """Try to evaluate; return a two-tuple(obj, success).

        If success, the obj is the result, if not; obj is self. Specific items
        my implement this to replace successfully evaluated sub-attributes.

        """
        try:
            return self.evaluate(ns), 1
        except EvaluationError:
            return self, 0

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ', '.join(map(repr, self._repr_args())))

    def _repr_args(self):
        return ()


class RuleItem(Item):
    """Base class for items that may become visible in rules."""
    __slots__ = ()


class VariableItem(Item):
    """A named variable that's accessed in the namespace."""
    __slots__ = ()
    name = "name"

    def evaluate(self, ns):
        """Get the variable from the namespace dict."""
        try:
            return ns[self.name]
        except KeyError as e:
            raise EvaluationError("Can't find variable '{name}'".format(self.name)) from e

    def __repr__(self):
        return self.name.upper()


class ArgItem(VariableItem):
    """Represents the ``arg`` attribute in the namespace."""
    __slots__ = ()
    name = "arg"


class TextItem(VariableItem):
    """Represents the ``text`` attribute in the namespace."""
    __slots__ = ()
    name = "text"


class MatchItem(VariableItem):
    """Represents the ``match`` attribute in the namespace."""
    __slots__ = ()
    name = "match"

    def __call__(self, n):
        return call(_get_match_group, self, n)

#: the lexicon argument
ARG = ArgItem()

#: the regular expression match (or None)
MATCH = MatchItem()

#: the matched text
TEXT = TextItem()


del ArgItem, MatchItem, TextItem, VariableItem


class call(Item):
    """Call predicate with arguments."""
    __slots__ = ('_predicate', '_arguments')
    def __init__(self, predicate, *arguments):
        self._predicate = predicate
        self._arguments = arguments

    def evaluate(self, ns):
        """Call predicate with the arguments."""
        predicate = self._predicate
        if isinstance(predicate, Item):
            predicate = predicate.evaluate(ns)
        arguments = []
        for a in self._arguments:
            if isinstance(a, Item):
                a = a.evaluate(ns)
            arguments.append(a)
        return predicate(*arguments)

    def pre_evaluate(self, ns):
        """Optimize by pre-evaluating what can be pre-evaluated."""
        predicate = self._predicate
        if isinstance(predicate, Item):
            predicate, pred_ok = predicate.pre_evaluate(ns)
        else:
            pred_ok = 1
        arguments, found = [], []
        for a in self._arguments:
            if isinstance(a, Item):
                a, ok = a.pre_evaluate(ns)
            else:
                ok = 1
            arguments.append(a)
            found.append(ok)
        if pred_ok and all(found):
            return predicate(*arguments), 1
        if pred_ok or any(found):
            return type(self)(predicate, *arguments), 0
        return self, 0      # nothing changed

    def _repr_args(self):
        return (self._predicate, *self._arguments)


class RuleItem(Item):
    """Classes inheriting RuleItem are allowed in toplevel in rules."""
    __slots__ = ()


class choose(RuleItem):
    """Chooses one of the items.

    If an item is a list, it is unrolled when replacing the item in a rule.

    """
    __slots__ = ('_index', '_items')

    def __init__(self, index, *items):
        self._index = index
        self._items = items

    def evaluate(self, ns):
        """Return items[index]."""
        index = self._index
        if isinstance(index, Item):
            index = index.evaluate(ns)
        item = self._items[index]
        if isinstance(item, Item):
            item = item.evaluate(ns)
        return item

    def pre_evaluate(self, ns):
        """Optimize by pre-evaluating what can be pre-evaluated."""
        index, ok = self._index, 1
        if isinstance(index, Item):
            index, ok = index.pre_evaluate(ns)
        if ok:
            # we know the index, only one item needs to be evaluated
            # and can be returned.
            item = self._items[index]
            if isinstance(item, Item):
                return item.pre_evaluate(ns)
            return item, 1
        # we don't yet know the index, pre-evaluate every item
        # is possible.
        items, found = [], []
        for i in self._items:
            if isinstance(i, Item):
                i, ok = i.pre_evaluate(ns)
            else:
                ok = 1
            items.append(i)
            found.append(ok)
        if any(found):
            return type(self)(index, items), 0
        return self, 0      # nothing changed

    def _repr_args(self):
        return (self._index, *self._items)


class target(RuleItem):
    """target(value, *lexicons)

    Has a special handling: if the value is an integer, it is used as the
    result value (to push/pop contexts).

    If it is a two-tuple(index, argument): The index points to the lexicon the
    argument is used as lexicon argument.

    """
    __slots__ = ('_value', '_lexicons')

    def __init__(self, value, *lexicons):
        self._value = value
        self._lexicons = lexicons

    def evaluate(self, ns):
        """Return value if integer, otherwise lexicons[value[0]](value[1])."""
        value = self._value
        if isinstance(value, Item):
            value = value.evaluate(ns)
        if isinstance(value, int):
            return value
        index, arg = value
        lexicon = self._lexicons[index]
        if isinstance(lexicon, Item):
            lexicon = lexicon.evaluate(ns)
        if arg is not None:
            return lexicon(arg)
        return lexicon

    def pre_evaluate(self, ns):
        """Optimize by pre-evaluating what can be pre-evaluated."""
        value, ok = self._value, 1
        if isinstance(value, Item):
            value, ok = value.pre_evaluate(ns)
        if ok:
            if isinstance(value, int):
                return value, 1
            index, arg = value
            lexicon = self._lexicons[index]
            if isinstance(lexicon, Item):
                lexicon, ok = lexicon.pre_evaluate(ns)
            if ok:
                return lexicon(arg), 1
            return type(self)((0, arg), *[lexicon]), 0
        # pre-evaluate the lexicons
        lexicons, found = [], []
        for lexicon in self._lexicons:
            if isinstance(lexicon, Item):
                lexicon, ok = lexicon.pre_evaluate(ns)
            else:
                ok = 1
            lexicons.append(lexicon)
            found.append(ok)
        if any(found):
            return type(self)(value, lexicons), 0
        return self

    def _repr_args(self):
        return (self._value, *self._lexicons)


class SurvivingItem(RuleItem):
    """Allowed in a rule, but evaluation is postponed, although pre-evaluation
    may occur."""
    __slots__ = ()

    def evaluate(self, ns):
        return self


class ActionItem(SurvivingItem):
    """Base class for dynamic actions.

    The actions are replaced, but the object itself remains alive after
    building the rule.

    """
    __slots__ = ()
    ## when pre-evaluating with ARG, allow actions inside SubgroupAction
    ## to be replaced. But not when evaluating. Then it's done by the lexer.
    def evaluate(self, ns):
        """Evaluates sub-items, but returns self."""
        return self


class pattern(SurvivingItem):
    """Represents a pattern.

    This evaluates its value, but remains alive after building the rule.

    """
    __slots__ = ('_value',)

    def __init__(self, value):
        self.value = value

    def evaluate(self, ns):
        """Evaluate the value, but return self."""
        value = self._value
        if isinstance(value, Item):
            return type(self)(value.evaluate(ns))
        return self

    def pre_evaluate(self, ns):
        """Try to evaluate the value, but return self."""
        value = self._value
        if isinstance(value, Item):
            value, ok = value.pre_evaluate(ns)
            if ok:
                return type(self)(value), 1
            return self, 0
        return self, 1

    def _repr_args(self):
        return self.value


def _get_item(text, n):
    return text[n]


def _get_match_group(match, n):
    return match.group(match.lastindex + n)


