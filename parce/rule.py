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


class DynamicRuleItem(DynamicItem):
    """Base class for items that are already replaced by the lexicon."""
    def __init__(self, predicate, *itemlists):
        self.predicate = predicate
        self.itemlists = [i if isinstance(i, (tuple, list)) else (i,)
                          for i in itemlists]

    def replace(self, text, match):
        """Return one of the itemlists.

        Based on either text or match (depending on implementation) one
        is chosen.

        """
        raise NotImplementedError()


class ArgRuleItem(DynamicRuleItem):
    """Chooses the itemlist based on a predicate that gets the lexicon argument.

    This rule item is handled once, before parsing.

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


class LexiconWithText(DynamicRuleItem):
    """Return a LexiconVariant by calling a Lexicon with an argument.

    The argument is the text of the specified match group, optionally
    mapped by a specified mapping. When the text is not in the mapping,
    the argument is set to None, so that the vanilla lexicon is returned.

    """
    def __init__(self, group, lexicon, mapping=None):
        self.group = group
        self.itemlists = [[lexicon]]
        self.mapping = mapping

    def replace(self, text, match):
        arg = match.group(self.group)
        if self.mapping:
            arg = self.mapping.get(arg)
        return self.itemlists[0][0](arg),

