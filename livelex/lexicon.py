# -*- coding: utf-8 -*-
#
# This file is part of the livelex Python package.
#
# Copyright © 2019 by Wilbert Berendsen <info@wilbertberendsen.nl>
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


import re

import livelex.pattern


class Lexicon:
    """A Lexicon consists of a set of pattern rules a text is scanned for.

    """
    __slots__ = ('rules_func', 'lexicons', 're_flags')

    def __init__(self, rules_func,
                       re_flags=0,
        ):
        """Initializes with the rules function.

        The rules function accepts the Language class as argument, and yields
        the pattern, action, target, ... tuples.

        """
        self.rules_func = rules_func
        self.re_flags = re_flags
        self.lexicons = {}

    def __get__(self, instance, owner):
        """Called when accessed as a descriptor, via the Language class."""
        if instance:
            raise RuntimeError('Language should never be instantiated')
        try:
            lexicon = self.lexicons[owner]
        except KeyError:
            lexicon = self.lexicons[owner] = BoundLexicon(self, owner)
        return lexicon


class BoundLexicon:
    """A Bound Lexicon is tied to a particular class.

    This makes it possible to inherit from a Language class and change
    only some Lexicons.

    """
    __slots__ = ('lexicon', 'language', '_parser_func')

    def __init__(self, lexicon, language):
        self.lexicon = lexicon
        self.language = language

    def __call__(self):
        """Call the original function, yielding the rules."""
        return self.lexicon.rules_func(self.language)

    def __repr__(self):
        return self.name()

    def name(self):
        """Return the 'Language.lexicon' name of this bound lexicon."""
        return '.'.join((self.language.__name__, self.lexicon.rules_func.__name__))

    @property
    def parse(self):
        try:
            f = self._parser_func
        except AttributeError:
            f = self._parser_func = self._get_parser_func()
        return f

    @property
    def re_flags(self):
        """The re_flags set on instantiation."""
        return self.lexicon.re_flags

    def _get_parser_func(self):
        """Compile the pattern rules and return a parse(text, pos) func."""
        patterns = []
        action_targets = []
        default_action = None
        default_target = None
        # make lists of pattern, action and possible targets
        for pattern, action, *target in self():
            if pattern is livelex.default_action:
                default_action = action
            elif pattern is livelex.default_target:
                default_target = action, *target
            else:
                if isinstance(pattern, livelex.pattern.Pattern):
                    pattern = pattern.build()
                patterns.append(pattern)
                action_targets.append((action, *target))
        # compile the regexp for all patterns
        rx = re.compile("|".join("(?P<g_{0}>{1})".format(i, pattern)
            for i, pattern in enumerate(patterns)), self.re_flags)
        # make a fast mapping list from matchObj.lastindex to the targets
        indices = sorted(v for k, v in rx.groupindex.items() if k.startswith('g_'))
        index = [None] * (indices[-1] + 1)
        for i, action_target in zip(indices, action_targets):
            index[i] = action_target

        if default_action:
            def parse(text, pos):
                """Parse text, using a default action for unknown text."""
                for m in rx.finditer(text, pos):
                    if m.start() > pos:
                        yield pos, text[pos:m.start()], None, default_action
                    yield (m.start(), m.group(), m, *index[m.lastindex])
                    pos = m.end()
                if pos < len(text):
                    yield (pos, text[pos:], None, default_action)
        elif default_target:
            def parse(text, pos):
                """Parse text, stopping with the default target at unknown text."""
                while True:
                    m = rx.match(text, pos)
                    if m:
                        yield (pos, m.group(), m, *index[m.lastindex])
                        pos = m.end()
                    else:
                        yield (pos, "", None, None, *default_target)
                        break
        else:
            def parse(text, pos):
                """Parse text, skipping unknown text."""
                for m in rx.finditer(text, pos):
                    yield (m.start(), m.group(), m, *index[m.lastindex])
        return parse


