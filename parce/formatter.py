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
This module provides the Formatter class.

Holds a Theme the information from a CSS file and can it provide the
formatting for every standard action, a Formatter is used to actually do
something with a theme. A Formatter can convert TextFormat instances from a
Theme to something you can use, caches those objects and provides a way to
apply formatting to a range of Tokens.

As a special feature, Formatter has a special method ``add_language()`` to
add a language class with its own Theme. The actual theme to use is then
chosen based on the lexicon of the token's Context, so an embedded language
can have its own color scheme.

For example::

    th = Theme.byname('default')     # use the formats from 'default.css'
    f = Formatter(th)
    f.add_language(parce.lang.xml.Xml, Theme("my_funky_xml.css"))

Tokens that originate from lexicons from the Xml language then use the colors
or text formats from my_funky_xml.css, while other tokens are shown in the
colors of the default stylesheet.

If you set ``f.subtheme_window_enabled`` to True (which it is by default),
some formatters can set the window properties for a subtheme to the region of
tokens originating from that theme, enabling an even more advanced
colorization scheme.

"""


import collections
import functools

from . import util


FormatRange = collections.namedtuple("FormatRange", "pos end textformat window")


class Formatter:
    """A Formatter uses a Theme to format text.

    A factory can be set that maps the TextFormats from the theme to
    something else if desired, before they are cached. A factory might
    return None, indicating that no particular formatting is set for
    that action.

    A Formatter is instantiated with a theme that it will use, but it is
    possible to add other Themes for specific languages using add_language().

    If the subtheme_window_enabled instance variable is set to True (the
    default), the property_ranges yielded for sub-languages have the window()
    textformat for that language's Theme in the window attribute, which is
    None otherwise.  This can be used to highlight languages inside other
    languages with their own window theme, if desired.

    """
    subtheme_window_enabled = True

    def __init__(self, theme, factory=None):
        self._theme = theme
        self._factory = factory or (lambda f: f)
        self._formatters = {}

    def theme(self):
        """Return our Theme."""
        return self._theme

    def add_language(self, language, theme):
        """Add a Theme for the specified language."""
        if theme is not self.theme():
            for formatter in self._formatters.values():
                if formatter.theme() is theme:
                    break
            else:
                formatter = type(self)(theme, self._factory)
            self._formatters[language] = formatter

    @functools.lru_cache()
    def window(self, state="default"):
        """Return the textformat for the editor window or encompassing DIV.

        Just like with Theme, state can be "default", "focus" or "disabled."

        """
        return self._factory(self._theme.window(state))

    @functools.lru_cache()
    def selection(self, state="default"):
        """Return the textformat for the selected text.

        Just like with Theme, state can be "default", "focus" or "disabled."

        """
        return self._factory(self._theme.selection(state))

    @functools.lru_cache()
    def currentline(self, state="default"):
        """Return the textformat for the current line.

        Just like with Theme, state can be "default", "focus" or "disabled."

        """
        return self._factory(self._theme.currentline(state))

    @functools.lru_cache()
    def textformat(self, action):
        """Return the textformats for the specified standard action."""
        return self._factory(self._theme.textformat(action))

    def format_ranges(self, tokens):
        """Yield four-tuples PropertyRange(pos, end, properties, window).

        For the base theme, ``window`` is None, but, if
        ``subtheme_window_enabled`` is set to True, for sub-themes that were
        added using add-language, ``window`` are the properties returned by
        Formatter.window() for that theme.

        If different tokens are adjacent and have the same properties, the
        ranges are merged.

        """
        if self._formatters:
            def get_props(token):
                lang = token.parent.lexicon.language
                formatter = self._formatters.get(lang)
                if formatter:
                    window = formatter.window() if self.subtheme_window_enabled else None
                    return formatter.textformat(token.action), window
                return self.textformat(token.action), None
        else:
            def get_props(token):
                return self.textformat(token.action), None
        def gen():
            for t in tokens:
                props, window = get_props(t)
                if props is not None:
                    yield t.pos, t.end, props, window
        return util.merge_adjacent(gen(), FormatRange)


