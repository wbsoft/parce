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

When the Lexicon builds its internal representation of the rules,
RuleItem instances are evaluated in two stages. First, the items
are pre-elevated: meaning that the items that depend on the lexicon
argument (the ARG variable) are evaluated.

When a rule matches during parsing, the rest of the items are evaluated
using the TEXT and the MATCH variables.

Only Items that inherit from RuleItem may directly appear in a rule,
and items that they expose (such as the items a :class:`choose` Item chooses
from) must also inherit from RuleItem.

This way, we can be sure that we are able to validate a Lexicon beforehand,
and know all actions or target lexicons that it might yield during parsing.

A third evaluation stage happens in the lexer, for Item objects that inherit
of ActionItem.

The following fixed Item instances are defined here:

``ARG``
    represents the lexicon argument
``MATCH``
    represents the match object of a regular expression match
``TEXT``
    represents the matched text

The match and text variables have some additional functionality:

``MATCH(n)``
    represents the text in a subgroup of the match (subgroups start with 1)
``MATCH(n)[s]``
    represents a slice of the text in a subgroup (fails if the group is None)
``TEXT[s]``
    represents a slice of the matched text

Very often you want to use a predicate function on one of the above
variables, then you need the ``call`` item type:

``call(callable, *arguments)``
    gets the result of calling callable with zero or more arguments

Callable and arguments may also be Item instances.
The ``call`` item type is not allowed directly in a rule, because is not clear
what value it will return. Use it in combination with ``choose``, ``target``,
``pattern`` or dynamic actions (see below).

The following items are RuleItem types (allowed in toplevel in a rule):

``choose(index, *items)``
    chooses the item pointed to by the value in index. The item that ends up in
    a rule is unrolled when it is a list.
``target(value, *lexicons)``
    has a special handling: if the value is an integer, return it (pop or push
    value). If it is a two-tuple(index, arg): derive the lexicon at index with
    arg.

And the following items may also appear in a rule, they survive evaluating,
although the *pre*-evaluation process may alter their attributes:

``pattern(value)``
    only allowed as the first item in a rule; is expected to create a string
    or None. If None, the whole rule is skipped.

``ActionItem(*items)``
    base class for dynamic actions. Those are not evaluated by the Lexicon,
    although the items they contain may be. The lexer takes care of these
    items.

"""


from . import util


class _EvaluationError(RuntimeError):
    """Raised when an attribute is missing in the evaluation namespace."""
    pass


class Item:
    """Base class for any replacable rule item.

    An Item is considered to be immutable; you should never alter the
    attributes after instantiation. When an Item can be partly pre-evaluated a
    copy must be returned by calling ``type(self)(*args)``.

    In some cases you can also return a different Item type when pre-evaluating
    partly succeeds. For example, the :class:`choose` type simply returns the
    chosen item if the index already can be evaluated, without evaluating the
    other items.


    """
    __slots__ = ()

    def __getitem__(self, n):
        return call(_get_item, self, n)

    def evaluate(self, ns):
        """Evaluate item in namespace dict."""
        raise NotImplementedError

    def pre_evaluate(self, ns):
        """Try to evaluate; return a two-tuple(obj, success).

        If success = 1, the obj is the result, if 0; obj is the item itself, or
        a partially evaluated copy of the item. Specific items may re-implement
        this to return a copy with successfully evaluated sub-attributes
        replaced.

        """
        try:
            return self.evaluate(ns), 1
        except _EvaluationError:
            return self, 0

    def variations(self):
        """Yield the possible results for this item.

        This is used to build a decision tree for a rule, to see which actions
        and targets it could bring.

        The default implementation raises a RuntimeError; only RuleItem
        objects can yield variations.

        """
        raise RuntimeError("Item '{}' can't be used directly in a rule".format(repr(self)))

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ', '.join(map(repr, self._repr_args())))

    def _repr_args(self):
        return ()


class RuleItem(Item):
    """Base class for items that may become visible in rules."""
    __slots__ = ()


class _VariableItem(Item):
    """A named variable that's accessed in the namespace."""
    __slots__ = ()
    name = "name"

    def evaluate(self, ns):
        """Get the variable from the namespace dict."""
        try:
            return ns[self.name]
        except KeyError as e:
            raise _EvaluationError("Can't find variable '{}'".format(self.name)) from e

    def __repr__(self):
        return self.name.upper()


class _ArgItem(_VariableItem):
    """Represents the ``arg`` attribute in the namespace."""
    __slots__ = ()
    name = "arg"


class _TextItem(_VariableItem):
    """Represents the ``text`` attribute in the namespace."""
    __slots__ = ()
    name = "text"


class _MatchItem(_VariableItem):
    """Represents the ``match`` attribute in the namespace."""
    __slots__ = ()
    name = "match"

    def __call__(self, n):
        return call(_get_match_group, self, n)

#: the lexicon argument
ARG = _ArgItem()

#: the regular expression match (or None)
MATCH = _MatchItem()

#: the matched text
TEXT = _TextItem()


