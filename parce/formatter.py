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

It is possible to add more Themes to a formatter, coupled to a certain
language, so that the formatter can switch to that theme for embedded pieces of
text of that language.

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

    def format_caches(self):
        """Should return a dictionary mapping language to FormatCache.

        A FormatCache normally encapsulates a theme. The key None should be
        present and denotes the default theme. Other keys should be
        :class:`~parce.language.Language` subclasses, and their theme is used
        for tokens that originate from that language.

        """
        raise NotImplementedError

    def baseformat(self, role="window", state="default"):
        """Return our textformat for the current line."""
        return self.format_caches()[None].baseformat(role, state)

    def format_ranges(self, tree, start=0, end=None, format_context=None):
        """Yield FormatRange(pos, end, format) three-tuples.

        The ``format`` is the value returned by Theme.textformat() for the
        token's action, converted by our factory (and cached of course).
        Ranges with a TextFormat for which our factory returns None are
        skipped.

        """
        format_caches = self.format_caches()
        if len(format_caches) == 1:
            # language will never be switched, no need to follow language
            def stream():
                fc = format_caches.get(None)
                format_context and format_context.start(fc)
                for t in tree.tokens_range(start, end):
                    f = fc.format(t.action)
                    if f is not None:
                        yield t.pos, t.end, f
                format_context and format_context.done()
        else:
            # language can potentially switch, follow it
            def stream():
                cache = self.format_caches.get
                default_fcache = fc = cache(None)
                format_context and format_context.start(fc)
                curlang = None

                # Modifies curlang and current format cache fc if lang changes
                def check_lang(lang):
                    nonlocal curlang, fc
                    if lang is not curlang:
                        curlang = lang
                        nfc = cache(lang, default_fcache)
                        if nfc is not fc:
                            fc = nfc
                            if format_context:
                                format_context.switch(fc)

                prev_end = start
                for context, slice_ in tree.context_slices(start, end):
                    check_lang(context.lexicon.language)
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
                                check_lang(n.lexicon.language)
                                break
                        else:
                            if stack:
                                n = n.parent
                                check_lang(n.lexicon.language)
                                i = stack.pop() + 1
                            else:
                                break
                if fc.base is not None and end is not None and prev_end < end:
                    yield prev_end, end, fc.base
                format_context and format_context.done()

        return util.merge_adjacent(
            util.fix_boundaries(stream(), start, end), FormatRange)


class Formatter(AbstractFormatter):
    """A Formatter is used to format or highlight text according to a Theme.

    Supply the theme, and an optional factory that converts a TextFormat to
    something else. For example::

        >>> from parce import root, find, theme_by_name
        >>> from parce.formatter import Formatter
        >>> tree = root(find("css"), "h1 { color: red; }")
        >>> f = Formatter(theme_by_name('default'))
        >>> list(f.format_ranges(tree))
        [FormatRange(pos=0, end=2, textformat=<TextFormat color=Color(r=0, g=0,b=
        139, a=1.0), font_weight='bold'>), FormatRange(pos=3, end=4, textformat=<
        TextFormat font_weight='bold'>), FormatRange(pos=5, end=10, textformat=<T
        extFormat color=Color(r=65, g=105, b=225, a=1.0), font_weight='bold'>), F
        ormatRange(pos=12, end=15, textformat=<TextFormat color=Color(r=46, g=139
        , b=87, a=1.0)>), FormatRange(pos=15, end=16, textformat=<TextFormat >),
        FormatRange(pos=17, end=18, textformat=<TextFormat font_weight='bold'>)]

    The default factory just yields the TextFormat right from the theme, unless
    the format is empty, evaluating to None.

    And here is an example using a factory that converts the textformat to a
    dictionary of css properties, e.g. to use for inline CSS highlighting. Note
    that when the factory returns None, a range is skipped, so we return None
    in case a dictionary ends up empty::

        >>> factory = lambda tf: tf.css_properties() or None
        >>> f = Formatter(theme_by_name('default'), factory)
        >>> list(f.format_ranges(tree))
        [FormatRange(pos=0, end=2, textformat={'color': '#00008b', 'font-weight':
        'bold'}), FormatRange(pos=3, end=4, textformat={'font-weight': 'bold'}),
        FormatRange(pos=5, end=10, textformat={'color': '#4169e1', 'font-weight':
        'bold'}), FormatRange(pos=12, end=15, textformat={'color': '#2e8b57'}),
        FormatRange(pos=17, end=18, textformat={'font-weight': 'bold'})]

    In addition to the default theme (which is required), other themes can be
    added coupled to a specific language. This allows the formatter to switch
    theme based on the language of the text.

    """
    def __init__(self, theme=None, factory=None):
        if factory is None:
            factory = lambda f: f or None
        self._factory = factory
        self._themes = {}
        if theme is not None:
            self.add_theme(None, theme)

    def format_caches(self):
        """Reimplemented to return the format caches added by add_theme()."""
        return self._themes

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

        self.format_caches()[language] = FormatCache(theme, base, factory, baseformat)

    def get_theme(self, language=None):
        """Return the theme for the specified language.

        If language is None, the default theme is returned.
        Returns None if the language has no specific theme.

        """
        try:
            return self.format_caches()[language].theme
        except KeyError:
            pass

    def remove_theme(self, language):
        """Remove the theme for the specified language."""
        del self.format_caches()[language]


class SimpleFormatter(AbstractFormatter):
    """A formatter that simply yields a HTML class string for every action.

    For example::

        >>> import parce.formatter
        >>> tree = parce.root(parce.find("css"), "h1 { color: red; }")
        >>> f = parce.formatter.SimpleFormatter()
        >>> list(f.format_ranges(tree))
        [FormatRange(pos=0, end=2, textformat='name tag'),
         FormatRange(pos=3, end=4, textformat='delimiter bracket'),
         FormatRange(pos=5, end=10, textformat='name property definition'),
         FormatRange(pos=10, end=11, textformat='delimiter'),
         FormatRange(pos=12, end=15, textformat='literal color'),
         FormatRange(pos=15, end=16, textformat='delimiter'),
         FormatRange(pos=17, end=18, textformat='delimiter bracket')]

    This formatter does not use a theme; language switches are ignored.

    """
    def format_caches(self):
        """Reimplemented to return a FormatCache with a factory that concerts
        an action to a css class string.

        """
        from parce.theme import css_class
        def baseformat(role, state):
            return None
        return {None: FormatCache(None, None, css_class, baseformat)}


class FormatContext:
    """FormatContext can be used to track theme changes during formatting.

    A FormatContext instance can be given to the
    :meth:`AbstractFormatter.format_ranges` method of a formatter.

    Inheriting from this class and implementing the methods enable you to
    react to theme changes during formatting.

    """
    def start(self, fcache):
        """Called when formatting starts, with the default Theme's format cache."""

    def switch(self, fcache):
        """Called whenever formatting switches to a different theme."""

    def done(self):
        """Called when formatting has finished."""


