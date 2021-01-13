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


r"""
A Lexicon groups rules to match.

A Lexicon is created by decorating a method yielding rules with the
:attr:`@lexicon <lexicon>` decorator. (Although this actually
creates a LexiconDescriptor. When a LexiconDescriptor is accessed for the first
time via a Language subclass, a Lexicon for that class is created and cached,
and returned each time that attribute is accessed.)

This makes it possible to inherit from a Language class and only re-implement
some lexicons, the others keep working as in the base class.

The Lexicon can parse text according to the rules. When its :func:`parse`
function is called for the first time, the rules-function is run with the
language class as argument, and the rules it yields are cached.

The Lexicon then combines the patterns of the rules into one regular expression
that is used to parse the text, using some smart optimizations. (For example,
when a lexicon has only one pattern rule which turns out to be an unambigious
string, :meth:`str.find` is used rather than using :py:func:`re.search`.)

Example:

    >>> from parce import Language, lexicon
    >>>
    >>> class MyLang(Language):
    ...     @lexicon
    ...     def numbers(cls):
    ...         yield r'\d+', "A number"
    ...         yield r'\w+', "A word"
    ...
    >>> MyLang.numbers
    MyLang.numbers
    >>> type(MyLang.numbers)
    <class 'parce.lexicon.Lexicon'>
    >>> for i in MyLang.numbers.parse("1 a2 d3 4 p 5", 0):
    ...  print(i)
    ...
    (0, '1', <re.Match object; span=(0, 1), match='1'>, 'A number', None)
    (2, 'a2', <re.Match object; span=(2, 4), match='a2'>, 'A word', None)
    (5, 'd3', <re.Match object; span=(5, 7), match='d3'>, 'A word', None)
    (8, '4', <re.Match object; span=(8, 9), match='4'>, 'A number', None)
    (10, 'p', <re.Match object; span=(10, 11), match='p'>, 'A word', None)
    (12, '5', <re.Match object; span=(12, 13), match='5'>, 'A number', None)

Parsing (better: lexing) is done by a :class:`~parce.lexer.Lexer` instance,
which switches Lexicon when a target is encountered.

"""

import itertools
import re
import threading

import parce.regex
from . import util
from .target import TargetFactory
from .ruleitem import (
    Item, RuleItem, evaluate_rule, needs_evaluation, pre_evaluate_rule)


class LexiconDescriptor:
    """The LexiconDescriptor creates a Lexicon when called via a class."""

    def __init__(self, rules_func,
                       re_flags=0,
                       consume=False,
        ):
        """Initializes with the rules function.

        The rules function accepts the Language class as argument, and yields
        the pattern, action, target, ... tuples.

        """
        self.rules_func = rules_func    #: the function yielding the rules
        self._re_flags = re_flags
        self._consume = consume
        self._lexicons = {}
        self._lock = threading.Lock()

    def __get__(self, instance, owner):
        """Called when accessed as a descriptor, via the Language class."""
        if instance:
            raise RuntimeError('Language should never be instantiated')
        try:
            return self._lexicons[owner]
        except KeyError:
            # prevent instantiating the same Lexicon multiple times
            with self._lock:
                try:
                    lexicon = self._lexicons[owner]
                except KeyError:
                    lexicon = self._lexicons[owner] = Lexicon(self, owner)
                return lexicon


