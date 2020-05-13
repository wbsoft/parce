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
Helper functions to inspect and document objects.
"""


from .ruleitem import Item, variations_tree
from .standardaction import StandardAction
from .lexicon import LexiconDescriptor, Lexicon


def decision_tree(lexicon, build=False):
    """Yield all rules of the lexicon, including variations.

    Every rule is a tuple. Items are members of the tuple. A variation (choice)
    is indicated by a frozenset, which again contains tuples. See also
    :func:`parce.rule.variations_tree`.

    If ``build`` is set to True, Pattern objects are built and ArgItem
    instances are replaced.

    """
    rules = lexicon if build else lexicon.descriptor.rules_func(lexicon.language)
    for rule in rules:
        yield variations_tree(rule)


def lexicons(lang):
    """Return a list of all the lexicons on the language."""
    lexicons = []
    for key, value in lang.__dict__.items():
        if isinstance(value, LexiconDescriptor):
            lexicons.append(getattr(lang, key))
    return lexicons


def rule_items(lang):
    """Yield all rule items in a language, flattening all RuleItem instances."""
    def flatten(items):
        for i in items:
            if isinstance(i, Item):
                yield from flatten(i.variations())
            elif type(i) in (list, tuple):
                yield from flatten(i)
            else:
                yield i
    for lexicon in lexicons(lang):
        for rule in lexicon:
            yield from flatten(rule)


def standardactions(lang):
    """Return the set of all the StandardAction instances in the language.

    Does not follow targets to other languages.

    """
    return set(i for i in rule_items(lang) if isinstance(i, StandardAction))


def languages(lang):
    """Return the set of all languages that this language refers to.

    Does not follow targets from languages that are referred to.

    """
    return set(i.language
        for i in rule_items(lang)
            if isinstance(i, Lexicon) and i.language is not lang)



