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


import collections
import contextlib
import functools
import threading
import weakref


from . import util


FormatCache = collections.namedtuple("FormatCache", "theme base format baseformat")
FormatRange = collections.namedtuple("FormatRange", "pos end textformat")


class AbstractFormatter:
    """A Formatter formats text based on the action of tokens."""



class Formatter(AbstractFormatter):
    """A Formatter is used to format or highlight text according to a Theme.

    Supply the theme, and an optional factory that converts a TextFormat to
    something else.

    In addition to the default theme (which is required), other themes can be
    added coupled to a specific language. This allows the formatter to switch
    theme based on the language of the text.

    """
    def __init__(self, theme=None, factory=None):
        if factory is None:
            factory = lambda f: f
        self._factory = factory
        self._themes = {}
        if theme is not None:
            self.add_theme(None, theme)

    def add_theme(self, language, theme, add_baseformat=False):
        """Add a Theme.

        If ``language`` is None, the theme becomes the default theme and the
        ``add_baseformat`` argument is ignored. If a language is specified (a
        :class:`~parce.language.Language` subclass), the theme will be used for
        tokens from that language. If ``add_baseformat`` is True, the theme's
        baseformat color (window) will be added to all the theme's text
        formats.

        """
        cache = functools.lru_cache(maxsize=None)
        if add_baseformat:
            base_ = theme.baseformat()
            base = self._factory(base_)
            @cache
            def factory(action):
                return self._factory(base_ + theme.textformat(action))

        else:
            base = None
            @cache
            def factory(action):
                return self._factory(theme.textformat(action))

        @cache
        def baseformat(role, state):
            return self._factory(theme.baseformat(role, state))

        self._themes[language] = FormatCache(theme, base, factory, baseformat)

    def get_theme(self, language=None):
        """Return the theme for the specified language.

        If language is None, the default theme is returned.
        Returns None if the language has no specific theme.

        """
        fcache = self._themes.get(language)
        if fcache:
            return fcache.theme

    def remove_theme(self, language):
        """Remove the theme for the specified language."""
        del self._themes[language]

    def baseformat(self, role="window", state="default"):
        """Return our textformat for the current line."""
        return self._themes[None].baseformat(role, state)

    def format_ranges(self, tree, start=0, end=None, format_context=None):
        """Yield FormatRange(pos, end, format) three-tuples.

        The ``format`` is the value returned by Theme.textformat() for the
        token's action, converted by our factory (and cached of course).
        Ranges with a TextFormat for which our factory returns None are
        skipped.

        """
        def stream():
            cache = self._themes.get
            default_fcache = fc = cache(None)
            format_context and format_context.start(fc)
            curlang = None

            prev_end = start
            for context, slice_ in tree.context_slices(start, end):
                lang = context.lexicon.language
                if lang is not curlang:
                    curlang = lang
                    fc = cache(lang, default_fcache)
                    format_context and format_context.switch(fc)
                n = context[slice_]
                stack = []
                i = 0
                while True:
                    for i in range(i, len(n)):
                        m = n[i]
                        if m.is_token:
                            f = fc.format(m.action)
                            if f is not None:
                                if fc.base is not None and m.pos > prev_end:
                                    yield prev_end, m.pos, fc.base
                                yield m.pos, m.end, f
                                prev_end = m.end
                        else:
                            stack.append(i)
                            i = 0
                            n = m
                            lang = n.lexicon.language
                            if lang is not curlang:
                                curlang = lang
                                fc = cache(lang, default_fcache)
                                format_context and format_context.switch(fc)
                            break
                    else:
                        if stack:
                            n = n.parent
                            lang = n.lexicon.language
                            if lang is not curlang:
                                curlang = lang
                                fc = cache(lang, default_fcache)
                                format_context and format_context.switch(fc)
                            i = stack.pop() + 1
                        else:
                            break
            if fc.base is not None and end is not None and prev_end < end:
                yield prev_end, end, fc.base
            format_context and format_context.done()

        ranges = util.merge_adjacent(stream(), FormatRange)
        # make sure first and last range don't stick out
        if start > 0 or end is not None:
            for r in ranges:
                if r.pos < start:
                    r = FormatRange(start, r.end, r.textformat)
                for r1 in ranges:
                    yield r
                    r = r1
                if end is not None and r.end > end:
                    r = FormatRange(r.pos, end, r.textformat)
                yield r
        else:
            yield from ranges

