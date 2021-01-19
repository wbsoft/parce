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
from parce.action import Comment


class _LanguageType(type):
    """Language meta type that prints a customized repr string."""
    def __repr__(cls):
        return '{}.{}'.format(cls.__module__, cls.__name__)


class Language(metaclass=_LanguageType):
    """A Language represents a set of Lexicons comprising a specific language.

    A Language is never instantiated. The class itself serves as a namespace
    and can be inherited from.

    """

    @classmethod
    def comment_common(cls):
        """Provides subtle highlighting within comments.

        The default implementation highlights words like TODO, XXX, TEMP, etc.
        using Comment.Alert, and highlights URLs and email addresses with the
        Comment.Url and Comment.Email action respectively. Most bundled
        languages use this method for their comment lexicons.

        """
        yield r'\b\w+(?:[._%+-]\w+)*@\w+(?:[._-]\w+)*\b', Comment.Email
        yield r'(?:(?:https?|ftp):/|\bwww\.)(?:[\w_~:/#-]+([.?=][\w_~:/#-]+)*|\([\w._~:?/#-]*\))+', Comment.Url
        yield r"\b(ALERT|BUG|FIXME|TEMP|TODO|XXX+)\b", Comment.Alert
        yield parce.default_action, Comment


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
               and not obj.__name__.startswith('_')
               and obj is not parce.Language and obj.__module__ == modname):
            yield obj


def get_all_languages():
    """Import all modules in ``parce.lang`` and yield all defined classes
    that inherit from :class:`Language`.

    """
    for name in get_all_modules():
        yield from get_languages(name)


