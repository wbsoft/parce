# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
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


"""
A Lexicon groups rules to match.

A Lexicon is created by decorating a function yielding rules with the
`@lexicon` decorator. A Lexicon acts as a descriptor; when accessed for
the first time via a Language class, a BoundLexicon for that class is
created and cached, and returned each time that attribute is accessed.

The BoundLexicon can parse text according to the rules. When parsing for the
first time, the rules-function is run with the language class as argument, and
the rules it creates are cached.

This makes it possible to inherit from a Language class and only re-implement
some lexicons, the others keep working as in the base class.

"""

import re
import threading

import parce.action
import parce.pattern
import parce.regex


class Lexicon:
    """A Lexicon consists of a set of pattern rules a text is scanned for."""
    __slots__ = ('rules_func', 'lexicons', '_lock', 're_flags')

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
        self._lock = threading.Lock()

    def __get__(self, instance, owner):
        """Called when accessed as a descriptor, via the Language class."""
        if instance:
            raise RuntimeError('Language should never be instantiated')
        try:
            return self.lexicons[owner]
        except KeyError:
            # prevent instantiating the same BoundLexicon multiple times
            with self._lock:
                try:
                    lexicon = self.lexicons[owner]
                except KeyError:
                    lexicon = self.lexicons[owner] = BoundLexicon(self, owner)
                return lexicon


class BoundLexicon:
    """A Bound Lexicon is tied to a particular class.

    This makes it possible to inherit from a Language class and change
    only some Lexicons.

    Call BoundLexicon.parse(text, pos) to do the actual parsing work.
    This function is created as soon as it is called for the first time.

    """
    __slots__ = ('lexicon', 'language', 'parse', '_lock')

    def __init__(self, lexicon, language):
        self.lexicon = lexicon
        self.language = language
        # lock is used once when creating the parse() instance function
        self._lock = threading.Lock()

    def __call__(self):
        """Call the original function, yielding the rules."""
        return self.lexicon.rules_func(self.language) or ()

    def __repr__(self):
        return self.name()

    def name(self):
        """Return the 'Language.lexicon' name of this bound lexicon."""
        return '.'.join((self.language.__name__, self.lexicon.rules_func.__name__))

    def __getattr__(self, name):
        """Implemented to create the parse() function when called for the first time.

        The function is created by _get_parser_func() and is set as instance
        variable, so __getattr__ is not called again.

        """
        try:
            lock = object.__getattribute__(self, "_lock")
        except AttributeError:
            pass # the lock was already deleted, meaning parse is in place already
        else:
            with lock:
                if name == "parse":
                    try:
                        return object.__getattribute__(self, name)
                    except AttributeError:
                        self.parse = self._get_parser_func()
                    del self._lock
                    return self.parse
        return object.__getattribute__(self, name)

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
            if pattern is parce.default_action:
                default_action = action
            elif pattern is parce.default_target:
                default_target = action, *target
            else:
                if isinstance(pattern, parce.pattern.Pattern):
                    pattern = pattern.build()
                patterns.append(pattern)
                action_targets.append((action, *target))

        if not patterns:
            if default_action:
                def parse(text, pos):
                    yield pos, text[pos:], None, default_action
            elif default_target:
                def parse(text, pos):
                    yield (pos, "", None, None, *default_target)
            else:
                # just quits parsing
                def parse(text, pos):
                    yield from ()
            return parse

        # if there is only one pattern, and no dynamic action or target,
        # see if the pattern is simple enough to just use str.find
        if (len(patterns) == 1
            and not isinstance(action_targets[0][0], parce.action.DynamicAction)
            and not any(isinstance(target, parce.target.DynamicTarget)
                            for target in action_targets[0][1:])):
            needle = parce.regex.to_string(patterns[0])
            if needle:
                l= len(needle)
                action_target = action_targets[0]
                if default_action:
                    def parse(text, pos):
                        """Parse text, using a default action for unknown text."""
                        while True:
                            i = text.find(needle, pos)
                            if i > pos:
                                yield pos, text[pos:i], None, default_action
                            elif i == -1:
                                break
                            yield (i, needle, None, *action_target)
                            pos = i + l
                        if pos < len(text):
                            yield pos, text[pos:], None, default_action
                elif default_target:
                    def parse(text, pos):
                        """Parse text, stopping with the default target at unknown text."""
                        while needle == text[pos:pos+l]:
                            yield (pos, needle, None, *action_target)
                            pos += l
                        yield (pos, "", None, None, *default_target)
                else:
                    def parse(text, pos):
                        """Parse text, skipping unknown text."""
                        while True:
                            i = text.find(needle, pos)
                            if i == -1:
                                break
                            yield (i, needle, None, *action_target)
                            pos = i + l
                return parse
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


