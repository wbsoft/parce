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

from . import regex
from . import rule


def words(words, prefix="", suffix=""):
    """Create a regular expression from a list of words."""
    def build():
        expr = regex.words2regexp(words)
        if prefix or suffix:
            return prefix + '(?:' + expr + ')' + suffix
        return expr
    return rule.pattern(call(build))


def char(chars, positive=True):
    """Create a regular expression matching one of the characters in the string.

    If positive is False, the expression is negated, i.e. to match one character
    if it is not in the string.

    """
    def build():
        negate = "" if positive else "^"
        return '[{}{}]'.format(negate, regex.make_charclass(chars))
    return rule.pattern(call(build))


def arg(escape=True, prefix="", suffix="", default=None):
    r"""Create a pattern that contains the argument the current Lexicon was
    called with.

    If there is no argument in the current lexicon, this Pattern yields the
    default value, which is by default None, resulting in the rule being
    skipped.

    When there is an argument, it is escaped using :func:`re.escape` (when
    ``escape`` was set to True), and if given, ``prefix`` is prepended and
    ``suffix`` is appended. When the default value is used, ``prefix`` and
    ``suffix`` are not used.

    """
    def build(self, arg):
        """Return the lexicon argument as regular expression."""
        if isinstance(arg, str):
            if escape:
                arg = re.escape(arg)
            return prefix + arg + suffix
        return default
    return rule.pattern(call(build, rule.ARG))


def ifarg(pattern, else_pattern=None):
    r"""Create a pattern that returns the specified regular expression pattern
    if the lexicon was called with an argument.

    If there is no argument in the current lexicon, ``else_pattern`` is
    yielded, which is None by default, resulting in the rule being skipped.

    """
    return rule.pattern(rule.choose(rule.call(bool, rule.ARG), else_pattern, pattern))


