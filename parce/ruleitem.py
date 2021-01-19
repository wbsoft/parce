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
This module contains the implementation of the replacable rule item objects,
and some functions to query and manipulate rules that are used by the Lexicon.

Normally, you don't need this module directly; use the :mod:`~parce.rule`
module for your language definitions.

"""

import operator

from . import util


# pre_evaluate flags
_CHANGED = 0
_COMPLETE = 1
_UNCHANGED = 2


class _EvaluationError(RuntimeError):
    """Raised when an attribute is missing in the evaluation namespace."""
    pass


class Item:
    """Base class for any replacable rule item.

    An Item is considered to be immutable; you should never alter the
    attributes after instantiation. When an Item can be partly pre-evaluated a
    copy must be returned by calling ``type(self)(*args)``.

    In some cases you can also return a different Item type when pre-evaluating
    partly succeeds. For example, the :class:`select` type simply returns the
    chosen item if the index already can be evaluated, without evaluating the
    other items.

    """
    __slots__ = ()
    _getitem_func = operator.getitem

    def __getitem__(self, n):
        """Return a new Item that performs item[n]. n is evaluated as well."""
        return call(self._getitem_func, self, n)

    def evaluate(self, ns):
        """Evaluate item in namespace dict ``ns``."""
        raise NotImplementedError

    def pre_evaluate(self, ns):
        """Try to evaluate item in namespace dict ``ns``.

        Return a two-tuple(obj, success).

        Success is a two-bit value indicating whether the result is completely
        evaluated and whether something has changed. Bit 0 is set when the item
        is completely evaluated, and bit 1 is set when there was no
        modification. So all possible return values are:

        | 0: the object has changed but it is not yet completely evaluated
        | 1: the object has changed and now it is fully evaluated
        | 2: the object needs evaluation but is not changed

        Specific items may reimplement this method to return partially
        evaluated items.

        """
        try:
            return self.evaluate(ns), _COMPLETE
        except _EvaluationError:
            return self, _UNCHANGED

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


class VariableItem(Item):
    """A named variable that's accessed in the namespace.

    If a getitem_func is given, it is called when this item is accessed using
    the item syntax ``[n]``, with this item as first argument, and then the
    specified index.

    """
    __slots__ = ('_name', '_getitem_func')
    def __init__(self, name, getitem_func=operator.getitem):
        self._name = name
        self._getitem_func = getitem_func

    def evaluate(self, ns):
        """Get the variable from the namespace dict."""
        try:
            return ns[self._name]
        except KeyError as e:
            raise _EvaluationError("Can't find variable '{}'".format(self._name)) from e

    def __repr__(self):
        return self._name.upper()


class call(Item):
    """Call predicate with arguments."""
    __slots__ = ('_predicate', '_arguments')
    def __init__(self, predicate, *arguments):
        self._predicate = predicate
        self._arguments = arguments

    def evaluate(self, ns):
        """Call predicate with the arguments."""
        predicate = evaluate(self._predicate, ns)
        arguments = evaluate(self._arguments, ns)
        return predicate(*arguments)

    def pre_evaluate(self, ns):
        """Optimize by pre-evaluating what can be pre-evaluated."""
        predicate, pred_ok = pre_evaluate(self._predicate, ns)
        arguments, arg_ok  = pre_evaluate(self._arguments, ns)
        ok = pred_ok & arg_ok
        if ok & _COMPLETE:
            return predicate(*arguments), _COMPLETE
        if ok & _UNCHANGED:
            return self, _UNCHANGED
        return type(self)(predicate, *arguments), _CHANGED

    def _repr_args(self):
        return (self._predicate, *self._arguments)


class RuleItem(Item):
    """Classes inheriting RuleItem are allowed in toplevel in rules.

    They are evaluated by the lexicon when a rule matches.

    """
    __slots__ = ()


class select(RuleItem):
    """Chooses one of the items.

    If an item is a list, it is unrolled when replacing the item in a rule.

    """
    __slots__ = ('_index', '_items')

    def __init__(self, index, *items):
        self._index = index
        self._items = items

    def evaluate(self, ns):
        """Return items[index]."""
        index = evaluate(self._index, ns)
        item = evaluate(self._items[index], ns)
        return item

    def pre_evaluate(self, ns):
        """Optimize by pre-evaluating what can be pre-evaluated."""
        index, ok = pre_evaluate(self._index, ns)
        if ok & _COMPLETE:
            item, ok = pre_evaluate(self._items[index], ns)
            return item, ok & _COMPLETE     # mask unchanged state
        items, items_ok = pre_evaluate(self._items, ns)
        ok &= items_ok
        if ok & _UNCHANGED:
            return self, _UNCHANGED
        return type(self)(index, *items), _CHANGED

    def variations(self):
        """Yield all the items that could be chosen (unevaluated)."""
        yield from self._items

    def _repr_args(self):
        return (self._index, *self._items)


class target(RuleItem):
    """target(value, *lexicons)

    Has a special handling: if the value is an integer, it is used as the
    result value (to push/pop contexts).

    If it is a two-tuple(index, argument): The index points to the lexicon and
    the argument is used as lexicon argument.

    """
    __slots__ = ('_value', '_lexicons')

    def __init__(self, value, *lexicons):
        self._value = value
        self._lexicons = lexicons

    def evaluate(self, ns):
        """Return value if integer, otherwise lexicons[value[0]](value[1])."""
        value = evaluate(self._value, ns)
        if isinstance(value, int):
            return value
        index, arg = value
        lexicon = evaluate(self._lexicons[index], ns)
        return lexicon if arg is None else lexicon(arg)

    def pre_evaluate(self, ns):
        """Optimize by pre-evaluating what can be pre-evaluated."""
        value, ok = pre_evaluate(self._value, ns)
        if ok & _COMPLETE:
            if isinstance(value, int):
                return value, _COMPLETE
            index, arg = value
            lexicon, ok = pre_evaluate(self._lexicons[index], ns)
            if ok & _COMPLETE:
                return (lexicon if arg is None else lexicon(arg), _COMPLETE)
            return type(self)((0, arg), lexicon), _CHANGED
        # pre-evaluate the lexicons
        lexicons, l_ok = pre_evaluate(self._lexicons, ns)
        ok &= l_ok
        if ok & _UNCHANGED:
            return self, ok
        return type(self)(value, *lexicons), ok

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


class PostponedItem(RuleItem):
    """Mixin base class for items that keep alive after the Lexicon.

    When inheriting from this class, implement the :meth:`evaluate_items`
    method, which lists all values as they were given to the __init__ method.

    If this method returns values, those are evaluated, and a new PostponedItem
    is returned with the contents evaluated.

    """
    __slots__ = ()

    def evaluate(self, ns):
        """Evaluate all values returned by the evaluate_items() method.

        If any value changes, a copy of the Item is returned, otherwise the
        Item ifself. If the evaluate_items() method does not yield any value,
        this Item is always returned unchanged.

        """
        items, ok = pre_evaluate(self.evaluate_items(), ns)
        return self if ok & _UNCHANGED else type(self)(*items)

    def pre_evaluate(self, ns):
        """Pre-evaluate all values returned by the evaluate_items() method.

        If any value changes, a copy of the Item is returned, otherwise the
        Item ifself.

        """
        items, ok = pre_evaluate(self.evaluate_items(), ns)
        return self if ok & _UNCHANGED else type(self)(*items), ok

    def evaluate_items(self):
        """Return a tuple of the values as given to the __init__ method,
        when they need to be evaluated inside this PostponedItem.

        This method should either yield *all* values that were given to the
        __init__ method, or nothing. The default implementation yields nothing,
        so nothing is evaluated or pre-evaluated.

        """
        return ()


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
        return self._value,

    def variations(self):
        """If the value is evaluated, yield it, otherwise yields ``None`` and ``a_string``."""
        if isinstance(self._value, Item):
            yield None
            yield a_string
        else:
            yield self._value

    def _repr_args(self):
        return self._value,


class ActionItem(PostponedItem):
    """Mixin base class for dynamic actions."""
    __slots__ = ()


class SubgroupAction(ActionItem):
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
    __slots__ = ('_actions',)
    def __init__(self, *actions):
        self._actions = actions

    def replace(self, lexer, pos, text, match):
        for i, action in enumerate(self._actions, match.lastindex + 1):
            yield from lexer.filter_actions(action, match.start(i), match.group(i), match)

    def variations(self):
        """Yield the possible actions."""
        yield from self._actions

    def _repr_args(self):
        return self._actions


class DelegateAction(ActionItem):
    """This action uses a lexicon to parse the text.

    All tokens are yielded as one group, flattened, ignoring the tree
    structure, so this is not efficient for large portions of text, as the
    whole region is parsed again on every modification.

    But it can be useful when you want to match a not too large text blob first
    that's difficult to capture otherwise, and then lex it with a lexicon that
    does (almost) not enter other lexicons.

    """
    __slots__ = ('_lexicon',)

    def __init__(self, lexicon):
        self._lexicon = lexicon

    def replace(self, lexer, pos, text, match):
        """Use our lexicon to parse the matched text."""
        sublexer = type(lexer)([self._lexicon])
        for e in sublexer.events(text):
            for p, txt, action in e.lexemes:
                yield pos + p, txt, action

    def evaluate_items(self):
        """Return the lexicon specified on init, used by evaluate() and pre_evaluate()."""
        return self._lexicon,

    def variations(self):
        """Yield our lexicon."""
        yield self._lexicon

    def _repr_args(self):
        return self._lexicon,


class SkipAction(ActionItem):
    """A DynamicAction that yields nothing.

    A SkipAction() is stored in the module variable ``skip`` and causes the rule
    to silently ignore the matched text.

    """
    def replace(self, lexer, pos, text, match):
        yield from ()

    def variations(self):
        """Yield no variations."""
        return
        yield


def evaluate(obj, ns):
    """Evaluate an object, that may or may not be an Item.

    The namespace `ns` is a dictionary containing text, match and/or arg
    variables. A list or a tuple of items is also evaluated and always becomes
    a tuple.

    """
    if isinstance(obj, Item):
        return obj.evaluate(ns)
    if type(obj) in (list, tuple):
        return tuple(evaluate(o, ns) for o in obj)
    return obj


def evaluate_rule(rule, match):
    """Evaluate all RuleItem objects in the rule.

    The specified match object provides the value for the TEXT and MATCH
    variables. Lists and tuples are unrolled.

    """
    ns = {'text': match.group(), 'match': match}
    def eval_rule_items(objs):
        for obj in objs:
            if isinstance(obj, RuleItem):
                yield from unroll(obj.evaluate(ns))
            elif type(obj) in (list, tuple):
                yield from eval_rule_items(obj)
            else:
                yield obj
    yield from eval_rule_items(rule)


def pre_evaluate(obj, ns):
    """Pre-evaluate any object, that may or may not be an Item.

    Returns a two-tuple(result, success). The namespace `ns` is a dictionary
    containing text, match and/or arg variables.

    * If the object is an Item, returns ``object.pre_evaluate(ns)``.
    * If the object is a list or tuple, evaluates the contents and returns a
      tuple.
    * If the object is none of the above, simply returns the object unchanged.

    The ``success`` value can be one of the values described in
    :meth:`Item.pre_evaluate`, or it is 3, meaning that the object is returned
    unchanged and needs no evaluation.

    """
    if isinstance(obj, Item):
        return obj.pre_evaluate(ns)
    if type(obj) in (list, tuple):
        objs, success  = [], 3
        for o in obj:
            res, ok = pre_evaluate(o, ns)
            objs.append(res)
            success &= ok
        return tuple(objs), success
    return obj, 3


def pre_evaluate_rule(rule, arg):
    """Evaluate all RuleItem objects that can be evaluated in the rule.

    The specified ``arg`` provides the value for the ARG variable. Rule items
    that depend on the match object are not yet evaluated. Lists and tuples are
    unrolled. Returns the rule as a tuple.

    """
    ns = {'arg': arg}
    def pre_eval_rule_items(objs):
        for obj in objs:
            if isinstance(obj, RuleItem):
                yield from unroll(obj.pre_evaluate(ns)[0])
            elif type(obj) in (list, tuple):
                yield from pre_eval_rule_items(obj)
            else:
                yield obj
    result = pre_eval_rule_items(rule)
    # the first item may be a pattern instance; it should be evaluated by now
    for item in result:
        if isinstance(item, pattern):
            item = item.value
        return (item,) + tuple(result)
    return ()


def needs_evaluation(rule):
    """Return True if there are items in the rule that need evaluating."""
    for item in rule:
        if isinstance(item, PostponedItem):
            if needs_evaluation(item.evaluate_items()):
                return True
        elif isinstance(item, RuleItem) or \
             (type(item) in (tuple, list) and needs_evaluation(item)):
            return True
    return False


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
    """Unroll a tuple or list.

    If the object is a tuple or list, yields the unrolled members recursively.
    Otherwise just the object itself is yielded.

    """
    if type(obj) in (tuple, list):
        for i in obj:
            yield from unroll(i)
    else:
        yield obj


#: sentinel denoting that a variation is any integer
a_number = util.Symbol("a_number")

#: sentinel denoting that a variation is any string
a_string = util.Symbol("a_string")

