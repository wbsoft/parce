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

This module holds a few simple replacable objects that can be put in a rule
and are replaced by other objects depending on the match object of the matched
rule's pattern.

When in a pattern rule an object that inherits from ``DynamicRuleItem`` is
encountered, its ``bymatch()`` method is called with the match object, which
should return a list of items the DynamicRuleItem should be replaced with. This
list is again checked for DynamicRuleItem objects,

In most cases a DynamicRuleItem will be instantiated with a predicate and lists
of replacement objects. The predicate should return an integer index value (or
True or False, which count as 1 and 0, respectively), which determines the list
of replacement values to use.

"""


class DynamicItem:
    """Base class for all items from rules that are replaced."""
    def __init__(self, *itemlists):
        self.itemlists = [i if isinstance(i, (tuple, list)) else (i,)
                          for i in itemlists]

    def replace(self, *args):
        """Return one of the itemlists.

        Based on text, match or arg (depending on implementation) one or more
        are chosen.

        """
        raise NotImplementedError()


class DynamicRuleItem(DynamicItem):
    """Base class for items that are already replaced by the lexicon."""
    def __init__(self, predicate, *itemlists):
        self.predicate = predicate
        super().__init__(*itemlists)


class ArgRuleItem(DynamicRuleItem):
    """Chooses the itemlist based on a predicate that gets the lexicon argument.

    This rule item type is handled once, before parsing.

    """
    def replace(self, arg):
        """Return one of the itemlists.

        The predicate is called with the lexicon argument, and should return
        the index of the itemlist to choose.

        """
        index = self.predicate(arg)
        return self.itemlists[index]


class TextRuleItem(DynamicRuleItem):
    """Calls the predicate with the matched text.

    The predicate should return the index of the itemlists to return.
    The preferred way to create a TextRuleItem is using the
    :func:`parce.bytext` function.

    """
    def replace(self, text, match):
        index = self.predicate(text)
        return self.itemlists[index]


class MatchRuleItem(DynamicRuleItem):
    """Calls the predicate with the match object.

    The predicate should return the index of the itemlists to return.
    The preferred way to create a MatchRuleItem is using the
    :func:`parce.bymatch` function.

    """
    def replace(self, text, match):
        index = self.predicate(match)
        return self.itemlists[index]


class LexiconMatchRuleItem(DynamicRuleItem):
    """Return a derived Lexicon using the result of a predicate.

    The predicate is called with the match object. The lexicon is the called
    with the result of the predicate, yielding a derived Lexicon. The lexicon
    is the first item in the first itemlist, there should not be other items.

    """
    def replace(self, text, match):
        """Yield the derived lexicon with the result of predicate(match)."""
        result = self.predicate(match)
        return self.itemlists[0][0](result),


class LexiconTextRuleItem(DynamicRuleItem):
    """Return a derived Lexicon using the result of a predicate.

    The predicate is called with the matched text. The lexicon is the called
    with the result of the predicate, yielding a derived Lexicon. The lexicon
    is the first item in the first itemlist, there should not be other items.

    """
    def replace(self, text, match):
        """Yield the derived lexicon with the result of predicate(text)."""
        result = self.predicate(text)
        return self.itemlists[0][0](result),


class LexiconWithArg(ArgRuleItem):
    """Return a derived Lexicon with the same argument as the current Lexicon.

    The lexicon is the first item in the first itemlist, there should not be
    other items.

    """
    def replace(self, arg):
        """Yield the derived Lexicon with the same argument as the current Lexicon."""
        return self.itemlists[0][0](arg),


def variations(rule):
    """Yield lists with all possible variations on the rule.

    Every DynamicRuleItem is recursively replaced with all of its alternatives.
    Note that DynamicAction is a DynamicItem subclass, and that is not
    unfolded.

    """
    items = list(rule)
    for i, item in enumerate(items):
        if isinstance(item, DynamicRuleItem):
            prefix = items[:i]
            for suffix in variations(items[i+1:]):
                for itemlist in item.itemlists:
                    for l in variations(itemlist):
                        yield prefix + l + suffix
            break
    else:
        yield items


