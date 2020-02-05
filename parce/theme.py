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

By default, the properties are read from a normal CSS (Cascading StyleSheets)
file, although other storage backends could be devised.

Theme provides CSS properties for standard actions, and MetaTheme does
the same, but can have a sub-Theme for every Language.

In the ``themes/`` directory are bundled CSS themes that can be used.
Instantiate a bundled theme with::

    >>> from parce.theme import Theme
    >>> th = Theme.byname("default")

To use a custom CSS theme file, load it using::

    >>> th = Theme('/path/to/my/custom.css')

Get the CSS properties for an action, use e.g.::

    >>> props = th.properties(String)
    >>> props
    {'color': [<Value color='#c00000'>]}

A property value is a list of :py:class:`Value <parce.css.Value>` instances.
As CSS colors can be specified in many different ways, you can call
get_color() to get the color values in (r, g, b, a) format.


Mapping actions to CSS classes
------------------------------

Standard actions are mapped to a tuple of classes: the action itself and
the actions it descends from. All CSS rules are combined, the one with
the most matches comes first.

For example, Comment maps to the "comment" CSS class, and Number maps
to ("literal", "number") because Number is a descendant action of Literal.

Some actions might have the same name, e.g. Escape and String.Escape.
Both match CSS rules with the ``.escape`` class selector, but a rule
with ``.string.escape`` will have higher precedence.

The order of the action names does not matter. E.g. an action Text.Comment
will match exactly the same CSS rules as an action Comment.Text. So you
should take some care when designing you action hierachy and not add too much
base action types.

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
    def byname(cls, name="default"):
        """Create Theme by name, that should reside in the themes/ directory."""
        return cls(themes.filename(name))

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


