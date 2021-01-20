# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2021-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Bash and other UNIX shell (sh)  syntax.

"""

__all__ = ('Bash',)

import re

from parce import Language, lexicon, default_action
from parce.action import (
    Bracket, Comment, Delimiter, Escape, Keyword, Name, Number, Operator,
    String, Text
)
from parce.rule import MATCH, bygroup, ifgroup, findmember


class Bash(Language):
    """Bash and other shell syntax."""

    @lexicon(re_flags=re.MULTILINE)
    def root(cls):
        """Root lexicon."""
        yield r'\A#!.*?$', Comment.Special
        yield from cls.common()

    @classmethod
    def common(cls):
        """Yield common stuff: comment, expression, expansions, etc."""
        yield '#', Comment, cls.comment
        yield r'\(\(', Delimiter.Start, cls.arith_expr
        yield r'\(', Delimiter.Start, cls.subshell
        yield r'\{', Bracket.Start, cls.group_command
        yield r'\[\[', Bracket.Start, cls.cond_expr

        yield from cls.variable_expansion()

    @classmethod
    def expression_common(cls):
        """Common things in expressions."""
        yield r'0\d+', Number.Octal
        yield r'0[xX][0-9a-fA-F]+', Number.Hexadecimal
        yield r'\d+#[0-9a-zA-Z@_]+', Number
        yield r'\d+', Number
        yield r'\w+', Name.Variable
        yield r',', Delimiter.Separator
        yield r'\+\+?|--?|\*\*?|<[=<]?|>[=>]?|&&?|\|\|?|[=!]=|[~!/%^?:]', Operator
        yield r'(?:[*/%+&\-|]|<<|>>)?=', Operator.Assignment

    @classmethod
    def variable_expansion(cls):
        """Variable expansion with ``$``."""
        yield r'(\$)(\(\()', bygroup(Name.Variable, Delimiter.Start), cls.arith_expr
        yield r'(\$)(\()',  bygroup(Name.Variable, Delimiter.Start), cls.subshell
        yield r'\$[*@#?\$!0-9-]', Name.Variable.Special
        yield r'\$\w+', Name.Variable
        yield r'\$\{', Name.Variable, cls.parameter

    @classmethod
    def quoting(cls):
        """Escape, single and double quotes."""
        yield r'\\.', Escape
        yield r'"', String.Start, cls.dqstring
        yield r"'", String.Start, cls.sqstring

    @lexicon
    def dqstring(cls):
        """A double-quoted string."""
        yield r'"', String.End, -1
        yield r'\\.', String.Escape
        yield from cls.variable_expansion()
        yield default_action, String

    @lexicon
    def sqstring(cls):
        """A single-quoted string."""
        yield r"'", String.End, -1
        yield default_action, String

    @lexicon
    def parameter(cls):
        """Contents of ``${`` ... ``}``."""
        yield r'\}', Name.Variable, -1
        yield r'\w+', Name.Variable
        yield r'\[', Delimiter.Bracket.Start, cls.subscript
        yield r':[-=?+]?|##?|%%?|\^\^?|,,?|@', Delimiter.ModeChange

    @lexicon
    def subscript(cls):
        """Contents of ``[`` ... ``]`` in an array reference."""
        yield r'\]', Delimiter.Bracket.End, -1
        yield from cls.expression_common()
        yield from cls.variable_expansion()

    @lexicon
    def subshell(cls):
        """A subshell ( ... )."""
        yield r'\)', Delimiter.End, -1
        yield from cls.root

    @lexicon
    def group_command(cls):
        """A group command { ...; }."""
        yield r'\}', Bracket.End, -1
        yield from cls.root

    # expressions
    @lexicon
    def arith_expr(cls):
        """An arithmetic expression (( ... ))."""
        yield r'\)\)', Delimiter.End, -1
        yield from cls.expression_common()
        yield from cls.variable_expansion()
        yield from cls.common()

    @lexicon
    def cond_expr(cls):
        """A conditional expression [[ ... ]]."""
        yield r'\]\]', Bracket.End, -1
        yield from cls.expression_common()
        yield from cls.variable_expansion()
        yield from cls.common()


    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        """A comment."""
        yield r'$', None, -1
        yield from cls.comment_common()



BASH_KEYWORDS = (
    "case", "coproc", "do", "done", "elif", "else", "esac", "fi", "for",
    "function", "if", "in", "select", "then", "until", "while", "time",
)