class Lexicon:
    """A Lexicon parses text according to rules.

    A Lexicon is tied to a particular class, which makes it possible to inherit
    from a Language class and change only some Lexicons.

    .. py:function:: parse(text, pos)

        Start parsing ``text`` from the specified position.
        Yields five-tuples ``(pos, text, matchobj, action, target)``.

        The ``pos`` is the start position a match was found, ``text`` is the
        matched text, ``matchobj`` the match object (which can be None for
        default actions), ``action`` the action that was specified in the
        matching rule, and ``target`` is either None or a
        :class:`~parce.target.Target` object.

    """
    __hash__ = object.__hash__

    def __init__(self, descriptor, language, arg=None):
        #: The LexiconDescriptor this Lexicon was created by.
        self.descriptor = descriptor
        #: The Language class the lexicon belongs to.
        self.language = language
        #: The re_flags that were set on instantiation.
        self.re_flags = descriptor._re_flags
        #: Whether this lexicon wants the token(s) that switched to it
        self.consume = descriptor._consume
        #: The argument the lexicon was called with (creating a derived
        #: Lexicon). None for a normal lexicon.
        self.arg = arg
        #: The short name (name of the method this Lexicon was defined with)
        self.name = descriptor.rules_func.__name__
        #: The short name with the Language name prepended, like
        #: ``'Language.lexicon'``.
        self.fullname = language.__name__ + '.' + self.name
        #: The full name with the Language's module prepended, like
        #: ``'parce.lang.xml.Xml.root'``.
        self.qualname = language.__module__ + '.' + self.fullname
        self.__doc__ = descriptor.rules_func.__doc__
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

        When comparing Lexicons with ``==``, a derived lexicon compares equal
        with the Lexicon that created it, although they co-exist as separate
        objects. Use ``is`` to compare on identity.

        When yielding the rules from a derived lexicon, the dynamic rule items
        that depend on the Lexicon argument are already evaluated. When
        yielding the rules from a vanilla lexicon, they are not evaluated, so
        they adjust themselves to the lexicon they are included in (which will
        then evaluate the rules of course).

        If arg is None, self is returned.

        """
        if arg is None:
            return self
        elif self.arg is not None:
            vanilla = self.descriptor.__get__(None, self.language)
            return vanilla(arg)
        try:
            return self._derived[arg]
        except KeyError:
            with self._lock:
                try:
                    lexicon = self._derived[arg]
                except KeyError:
                    lexicon = self._derived[arg] = Lexicon(self.descriptor, self.language, arg)
            return lexicon

    def __eq__(self, other):
        """Return True if we are the same lexicon or a derivate from the same."""
        return type(other) is type(self) \
            and self.descriptor is other.descriptor \
            and self.language is other.language

    def __ne__(self, other):
        """Return True if we are the not the same lexicon or a derivate from the same."""
        return type(other) is not type(self) \
            or self.descriptor is not other.descriptor \
            or self.language is not other.language

    @util.cached_property
    def _rules(self):
        """Yield the rules.

        Rule items that depend on the lexicon argument are not yet evaluated.

        """
        return tuple(self.descriptor.rules_func(self.language) or ())

    @util.cached_property
    def rules(self):
        """Return all rules in a tuple.

        Rule items that depend on the lexicon argument are already evaluated.

        """
        return tuple(pre_evaluate_rule(rule, self.arg)
                for rule in self.descriptor.rules_func(self.language) or ())

    def __iter__(self):
        """Yield the rules.

        Patterns are created when this method is called for the first time. If
        this is a derived lexicon, dynamic rule items that depend on the
        argument are already evaluated.

        """
        yield from self.rules if self.arg is not None else self._rules

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
                    self.parse = self._get_instance_attributes()
        return object.__getattribute__(self, name)

    def _get_instance_attributes(self):
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
        for pattern, *rule in self.rules:
            if pattern is parce.default_action:
                default_action = rule[0]
            elif pattern is parce.default_target:
                default_target = make_target(self, rule)
            elif rule and pattern is not None and pattern not in patterns:
                # skip rule when the pattern is None or already seen
                patterns.append(pattern)
                rules.append(rule)

        # prepare to handle a dynamic default action
        if isinstance(default_action, RuleItem):
            def dynamic_default_action(text):
                return default_action.evaluate({'text': text})
        else:
            dynamic_default_action = False

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
                not needs_evaluation(rules[0]):
            needle = parce.regex.to_string(patterns[0])
            if needle:
                l = len(needle)
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
            if needs_evaluation(rule):
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
            action, *target = evaluate_rule(dynamic[m.lastindex], m)
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


def lexicon(rules_func=None, **kwargs):
    """Lexicon factory decorator.

    Use this decorator to make a function in a Language class definition a
    LexiconDescriptor object. The LexiconDescriptor is a descriptor, and when
    calling it via the Language class attribute, a Lexicon is created, cached
    and returned.

    You can specify keyword arguments, that will be passed on to the Lexicon
    object as soon as it is created.

    The following keyword arguments are supported:

    ``re_flags`` (0):
        The flags that are passed to the regular expression compiler

    ``consume`` (False):
        When set to True, tokens originating from a rule that pushed this
        lexicon are added to the target Context instead of the current.

    The code body of the function should return (yield) the rules of the
    lexicon, and is run with the Language class as first argument, as soon as
    the lexicon is used for the first time.

    You can also call the Lexicon object just as an ordinary classmethod, to
    get the rules, e.g. for inclusion in a different lexicon.

    """
    if rules_func and not kwargs:
        return LexiconDescriptor(rules_func)
    def lexicon(rules_func):
        return LexiconDescriptor(rules_func, **kwargs)
    return lexicon

