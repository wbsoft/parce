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

Normally a rule consists of pattern, action and zero or more target objects,
where the pattern is a regular expression string or a Pattern object; the
action can be any object and the targets are integers or lexicons.

But it is also possible to have replacable rule items, which are then replaced
before the rule is used.

There are three types of replacable rule item objects (all descending from
RuleItem). All items use the ``replace()`` method to do the replacement work,
but in slightly different ways.

``ArgItem``

    These items are replaced by the lexicon when used for the first time,
    before any parsing occurs, in the :meth:`~parce.lexicon.__iter__` method of
    :class:`~parce.lexicon.Lexicon`. The ``replace()`` method is called with
    the lexicon's argument or None. Replacement lists may consist of patterns,
    action and/or targets. (Although ultimately, for a normal rule, the first
    rule item must be the pattern and the second the action or ActionItem.)

``DynamicItem``

    These items are replaced by the lexicon during parsing. The ``replace()``
    method is called with both the matched text and the match object (if
    available).

``ActionItem``

    These items are replaced by the lexer, after parsing. The ``replace()``
    method is called with lexer, position, text and match values and should
    yield (pos, text, action) tuples to create tokens from.

``DynamicItem`` and ``ActionItem`` must have their possible replacement values
in lists in their ``itemlists`` atttribute. These attributes are scanned before
the items are used in parsing, and so all ``ArgItem`` instances that are in the
itemlists are replaced as soon as a Lexicon is used for the first time.

And when the lexer replaces ``ActionItem`` objects, the replacement objects
are scanned for Dynamic items as well.

Most dynamic and action item types then use a predicate function that returns
the index of the ``itemlists`` to choose.

"""


### abstract base classes

class Item:
    """Abstract base class for all items from rules that are replaced.

    Don't inherit from Item directly; use ArgItem, DynamicItem, or ActionItem.

    """
    def replace(self, *args):
        """Called to get the replacement."""
        raise NotImplementedError()


class ItemListMixin:
    """Mixin class providing ``itemlists`` handling."""
    def __init__(self, *itemlists):
        self.itemlists = [i if isinstance(i, (tuple, list)) else (i,)
                          for i in itemlists]


class PredicateItemListMixin(ItemListMixin):
    """Mixin class providing ``predicate`` and ``itemlists`` handling."""
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


class DynamicItem(ItemListMixin, Item):
    """Abstract base class for items replaced during parsing.

    These items are replaced by the Lexicon in the :meth:`parse` method.

    """
    def replace(self, text, match):
        """Called to get the replacement based on text and/or match object."""
        raise NotImplementedError()


class ActionItem(ItemListMixin, Item):
    """Abstract base class for items replaced after parsing.

    :class:`~parce.action.DynamicAction` inherits from this class. Dynamic
    actions are replaced by the lexer. See the :mod:`~parce.lexer` module.

    """


### argument items

class PredArgItem(PredicateItemListMixin, ArgItem):
    """Chooses the itemlist based on a predicate that gets the lexicon argument."""
    def replace(self, arg):
        """Return one of the itemlists.

        The predicate is called with the lexicon argument, and should return
        the index of the itemlist to choose.

        """
        index = self.predicate(arg)
        return self.itemlists[index]


class LexiconWithArg(ArgItem):
    """Return a derived Lexicon with the same argument as the current Lexicon."""
    def __init__(self, lexicon):
        self.lexicon = lexicon

    def replace(self, arg):
        """Yield the derived Lexicon with the same argument as the current Lexicon."""
        return self.lexicon(arg),


### dynamic items

class TextItem(PredicateItemListMixin, DynamicItem):
    """Calls the predicate with the matched text.

    The predicate should return the index of the itemlists to return.
    The preferred way to create a TextItem is using the
    :func:`parce.bytext` function.

    """
    def replace(self, text, match):
        index = self.predicate(text)
        return self.itemlists[index]


class MatchItem(PredicateItemListMixin, DynamicItem):
    """Calls the predicate with the match object.

    The predicate should return the index of the itemlists to return.
    The preferred way to create a MatchItem is using the
    :func:`parce.bymatch` function.

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

    Every DynamicItem is recursively replaced with all of its alternatives.
    Note that DynamicAction is an ActionItem subclass, and that is not
    unfolded.

    """
    items = list(rule)
    for i, item in enumerate(items):
        if isinstance(item, DynamicItem):
            prefix = items[:i]
            for suffix in variations(items[i+1:]):
                for itemlist in item.itemlists:
                    for l in variations(itemlist):
                        yield prefix + l + suffix
            break
    else:
        yield items


