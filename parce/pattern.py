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
Helper objects to construct regular expressions.

"""


class Pattern:
    """Base class for objects that build a regular expression."""
    def build(self):
        raise NotImplementedError


class Words(Pattern):
    """Creates a regular expression from a list of words."""
    def __init__(self, words, prefix="", suffix=""):
        self.words = words
        self.prefix = prefix
        self.suffix = suffix

    def build(self):
        from . import regex
        expr = regex.words2regexp(self.words)
        if self.prefix or self.suffix:
            return self.prefix + '(?:' + expr + ')' + self.suffix
        return expr


class Char(Pattern):
    """Create a regular expression matching one of the characters in the string.

    If positive is False, the expression is negated, i.e. to match one character
    if it is not in the string.

    """
    def __init__(self, chars, positive=True):
        self.chars = chars
        self.positive = positive

    def build(self):
        from . import regex
        negate = "" if self.positive else "^"
        return '[' + negate + regex.make_charclass(set(self.chars)) + ']'


