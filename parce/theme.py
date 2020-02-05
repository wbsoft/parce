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


Using MetaTheme
---------------

A MetaTheme works just like a normal Theme, reading its style properties from
a CSS file.

But MetaTheme has a special method ``add_language()`` to add a language class
with its own Theme. The actual theme to use is then chosen based on the lexicon
of the token's Context, so each language can have its own color scheme.

If a certain language is not added, the MetaTheme's own properties are used.

For example::

    th = MetaTheme.byname('default')     # use the formats from 'default.css'
    th.add_language(parce.lang.xml.Xml, Theme("my_funky_xml.css"))

Tokens that originate from lexicons from the Xml language then use the colors
or text formats from my_funky_xml.css, while other tokens are shown in the
colors of the default stylesheet.

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
    def default(self):
        """Return the default textformat properties.

        Those are intended to be used for the editor window or encompassing DIV
        element.

        """
        e = css.Element(class_="parce")
        return self.style.select_element(e).properties()

    @functools.lru_cache()
    def selection(self):
        """Return the default textformat properties for selected text.

        Those are intended to be used for the editor window or encompassing DIV
        element.

        """
        e = css.Element(class_="parce", pseudo_elements=["selection"])
        return self.style.select_element(e).properties()

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
        self.themes = {}

    def add_language(self, language, theme):
        """Add a Theme for the specified language."""
        self.themes[language] = theme

    def property_ranges(self, tokens):
        """Reimplemented to return properties from added languages."""
        for pos, end, action, language in \
                    util.merge_adjacent_actions_with_language(tokens):
            theme = self.themes.get(language, self)
            properties = theme.properties(action)
            if properties:
                yield pos, end, properties


_dispatch = {}
class TextFormat:
    """Simple textformat that reads CSS properties and supports a subset of those."""
    color = None
    background_color = None
    text_decoration_color = None
    text_decoration_line = ()
    text_decoration_style = None
    font_family = ()
    font_size = None
    font_size_unit = None
    font_style = None
    font_style_angle = None
    font_style_angle_unit = None
    font_variant_caps = None
    font_variant_position = None
    font_weight = None


    def at(*propnames):
        def decorator(func):
            for p in propnames:
                _dispatch[p] = func
            return func
        return decorator

    def __init__(self, properties):
        for prop, values in properties.items():
            meth = self._dispatch.get(prop)
            if meth:
                meth(self, values)

    @at("color")
    def read_color(self, values):
        for v in values:
            c = v.get_color()
            if c:
                self.color = c
                return

    @at("background-color")
    def read_background_color(self, values):
        for v in values:
            c = v.get_color()
            if c:
                self.background_color = c
                return

    @at("background")
    def read_background(self, values):
        self.read_background_color(values)

    @at("text-decoration-color")
    def read_text_decoration_color(self, values):
        for v in values:
            c = v.get_color()
            if c:
                self.text_decoration_color = c
                return

    @at("text-decoration-line")
    def read_text_decoration_line(self, values):
        decos = []
        for v in values:
            if v.text in ("underline", "overline", "line-through"):
                decos.append(v.text)
            elif v.text == "none":
                decos.clear()
        self.text_decoration_line = decos

    @at("text-decoration-style")
    def read_text_decoration_style(self, values):
        for v in values:
            if v.text in ("solid", "double", "dotted", "dashed", "wavy"):
                self.text_decoration_style = v.text
                return

    @at("text-decoration")
    def read_text_decoration(self, values):
        self.read_text_decoration_color(values)
        self.read_text_decoration_line(values)
        self.read_text_decoration_style(values)

    @at("font-family")
    def read_font_family(self, values):
        families = []
        for v in values:
            if v.text and (v.quoted or v.text in (
                "serif",
                "sans-serif",
                "monospace",
                "cursive",
                "fantasy",
                "system-ui",
                "math",
                "emoji",
                "fangsong",
            )):
                families.append(v.text)
        self.font_family = families

    @at("font-kerning")
    def read_font_kerning(self, values):
        for v in values:
            if v.text in ("auto", "normal", "none"):
                self.font_kerning = v.text
                return

    @at("font-size")
    def read_font_size(self, values):
        for v in values:
            if v.text in ("xx-small", "x-small", "small", "medium",
                          "large", "x-large", "xx-large", "xxx-large",
                          "larger", "smaller"):
                self.font_size = v.text
                return
            elif v.number is not None:
                self.font_size = v.number
                self.font_size_unit = v.unit
                return

    @at("font-style")
    def read_font_style(self, values):
        for v in values:
            if v.text in ("normal", "italic"):
                self.font_style = v.text
                return
            elif v.text == "oblique":
                self.font_style = v.text
            elif v.number is not None:
                if self.font_style == "oblique" and self.font_style_angle is None:
                    self.font_style_angle = v.number
                    self.font_style_angle_unit = v.unit
                    return

    @at("font-variant-caps")
    def read_font_variant_caps(self, values):
        for v in values:
            if v.text in ("normal", "small-caps", "all-small-caps", "petite-caps",
                          "all-petite-caps", "unicase", "titling-caps"):
                self.font_variant_caps = v.text
                return

    @at("font-variant-position")
    def read_font_variant_position(self, values):
        for v in values:
            if v.text in ("normal", "sub", "super"):
                self.font_variant_position = v.text
                return

    @at("font-weight")
    def read_font_weight(self, values):
        for v in values:
            if v.text in ("normal", "bold", "lighter", "bolder"):
                self.font_weight = v.text
                return
            elif v.number is not None:
                self.font_weight = v.number
                return



# throw away the dispatcher decorator
del TextFormat.at
TextFormat._dispatch = _dispatch
del _dispatch


def css_classes(action):
    """Return a tuple of lower-case CSS class names for the specified standard action."""
    return tuple(a._name.lower() for a in action)


