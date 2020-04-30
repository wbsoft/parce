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
Helper objects to construct regular expressions.

"""


import re
import reprlib


class Pattern:
    """Base class for objects that build a regular expression.

    The ``build()`` method should return a regular pattern string, or another
    ``Pattern`` object.

    If the ``build()`` method returns None, the entire rule is skipped.

    """
    def build(self):
        """Create and return the regular expression string."""
        raise NotImplementedError

    def __repr__(self):
        items = ("{}={}".format(name, reprlib.repr(value))
                    for name, value in self.__dict__.items())
        return "<{} {}>".format(self.__class__.__name__, ", ".join(items))


class Words(Pattern):
    """Creates a regular expression from a list of words."""
    def __init__(self, words, prefix="", suffix=""):
        self.words = words
        self.prefix = prefix
        self.suffix = suffix

    def build(self):
        """Return an optimized regular expression string from the words list."""
        from . import regex
        expr = regex.words2regexp(self.words)
        if self.prefix or self.suffix:
            return self.prefix + '(?:' + expr + ')' + self.suffix
        return expr


class Char(Pattern):
    """Creates a regular expression matching one of the characters in the string.

    If positive is False, the expression is negated, i.e. to match one character
    if it is not in the string.

    """
    def __init__(self, chars, positive=True):
        self.chars = chars
        self.positive = positive

    def build(self):
        """Return an optimized regular expression string for the characters."""
        from . import regex
        negate = "" if self.positive else "^"
        return '[{}{}]'.format(negate, regex.make_charclass(self.chars))


class ArgPattern(Pattern):
    """Abstract Pattern subclass that uses the lexicon argument.

    The :meth:`build` method has changed to accept the Lexicon argument, which
    can be used to customize the pattern.

    """
    def build(self, arg):
        """Create and return the regular expression string, using the lexicon argument."""
        raise NotImplementedError


class Arg(ArgPattern):
    r"""Creates a pattern that contains the argument the current Lexicon was
    called with.

    If there is no argument in the current lexicon, this Pattern yields the
    default value, which is by default None, resulting in the rule being
    skipped.

    When there is an argument, it is escaped using :func:`re.escape` (when
    ``escape`` was set to True), and if given, ``prefix`` is prepended and
    ``suffix`` is appended. When the default value is used, ``prefix`` and
    ``suffix`` are not used.

    """
    def __init__(self, escape=True, prefix="", suffix="", default=None):
        self.escape = escape
        self.prefix = prefix
        self.suffix = suffix
        self.default = default

    def build(self, arg):
        """Return the lexicon argument as regular expression."""
        if isinstance(arg, str):
            if self.escape:
                arg = re.escape(arg)
            return self.prefix + arg + self.suffix
        return self.default


class IfArg(ArgPattern):
    r"""Pattern that returns the specified regular expression pattern (or
    nested Pattern instance) if the lexicon was called with an argument.

    If there is no argument in the current lexicon, ``else_pattern`` is
    yielded, which is None by default, resulting in the rule being skipped.

    """
    def __init__(self, pattern, else_pattern=None):
        self.pattern = pattern
        self.else_pattern = else_pattern

    def build(self, arg):
        return self.pattern if arg is not None else self.else_pattern


