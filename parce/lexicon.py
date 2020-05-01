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
A Lexicon groups rules to match.

A LexiconDescriptor is created by decorating a function yielding rules with the
`@lexicon` decorator. When a LexiconDescriptor is accessed for the first time
via a Language subclass, a Lexicon for that class is created and cached, and
returned each time that attribute is accessed.

The Lexicon can parse text according to the rules. When parsing for the first
time, the rules-function is run with the language class as argument, and the
rules it creates are cached.

This makes it possible to inherit from a Language class and only re-implement
some lexicons, the others keep working as in the base class.

Every Lexicon has the following attributes: (they are almost never needed, but
anyway)

``arg``
    The argument the lexicon was called with (creating a derived Lexicon).
    None for a normal lexicon.
``name``
    The short name (name of the method it was defined with)
``fullname``
    The short name with the Language name prepended, like
    ``'Language.lexicon'``.
``qualname``
    The full name with the Language's module prepended, like
    ``'parce.lang.xml.Xml.root'``.
``language``
    The Language class the lexicon belongs to.
``lexicon``
    The LexiconDescriptor the Lexicon was created by.
``re_flags``
    The ``re_flags`` set by the @lexicon decorator.

"""

import itertools
import re
import threading

import parce.regex
from . import util
from .pattern import ArgPattern, Pattern
from .target import TargetFactory
from .rule import Item, ArgItem, DynamicItem, TextItem


class LexiconDescriptor:
    """The LexiconDescriptor creates a Lexicon when called via a class."""
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
            # prevent instantiating the same Lexicon multiple times
            with self._lock:
                try:
                    lexicon = self.lexicons[owner]
                except KeyError:
                    lexicon = self.lexicons[owner] = Lexicon(self, owner)
                return lexicon


class Lexicon:
    """A Lexicon is tied to a particular class.

    This makes it possible to inherit from a Language class and change
    only some Lexicons.

    Call Lexicon.parse(text, pos) to do the actual parsing work.
    This function is created as soon as it is called for the first time.

    """
    def __init__(self, lexicon, language, arg=None):
        self.lexicon = lexicon
        self.language = language
        self.arg = arg
        self.name = lexicon.rules_func.__name__
        self.fullname = language.__name__ + '.' + self.name
        self.qualname = language.__module__ + '.' + self.fullname
        self.__doc__ = lexicon.rules_func.__doc__
        self._derived = {}
        # lock is used when creating a derivate and/or the parse() instance function
        self._lock = threading.Lock()

    def __call__(self, arg=None):
        """Create a derived Lexicon with argument ``arg``.

        The argument should be a simple, hashable singleton object, such as a
        string, an integer or a standard action. The created Lexicon is cached.
        The argument is accessible using special pattern and rule item types,
        so a derived Lexicon can parse text based on rules that are defined at
        parse time, which is useful for things like here documents, where you
        only get to know the end token after the start token has been found.

        When comparing Lexicons with ``equals()``, a derivative lexicon
        compares equal with the Lexicon that created them, although they
        co-exist as separate objects.

        If arg is None, self is returned.

        """
        if arg is None or self.arg is not None:
            return self
        try:
            return self._derived[arg]
        except KeyError:
            with self._lock:
                try:
                    lexicon = self._derived[arg]
                except KeyError:
                    lexicon = self._derived[arg] = Lexicon(self.lexicon, self.language, arg)
            return lexicon

    def equals(self, other):
        """Return True if we are the same lexicon or a derivate from the same."""
        return self.lexicon is other.lexicon and self.language is other.language

    @util.cached_property
    def _rules(self):
        """Yield the rules, building the patterns and replacing the ArgItem instances."""
        def replace_arg_items(items):
            """Replace ArgRuleItem instances."""
            for i in items:
                if isinstance(i, ArgItem):
                    yield from replace_arg_items(i.replace(self.arg))
                else:
                    if isinstance(i, Item):
                        i.itemlists = [list(replace_arg_items(l)) for l in i.itemlists]
                    yield i
        def rules():
            for rule in self.lexicon.rules_func(self.language) or ():
                pattern, *rule = replace_arg_items(rule)
                while isinstance(pattern, Pattern):
                    if isinstance(pattern, ArgPattern):
                        pattern = pattern.build(self.arg)
                    else:
                        pattern = pattern.build()
                yield (pattern, *rule)
        return tuple(rules())

    def __iter__(self):
        """Yield the rules.

        Pattern objects are built, and the ArgItem instances replaced when this
        method is called for the first time.

        """
        yield from self._rules

    def __repr__(self):
        s = self.fullname
        if self.arg is not None:
            s += '*'
        return s

    def __getattr__(self, name):
        """Create certain instance attributes when requested the first time.

        Calls :meth:`get_instance_attributes` to get instance attributes needed
        to use the Lexicon. Those attributes then are set in the Lexicon
        instance, so the do not need to be computed again.

        """
        if name in ("parse",):
            with self._lock:
                try:
                    return object.__getattribute__(self, name)
                except AttributeError:
                    self.parse = self.get_instance_attributes()
        return object.__getattribute__(self, name)

    @property
    def re_flags(self):
        """The re_flags set on instantiation."""
        return self.lexicon.re_flags

    def get_instance_attributes(self):
        """Compile the pattern rules and return instance attributes.

        These are:

        ``parse``
            A ``parse(text, pos)`` function that parses text.

        """
        patterns = []
        rules = []
        no_default_action = object()
        default_action = no_default_action
        default_target = None

        make_target = TargetFactory.make

        # make lists of pattern, action and possible targets
        for pattern, *rule in self:
            if pattern is parce.default_action:
                default_action = rule[0]
            elif pattern is parce.default_target:
                default_target = make_target(self, rule)
            elif rule and pattern is not None and pattern not in patterns:
                # skip rule when the pattern is None or already seen
                patterns.append(pattern)
                rules.append(rule)

        # prepare to handle a dynamic default lexicon (if TextItem descendant)
        dynamic_default_action = False
        if isinstance(default_action, TextItem):
            def dynamic_default_action(text):
                def replace_action(action):
                    for a in action.replace(text, None):
                        return replace_action(a) if isinstance(a, TextItem) else a
                return replace_action(default_action)

        # handle the empty lexicon case
        if not patterns:
            if dynamic_default_action:
                def parse(text, pos):
                    t = text[pos:]
                    yield pos, t, None, dynamic_default_action(t), None
            elif default_action is not no_default_action:
                def parse(text, pos):
                    yield pos, text[pos:], None, default_action, None
            elif default_target:
                def parse(text, pos):
                    if pos < len(text):
                        yield pos, "", None, None, default_target
            else:
                # just quits parsing
                def parse(text, pos):
                    yield from ()
            return parse

        # if there is only one pattern, and no dynamic action or target,
        # see if the pattern is simple enough to just use str.find
        if len(patterns) == 1 and not self.re_flags & re.IGNORECASE and \
                not any(isinstance(item, Item) for item in rules[0]):
            needle = parce.regex.to_string(patterns[0])
            if needle:
                l= len(needle)
                action, *rule = rules[0]
                target = make_target(self, rule)
                if dynamic_default_action:
                    def parse(text, pos):
                        """Parse text, using a default action for unknown text."""
                        while True:
                            i = text.find(needle, pos)
                            if i > pos:
                                t = text[pos:i]
                                yield pos, t, None, dynamic_default_action(t), None
                            elif i == -1:
                                break
                            yield i, needle, None, action, target
                            pos = i + l
                        if pos < len(text):
                            t = text[pos:]
                            yield pos, t, None, dynamic_default_action(t), None
                elif default_action is not no_default_action:
                    def parse(text, pos):
                        """Parse text, using a default action for unknown text."""
                        while True:
                            i = text.find(needle, pos)
                            if i > pos:
                                yield pos, text[pos:i], None, default_action, None
                            elif i == -1:
                                break
                            yield i, needle, None, action, target
                            pos = i + l
                        if pos < len(text):
                            yield pos, text[pos:], None, default_action, None
                elif default_target:
                    def parse(text, pos):
                        """Parse text, stopping with the default target at unknown text."""
                        while needle == text[pos:pos+l]:
                            yield pos, needle, None, action, target
                            pos += l
                        if pos < len(text):
                            yield pos, "", None, None, default_target
                else:
                    def parse(text, pos):
                        """Parse text, skipping unknown text."""
                        while True:
                            i = text.find(needle, pos)
                            if i == -1:
                                break
                            yield i, needle, None, action, target
                            pos = i + l
                return parse

        # compile the regexp for all patterns
        rx = re.compile("|".join("(?P<g_{0}>{1})".format(i, pattern)
            for i, pattern in enumerate(patterns)), self.re_flags)
        # make a fast mapping list from matchObj.lastindex to the rules.
        # rules that contain Item instances are put in the dynamic index
        indices = sorted(v for k, v in rx.groupindex.items() if k.startswith('g_'))
        static = [None] * (indices[-1] + 1)
        dynamic = [None] * (indices[-1] + 1)
        for i, rule in zip(indices, rules):
            if any(isinstance(item, Item) for item in rule):
                dynamic[i] = rule
            else:
                action, *target = rule
                static[i] = (action, make_target(self, target))

        # for rule containing no dynamic stuff, static has the rule, otherwise
        # falls back to dynamic, which is then immediately executed
        def token(m):
            """Return pos, text, match, *rule for the match object."""
            return (m.start(), m.group(), m, *(static[m.lastindex] or replace(m)))

        def replace(m):
            """Recursively replace dynamic rule items in the rule pointed to by match object."""
            def inner_replace(items):
                for i in items:
                    if isinstance(i, DynamicItem):
                        yield from inner_replace(i.replace(m.group(), m))
                    else:
                        yield i
            action, *target = inner_replace(dynamic[m.lastindex])
            return action, make_target(self, target)

        if dynamic_default_action:
            finditer = rx.finditer
            def parse(text, pos):
                """Parse text, using a default action for unknown text."""
                for m in finditer(text, pos):
                    if m.start() > pos:
                        t = text[pos:m.start()]
                        yield pos, t, None, dynamic_default_action(t), None
                    yield token(m)
                    pos = m.end()
                if pos < len(text):
                    t = text[pos:]
                    yield pos, t, None, dynamic_default_action(t), None
        elif default_action is not no_default_action:
            finditer = rx.finditer
            def parse(text, pos):
                """Parse text, using a default action for unknown text."""
                for m in finditer(text, pos):
                    if m.start() > pos:
                        yield pos, text[pos:m.start()], None, default_action, None
                    yield token(m)
                    pos = m.end()
                if pos < len(text):
                    yield pos, text[pos:], None, default_action, None
        elif default_target:
            match = rx.match
            def parse(text, pos):
                """Parse text, stopping with the default target at unknown text."""
                while True:
                    m = match(text, pos)
                    if m:
                        yield token(m)
                        pos = m.end()
                    else:
                        if pos < len(text):
                            yield pos, "", None, None, default_target
                        break
        else:
            finditer = rx.finditer
            def parse(text, pos):
                """Parse text, skipping unknown text."""
                return map(token, finditer(text, pos))
        return parse


