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


import sys
import collections
import contextlib
import threading
import weakref


from . import util


FormatRange = collections.namedtuple("FormatRange", "pos end textformat")


class FormatCache:
    """A FormatCache caches conversions from TextFormat to something else.

    It can keep a window() TextFormat into account for secondary themes
    (themes that are invoked on a per-language basis), and it can adjust
    the formats for the sub-themed tokens with the window() format for
    that theme.

    """
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


class FormatContext:
    """A FormatContext is used during a formatting job.

    It maintains the state needed to format using a MetaTheme. The only API
    used is the ``switch_theme()`` context manager method, which is called by
    the ``tokens()`` method of MetaTheme.

    """
    def __init__(self, formatter):
        self.formatter = formatter
        t = formatter.theme()
        c = self.cache = formatter.format_cache(t)
        self.window = c.window
        self.format = c.format

    @contextlib.contextmanager
    def switch_theme(self, theme):
        old = self.cache
        c = self.cache = self.formatter.format_cache(theme)
        self.window = c.window
        self.format = c.format
        try:
            yield
        finally:
            self.cache = old
            self.window = old.window
            self.format = old.format


class Formatter:
    """A Formatter is used to format or highlight text according to a theme.

    Supply the theme, and an optional factory that converts a TextFormat
    to something else.  If you set ``secondary_subthemes`` to True (the default),
    TextFormats of subthemes will be mixed with their window() attributes.
    If you set ``secondary_subthemes`` to False, the textformats of subthemes
    will not be altered.

    """
    def __init__(self, theme, factory=None, secondary_subthemes=True):
        self._lock = threading.Lock()   # lock for FormatCaches
        self._theme = theme
        self._factory = factory or (lambda f: f)
        self._current_theme = theme
        self._caches = weakref.WeakKeyDictionary()
        self._caches[theme] = c = FormatCache(theme, factory, False)

    def theme(self):
        """Return the Theme we were instantiated with."""
        return self._theme

    @util.cached_method
    def window(self, state="default"):
        """Return our textformat for the window or encompassing DIV."""
        return self._factory(self._theme.window(state))

    @util.cached_method
    def selection(self, state="default"):
        """Return our textformat for the selected text."""
        return self._factory(self._theme.selection(state))

    @util.cached_method
    def currentline(self, state="default"):
        """Return our textformat for the current line."""
        return self._factory(self._theme.currentline(state))

    def format_cache(self, theme):
        """Return a FormatCache for the Theme.

        This is used when a sub-theme from a MetaTheme is used.

        """
        try:
            return self._caches[theme]
        except KeyError:
            with self._lock:
                try:
                    return self._caches[theme]
                except KeyError:
                    c = self._caches[theme] = FormatCache(
                            theme, self.factory, self.secondary_subthemes)
                return c

    def format_ranges(self, slices):
        """Yield FormatRange(pos, end, format) three-tuples.

        The ``format`` is the value returned by Theme.textformat() for the
        token's action, converted by our factory (and cached of course).

        """
        end = sys.maxsize
        c = FormatContext(self)
        for t in self._theme.tokens(c.switch_theme, slices):
            if t.pos > end and c.window is not None:
                # if a sub-language is active, draw its background
                yield FormatRange(end, t.pos, c.window)
            yield FormatRange(t.pos, t.end, c.format(t.action))
            end = t.end



