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
TeX and LaTeX.
"""

__all__ = ('Latex',)

import re

from parce import Language, lexicon, default_action
from parce.action import (
    Comment, Delimiter, Escape, Name, Number, Operator, Pseudo, Text)
from parce.rule import arg, MATCH, bygroup, ifgroup, ifmember


MATH_ENVIRONMENTS = (
    "math", "displaymath", "equation", "eqnarray", "aqnarray*")


class Latex(Language):
    @lexicon
    def root(cls):
        yield from cls.common()
        yield default_action, Text

    @classmethod
    def common(cls):
        yield r'(\\begin)(?:\s*(\{)(.*?)(\})|(?=[\W\d]))', \
            bygroup(Name.Builtin, Delimiter, Name.Tag, Delimiter), \
            cls.get_environment_target()
        yield r'(\\[^\W\d]+)(?:\s*(\[))?', bygroup(Name.Command, Delimiter.Bracket), \
            ifgroup(2, cls.option)
        yield r'\{\\(oe|OE|ae|AE|aa|AA|o|O|l|L|ss|SS)\}', Escape
        yield r"[!?]'", Escape
        yield r"""\\[`'^"~=.]([a-zA-Z]{1,2}|\\[ij])(?=[\W\d])""", Escape
        yield r"""\\[`'^"~=.uvHtcdbr]\{([a-zA-Z]{1,2}|\\[ij])\}""", Escape
        yield r'\{', Delimiter.Brace, cls.brace
        yield r'\\\[', Delimiter, cls.math(r'\]')
        yield r'\$\$', Delimiter, cls.math(r'$$')
        yield r'\\\(', Delimiter, cls.math(r'\)')
        yield r'\$', Delimiter, cls.math(r'$')
        yield from cls.base()

    @classmethod
    def base(cls):
        """Basic stuff."""
        yield r'\\[#$&~^%{}_ ]', Escape
        yield r'[&_^~]', Name.Command
        yield r'\\\\', Delimiter.Terminator    # line termination TODO: better action?
        yield r'%', Comment, cls.comment

    @lexicon
    def brace(cls):
        yield r'\}', Delimiter.Brace, -1
        yield from cls.root

    @lexicon
    def option(cls):
        yield r'\]', Delimiter.Bracket, -1
        yield from cls.common()
        yield default_action, Pseudo    # TODO: find better action

    @lexicon
    def environment(cls):
        yield r'(\\end)(?:\s*(\{)(.*?)(\})|(?=[\W\d]))', \
            bygroup(Name.Builtin, Delimiter, Name.Tag, Delimiter), -1
        yield from cls.root

    # ------------------------------ math ------------------------------------
    @lexicon
    def environment_math(cls):
        yield r'(\\end)(?:\s*(\{)(.*?)(\})|(?=[\W\d]))', \
            bygroup(Name.Builtin, Delimiter, Name.Tag, Delimiter), -1
        yield from cls.math_common()

    @lexicon
    def math(cls):
        yield arg(default=r'\}'), Delimiter, -1
        yield from cls.math_common()

    @classmethod
    def math_common(cls):
        """Stuff in math mode."""
        yield r'\{', Delimiter.Brace, cls.math
        yield r"[\-+=<>/:!']", Operator
        yield r"[\|\[\]\(\)]", Delimiter
        yield r'\\[A-Za-z]+', Name.Function
        yield r'[A-Za-z]+', Name.Variable
        yield r'\d+(?:\.\d+)*', Number
        yield from cls.base()
        yield default_action, Text.Math

    @classmethod
    def get_environment_target(cls):
        """Return environment target, can be overridden to support special environments."""
        return ifmember(MATCH(3), MATH_ENVIRONMENTS, cls.environment_math, cls.environment)

    # ----------------------------- comments ---------------------------------
    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield '$', None, -1
        yield from cls.comment_common()

