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
The Formatter uses a Theme to highlight text according to the token's
``action`` attribute. The action is mapped to a TextFormat by the theme.

When a MetaTheme is used, a Formatter is capable of switching Theme
as the MetaTheme provides a special theme for a certain embedded language.

"""


import collections
import contextlib
import weakref


from . import util


FormatRange = collections.namedtuple("FormatRange", "pos end textformat")


class FormatCache:
    window = None
    def __init__(self, theme, factory, secondary=True):
        """Caches conversions from TextFormat to something else."""
        self.factory = factory
        self.theme = theme
        self.secondary = secondary
        if secondary:
            self.window = factory(theme.window())

    @util.cached_method
    def format(self, action):
        if self.secondary:
            f = self.theme.window()
            f += self.theme.textformat(action)
        else:
            f = self.theme.textformat(action)
        return self.factory(f)


class Formatter:
    """A Formatter is used to format or highlight text according to a theme.

    Don't use a Formatter for multiple jobs at the same time.

    """
    def __init__(self, theme, factory=None):
        self._theme = theme
        self.factory = factory or (lambda f: f)
        self._current_theme = theme
        self._caches = weakref.WeakKeyDictionary()
        self._caches[theme] = c = FormatCache(theme, factory, False)
        self._window = c.window
        self._format = c.format

    def theme(self):
        """Return the Theme we were instantiated with."""
        return self._theme

    @util.cached_method
    def window(self, state="default"):
        """Return our textformat for the window or encompassing DIV."""
        return self.factory(self._theme.window(state))

    @util.cached_method
    def selection(self, state="default"):
        """Return our textformat for the selected text."""
        return self.factory(self._theme.selection(state))

    @util.cached_method
    def currentline(self, state="default"):
        """Return out textformat for the current line."""
        return self.factory(self._theme.currentline(state))

    @contextlib.contextmanager
    def switch_theme(self, theme):
        """This context manager is called by MetaTheme.tokens.

        It temporarily switches the current theme.

        """
        old = self._current_theme
        try:
            c = self._caches[theme]
        except KeyError:
            # TODO: know whether we are the default theme of a meta theme...
            c = self._caches[theme] = FormatCache(theme, self.factory, True)
        self._window = c.window
        self._format = c.format
        self._current_theme = theme
        try:
            yield
        finally:
            self._current_theme = old
            c = self._caches[old]
            self._format = c.format
            self._window = c.window

    def format_ranges(self, slices):
        end = 0
        for t in self._theme.tokens(self, slices):
            if t.pos > end and end and self._window is not None:
                yield FormatRange(end, t.pos, self._window)
            yield FormatRange(t.pos, t.end, self._format(t.action))
            end = t.end



