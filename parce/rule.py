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

A normal rule consists of a pattern, action and zero or more targets.

An action may be any object, a target is either an integer or a lexicon. The
lexicon may be a derived lexicon (i.e. created by calling a vanilla lexicon
with an argument).

This module defines some classes for replacable rule item objects, which can
be used in a rule, and which generate other objects, ultimately resulting in a
normal rule.

These replacable objects can be used to define actions and targets. (For
generated patterns, the :class:`~parce.pattern.Pattern` class from the
:mod:`~parce.pattern` module must be used.)

There are four moments when replaceable rule items are processed:

1. when yielding the rules of the lexicon, in the
   :meth:`~parce.lexicon.__iter__` method of :class:`~parce.lexicon.Lexicon`.

   At this stage, :class:`ArgItem` instances are replaced, by calling their
   ``replace()`` method with the lexicon argument (which is None for a vanilla
   lexicon).

2. when constructing the :meth:`parse` method of the Lexicon, just before
   the first parsing. At this stage, :class:`~parce.pattern.Pattern` objects
   are built by the lexicon.

3. while parsing, when a rule's pattern matches the text. At this moment,
   :class:`DynamicItem` instances are replaced by calling their ``replace()``
   method with both the matched text and the match object (if available).

4. after parsing, :class:`ActionItem` instances are processed. A normal action
   is just paired with the matched text to form a token, but an ActionItem can
   create zero or more tokens, e.g. to match subgroups in a regular expression,
   or to skip some types of text. This is done by the
   :class:`~parce.lexer.Lexer` from the :mod:`~parce.lexer` module.

   When the lexer replaces ``ActionItem`` objects, the replacement objects
   are scanned for ``DynamicItem`` instances as well.

All three Item subclasses, :class:`ArgItem`, :class:`DynamicItem` and
:class:`ActionItem` have their possible replacement objects in their
``itemlists`` attribute. So there are never unexpected objects in a rule, and
rules can always be validated, and e.g. all possible actions can be determined
beforehand.

"""


### abstract base classes

class Item:
    """Abstract base class for all items from rules that are replaced.

    Don't inherit from Item directly; use ArgItem, DynamicItem, or ActionItem.

    """
    def __init__(self, *itemlists):
        self.itemlists = [i if isinstance(i, (tuple, list)) else (i,)
                          for i in itemlists]

    def replace(self, *args):
        """Called to get the replacement."""
        raise NotImplementedError()


class PredicateMixin:
    """Mixin class providing ``predicate`` handling."""
    def __init__(self, predicate, *itemlists):
        super().__init__(*itemlists)
        self.predicate = predicate


class ArgItem(Item):
    """Abstract base class for items replaced before parsing.

    These items are replaced by the Lexicon in the :meth:`__iter__` method,
    when yielding the rules, before constructing the Lexicons's :meth:`parse`
    method.

    """
    def replace(self, arg):
        """Called to get the replacement based on lexicon argument."""
        raise NotImplementedError()


class DynamicItem(Item):
    """Abstract base class for items replaced during parsing.

    These items are replaced by the Lexicon in the :meth:`parse` method.

    """
    def replace(self, text, match):
        """Called to get the replacement based on text and/or match object."""
        raise NotImplementedError()


class ActionItem(Item):
    """Abstract base class for items replaced after parsing.

    :class:`~parce.action.DynamicAction` inherits from this class. Dynamic
    actions are replaced by the lexer. See the :mod:`~parce.lexer` module.

    """


### argument items

class LexiconArgItem(ArgItem):
    """Return a derived Lexicon with the same argument as the current lexicon.

    The lexicon is the first item in the first itemlist, there should not be
    other items.

    """
    def replace(self, arg):
        return self.itemlists[0][0](arg),


class PredicateArgItem(PredicateMixin, ArgItem):
    """Calls the predicate with the lexicon argument.

    The predicate should return the index of the itemlists to return.

    """
    def replace(self, arg):
        index = self.predicate(arg)
        return self.itemlists[index]


### dynamic items

class TextItem(PredicateMixin, DynamicItem):
    """Calls the predicate with the matched text.

    The predicate should return the index of the itemlists to return.

    """
    def replace(self, text, match):
        index = self.predicate(text)
        return self.itemlists[index]


class MatchItem(PredicateMixin, DynamicItem):
    """Calls the predicate with the match object.

    The predicate should return the index of the itemlists to return.

    """
    def replace(self, text, match):
        index = self.predicate(match)
        return self.itemlists[index]


class LexiconTextItem(TextItem):
    """Return a derived Lexicon using the result of a predicate.

    The predicate is called with the matched text. The lexicon is then called
    with the result of the predicate, yielding a derived Lexicon. The lexicon
    is the first item in the first itemlist, there should not be other items.

    """
    def replace(self, text, match):
        """Yield the derived lexicon with the result of predicate(text)."""
        result = self.predicate(text)
        return self.itemlists[0][0](result),


class LexiconMatchItem(MatchItem):
    """Return a derived Lexicon using the result of a predicate.

    The predicate is called with the match object. The lexicon is then called
    with the result of the predicate, yielding a derived Lexicon. The lexicon
    is the first item in the first itemlist, there should not be other items.

    """
    def replace(self, text, match):
        """Yield the derived lexicon with the result of predicate(match)."""
        result = self.predicate(match)
        return self.itemlists[0][0](result),


def variations(rule):
    """Yield lists with all possible variations on the rule.

    Every DynamicItem and every ArgItem is recursively replaced with all of its
    alternatives. Note that DynamicAction is an ActionItem subclass, and that
    is not unfolded.

    """
    items = list(rule)
    for i, item in enumerate(items):
        if isinstance(item, (DynamicItem, ArgItem)):
            prefix = items[:i]
            for suffix in variations(items[i+1:]):
                for itemlist in item.itemlists:
                    for l in variations(itemlist):
                        yield prefix + l + suffix
            break
    else:
        yield items


def variations_tree(rule):
    """Return a tuple with the tree structure of all possible variations.

    Unlike :func:`variations`, this function unfolds *all* Item instances.
    Branches (choices) are indicated by a frozenset, which contains
    one or more tuples.

    A DynamicAction can be recognized as a frozenset with only one member.
    For the SkipAction that member is an empty tuple.

    """
    items = tuple(rule)
    for i, item in enumerate(items):
        if isinstance(item, Item):
            return items[:i] + (
                    frozenset(variations_tree(l) for l in item.itemlists),
                    *variations_tree(items[i+1:]))
    else:
        return items

