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

All kinds of text formatting and/or highlighting can be implemented by using
or inheriting of Formatter. If you need to convert the TextFormats from the
theme to something else, you can provide a factory to Formatter to do that.

If you need more special behaviour, you can inherit from Formatter and
reimplement ``format_ranges()``, to do other things or to use a different
FormatContext.


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

    It can keep a window() TextFormat into account for sub-themes (themes
    that are invoked on a per-language basis), and it can adjust the formats
    for the sub-themed tokens with the window() format for that theme.

    The factory that was given to the Formatter is used by the FormatCache to
    convert the TextFormat of the theme to something used by the formatter.

    A Formatter keeps a FormatCache for its theme, and in the case of a
    MetaTheme, a FormatCache is used for every sub-theme. The FormatContext
    is used to switch theme, and in its default implementation it switches
    the FormatCache it uses.

    """
    def __init__(self, theme, factory, add_window=True):
        """Caches conversions from TextFormat to something else."""
        if add_window:
            window = theme.baseformat()
            self.window = factory(window)
            self._format = lambda action: factory(window + theme.textformat(action))
        else:
            self.window = None
            self._format = lambda action: factory(theme.textformat(action))

    @util.cached_method
    def format(self, action):
        """Return our text format for the action, caching it for later reuse."""
        return self._format(action)


class FormatContext:
    """A FormatContext is used during a formatting job.

    It maintains the state needed to format using a MetaTheme. The only API
    used is the ``push()`` and ``pop()`` method, which are called by the
    ``tokens()`` method of MetaTheme.

    The default Formatter uses the ``window`` property and ``format`` method
    to get the window style for the current theme and the factory that turns
    a standard action if the format we want.

    """
    def __init__(self, formatter):
        self._stack = []
        self._formatter = formatter
        self._current_theme = None
        self._set_theme(formatter.theme())

    def _switch_language(self, language):
        self._set_theme(self._formatter.theme().get_theme(language))

    def _set_theme(self, theme):
        if theme is not self._current_theme:
            self._current_theme = theme
            c = self.cache = self._formatter.format_cache(theme)
            self.window = c.window
            self.format = c.format

    def push(self, language):
        self._stack.append(language)
        if len(self._stack) < 2 or language is not self._stack[-2]:
            self._switch_language(language)

    def pop(self):
        language = self._stack.pop()
        if len(self._stack) > 0 and language is not self._stack[-1]:
            self._switch_language(self._stack[-1])


class Formatter:
    """A Formatter is used to format or highlight text according to a theme.

    Supply the theme, and an optional factory that converts a TextFormat
    to something else.

    """
    def __init__(self, theme, factory=None):
        self._lock = threading.Lock()   # lock for FormatCaches
        self._theme = theme
        self._factory = factory or (lambda f: f)
        self._caches = weakref.WeakKeyDictionary()
        self._caches[theme] = c = FormatCache(theme, factory, False)

    def theme(self):
        """Return the Theme we were instantiated with."""
        return self._theme

    @util.cached_method
    def baseformat(self, role="window", state="default"):
        """Return our textformat for the current line."""
        return self._factory(self._theme.baseformat(role, state))

    def format_cache(self, theme):
        """Return a FormatCache for the Theme.

        The FormatCache caches the converted textformat, optionally taking
        the default window style into account.  And the Formatter caches the
        FormatCaches :-)

        """
        try:
            return self._caches[theme]
        except KeyError:
            with self._lock:
                try:
                    return self._caches[theme]
                except KeyError:
                    add_window = self.theme().get_add_window(theme)
                    c = self._caches[theme] = FormatCache(
                                    theme, self._factory, add_window)
                return c

    def format_ranges(self, tree, start=0, end=None):
        """Yield FormatRange(pos, end, format) three-tuples.

        The ``format`` is the value returned by Theme.textformat() for the
        token's action, converted by our factory (and cached of course).
        Ranges with a TextFormat for which our factory returns None are
        skipped.

        """
        c = FormatContext(self)
        def stream():
            prev_end = sys.maxsize
            for t in self._theme.tokens(c, tree, start, end):
                if t.pos > prev_end and c.window is not None:
                    # if a sub-language is active, draw its background
                    yield prev_end, t.pos, c.window
                f = c.format(t.action)
                if f is not None:
                    yield t.pos, t.end, f
                prev_end = t.end
        yield from util.merge_adjacent(stream(), FormatRange)


