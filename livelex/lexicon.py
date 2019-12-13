# -*- coding: utf-8 -*-
#
# This file is part of the livelex Python module.
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


default_action = object()
default_target = object()


class Lexicon:
    """A Lexicon consists of a set of pattern rules a text is scanned for.
    
    """
    __slots__ = ('rules_func', 'lexicons')
    
    def __init__(self, rules_func):
        """Initializes with the rules function.
        
        The rules function accepts the Language class as argument, and yields
        the pattern, action, target, ... tuples.
        
        """
        self.rules_func = rules_func
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
    
    @property
    def parse(self):
        try:
            return self._parser_func
        except AttributeError:
            c = CompiledLexicon(self)
            if c.default_action:
                f = c._parse_with_default_action
            elif c.default_target:
                f = c._parse_with_default_state
            else:
                f = c._parse
            self._parser_func = f
            return f


class CompiledLexicon:
    """Compiles the pattern rules.
    
    Has the following member variables after instantiation:
    
    default_action (None), the default action
    default_target (None), the default target
    pattern, the compiled regular expression.
    
    """
    __slots__ = ('default_action', 'default_target', 'pattern', '_index')
    
    def __init__(self, lexicon):
        patterns = []
        index = []
        self.default_action = None
        self.default_target = None
        # make lists of pattern, action and possible targets
        for pattern, action, *target in lexicon():
            if pattern is default_action:
                self.default_action = action
            elif pattern is default_target:
                self.default_target = action, *target
            else:
                patterns.append(pattern)
                index.append((action, target))
        # compile the regexp for all patterns
        rx = self.pattern = re.compile("|".join("(?P<g_{0}>{1})".format(i, pattern)
            for i, pattern in enumerate(patterns)), lexicon.language.re_flags)
        # make a fast mapping list from matchObj.lastindex to the targets
        indices = sorted(v for k, v in rx.groupindex.items() if k.startswith('g_'))
        t = self._index = [None] * (indices[-1] + 1)
        for i, action_target in zip(indices, index):
            t[i] = action_target

    def _parse(self, text, pos):
        """Parse text continuously."""
        for m in self.pattern.finditer(text, pos):
            yield m.start(), m.group(), m, *self._index[m.lastindex]
    
    def _parse_with_default_action(self, text, pos):
        """Parse text continuously, using a default action for unparsed text."""
        for m in self.pattern.finditer(text, pos):
            if m.start() > pos:
                yield pos, text[pos:m.start()], None, self.default_action
            yield m.start(), m.group(), m, *self._index[m.lastindex]
            pos = m.end()
        if pos < len(text):
            yield pos, text[pos:], None, self.default_action

    def _parse_with_default_state(self, text, pos):
        """Parse text only once, used if there is a default_target."""
        m = self.pattern.match(text, pos)
        if m:
            yield m.start(), m.group(), m, *self._index[m.lastindex]
        else:
            yield pos, "", None, None, *self.default_target



def lexicon(rules_func):
    """Decorator to make a function in a Language class definition a Lexicon object."""
    return Lexicon(rules_func)



