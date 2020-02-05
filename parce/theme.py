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
This module provides the Theme class, which provides text formatting
properties based on the action (standard action) of a Token.

These properties can be used to colorize text according to a language
definition.

By default, the properties are read from a normal CSS file, although
other storage backends could be devised.

Theme provides CSS properties for standard actions, and MetaTheme does
the same, but can have a sub-Theme for every Language.

"""


import functools
import os

from . import themes
from . import css
from . import util


class Theme:
    def __init__(self, filename):
        """Instantiate Theme from a CSS file."""
        self.style = css.StyleSheet.from_file(filename).style

    @classmethod
    def byname(cls, name):
        """Create Theme by name, that should reside in the themes/ directory."""
        return cls(os.path.join(themes.__path__[0], name + '.css'))

    @functools.lru_cache()
    def properties(self, action):
        """Return the CSS properties for the specified action."""
        classes = css_classes(action)
        return self.style.select_class(*classes).properties()

    def property_ranges(self, tokens):
        """Yield three-tuples (pos, end, properties) from tokens.

        properties is a non-empty dictionary (empty dicts are skipped) with
        CSS properties.

        """
        for pos, end, action in util.merge_adjacent_actions(tokens):
            properties = self.properties(action)
            if properties:
                yield pos, end, properties


class MetaTheme(Theme):
    """A special Theme that can have sub-themes per-language.

    If a language was not added, the own properties are used.

    """
    def __init__(self, name):
        super().__init__(name)
        self.styles = {}

    def add_language(self, language, theme):
        """Add a Theme for the specified language."""
        self.styles[language] = theme

    def property_ranges(self, tokens):
        """Reimplemented to return properties from added languages."""
        for pos, end, action, language in \
                    util.merge_adjacent_actions_with_language(tokens):
            theme = self.styles.get(language, self.style)
            properties = style.properties(action)
            if properties:
                yield pos, end, properties


def css_classes(action):
    """Return a tuple of lower-case CSS class names for the specified standard action."""
    return tuple(a._name.lower() for a in action)


