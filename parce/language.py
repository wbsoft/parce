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
This module provides the Language class, which serves as the base class
for all language definitions.

Additionally, there are some utility functions to manage and query built-in
language definitions.

"""

import importlib
import glob
import os

import parce
import parce.lang
from parce.action import StandardAction
from parce.rule import DynamicItem
from parce.lexicon import LexiconDescriptor, Lexicon


class Language:
    """A Language represents a set of Lexicons comprising a specific language.

    A Language is never instantiated. The class itself serves as a namespace
    and can be inherited from.

    """

    @classmethod
    def comment_common(cls):
        """Highlights TODO, XXX and TEMP inside comments using Comment.Alert."""
        yield r"\b(XXX|TODO|TEMP)\b", parce.Comment.Alert
        yield parce.default_action, parce.Comment


def lexicons(lang):
    """Return a list of all the lexicons on the language."""
    lexicons = []
    for key, value in lang.__dict__.items():
        if isinstance(value, LexiconDescriptor):
            lexicons.append(getattr(lang, key))
    return lexicons


def rule_items(lang):
    """Yield all rule items in a language, flattening all DynamicItem instances."""
    def flatten(items):
        for i in items:
            if isinstance(i, DynamicItem):
                for l in i.itemlists:
                    yield from flatten(l)
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


def get_all_modules():
    """Return the sorted list of module names in ``parce.lang``.

    Modules that start with an underscore are skipped.

    """
    names = []
    for filename in glob.glob(os.path.join(parce.lang.__path__[0], "*.py")):
        name = os.path.splitext(os.path.basename(filename))[0]
        if not name.startswith('_'):
            names.append(name)
    names.sort()
    return names


def get_languages(name):
    """Yield the Language subclasses defined in the module ``name``.

    The module name must be one of the modules returned by
    :meth:``get_all_modules``.

    """
    modname = 'parce.lang.' + name
    mod = importlib.import_module(modname)
    for name, obj in mod.__dict__.items():
        if (isinstance(obj, type) and issubclass(obj, parce.Language)
               and obj is not parce.Language and obj.__module__ == modname):
            yield obj


def get_all_languages():
    """Import all modules in ``parce.lang`` and yield all defined classes
    that inherit from :class:`Language`.

    """
    for name in get_all_modules():
        yield from get_languages(name)