# these types are not needed anymore
del _ArgItem, _MatchItem, _TextItem


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
    """Classes inheriting RuleItem are allowed in toplevel in rules.

    They are evaluated by the lexicon when a rule matches.

    """
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
            return type(self)(index, *items), 0
        return self, 0      # nothing changed

    def variations(self):
        """Yield all the items that could be chosen (unevaluated)."""
        yield from self._items

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
            return type(self)((0, arg), lexicon), 0
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
            return type(self)(value, *lexicons), 0
        return self

    def variations(self):
        """Yield our possible variations.

        If the value is evaluated, yield either the value or the chosen
        lexicon. If not, yields ``a_number`` and all lexicons items.

        """
        value = self._value
        if isinstance(value, Item):
            yield a_number
            yield from self._lexicons
        elif isinstance(value, int):
            yield value
        else:
            index, arg = value
            yield self._lexicons[index]

    def _repr_args(self):
        return (self._value, *self._lexicons)


class PostponedItem(Item):
    """Mixin base class for items that keep alive after the Lexicon.

    When inheriting from this class, implement the :meth:`evaluate_items`
    method, which lists all values as they were given to the __init__ method.

    """
    __slots__ = ()

    def evaluate(self, ns):
        """Evaluate all values yielded by the evaluate_items() method.

        If any value changes, a copy of the Item is returned, otherwise the
        Item ifself. If the evaluate_items() method does not yield any value,
        this Item is always returned unchanged.

        """
        items, found = [], 0
        for item in self.evaluate_items():
            if evaluate and isinstance(item, Item):
                item = item.evaluate(ns)
                found = 1
            items.append(item)
        if found:
            return type(self)(*items)
        return self

    def pre_evaluate(self, ns):
        """Pre-evaluate all values yielded by the evaluate_items() method.

        If any value changes, a copy of the Item is returned, otherwise the
        Item ifself.

        """
        items, found = [], []
        for item in self.evaluate_items():
            if isinstance(item, Item):
                item, ok = item.pre_evaluate(ns)
                found.append(ok)
            items.append(item)
        if any(found):
            return type(self)(*items), int(all(found))
        return self, 0 if found else 1

    def evaluate_items(self):
        """Yield the current values as they are given to the __init__ method.

        This method should either yield *all( values that were given to the
        __init__ method, or nothing. The default implementation yields nothing,
        so nothing is evaluated or pre-evaluated.

        """
        return
        yield


class ActionItem(PostponedItem):
    """Mixin base class for dynamic actions."""
    __slots__ = ()


class pattern(PostponedItem):
    """Represents a pattern.

    This evaluates its value, but remains alive after building the rule.

    """
    __slots__ = ('_value',)

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        """Get the pattern value."""
        return self._value

    def evaluate_items(self):
        """Yield the pattern value."""
        yield self._value

    def variations(self):
        """If the value is evaluated, yield it, otherwise yields ``None`` and ``a_string``."""
        if isinstance(self._value, Item):
            yield None
            yield a_string
        else:
            yield self._value

    def _repr_args(self):
        return self._value,


# helper function used for Item.__getitem__
def _get_item(text, n):
    return text[n]


# helper function to get the match group in MatchItem.__call__
def _get_match_group(match, n):
    # lastindex is always the index of the lexicon's match
    return match.group(match.lastindex + n)


def pre_evaluate_rule(rule, arg):
    """Pre-evaluates items in the rule with the 'arg' variable.

    Unrolls lists. Returns the rule as a tuple.

    """
    ns = {'arg': arg}
    def items():
        for item in rule:
            if isinstance(item, Item):
                item = item.pre_evaluate(ns)[0]
            yield from unroll(item)
    result = items()
    # the first item may be a pattern instance; it should be evaluated by now
    for item in result:
        if isinstance(item, pattern):
            item = item.value
        return (item,) + tuple(result)
    return ()


def evaluate_rule(rule, match):
    """Yield all items of the rule, evaluating leftover Items, unrolling list or tuple results."""
    ns = {'text': match.group(), 'match': match}
    for item in rule:
        if isinstance(item, RuleItem):
            item = item.evaluate(ns)
            yield from unroll(item)
        else:
            yield item


def needs_evaluation(rule):
    """Return True if there are items in the rule that need evaluating."""
    return any(isinstance(item, RuleItem) for item in rule)


def variations_tree(rule):
    """Return a tuple with the tree structure of all possible variations.

    Branches (choices) are indicated by a frozenset, which contains
    zero or more tuples.

    """
    items = tuple(rule)
    for i, item in enumerate(items):
        if isinstance(item, Item):
            branch = frozenset(variations_tree(unroll(v)) for v in item.variations())
            return (*items[:i], branch, *variations_tree(items[i+1:]))
    else:
        return items


def variations(rule):
    """Yield all possible variations of the rule."""
    items = tuple(rule)
    for i, item in enumerate(items):
        if isinstance(item, Item):
            prefix = items[:i]
            for suffix in variations(items[i+1:]):
                for v in item.variations():
                    for l in variations(unroll(v)):
                        yield prefix + l + suffix
            break
    else:
        yield items


def unroll(obj):
    """Yield the obj.

    If the obj is a tuple or list, yields their members separately.

    """
    if isinstance(obj, (tuple, list)):
        yield from obj
    else:
        yield obj


#: sentinel denoting that a variation is any integer
a_number = util.Symbol("a_number")

#: sentinel denoting that a variation is any string
a_string = util.Symbol("a_string")

