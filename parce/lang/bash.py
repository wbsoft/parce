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
Bash and other UNIX shell (sh) syntax.

"""

__all__ = ('Bash',)

import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import *
from parce.rule import *


# Main source of information: man bash :-)


RE_NAME = r'[^\W\d]\w+'
RE_BRACE = (
    r'''([^|&;()<>\s"'`!{}]*)'''   # preamble
    r'(\{)'     # brace {
    r'(?:'
        r'(?:\w\.\.\w|\d+\.\.\d+)(?:\.\.\d+)?'   # sequence expr
        r'''|[^|&;()<>\s"'`!{}]*(?:,[^|&;()<>\s"'`!{}]*)+'''  # comma-separated strings
    r')'       # expand expr
    r'(\})'     # brace }
    r'''([^|&;()<>\s"'`!{}]*)'''   # postscript
)
RE_WORD = r'''[^|&;()<>\s$"'`!\\]+'''


class Bash(Language):
    """Bash and other shell syntax."""

    @lexicon(re_flags=re.MULTILINE)
    def root(cls):
        """Root lexicon, finds commands and arguments etc."""
        yield r'\A#!.*?$', Comment.Special
        yield r'(\w+)(=)', bygroup(Name.Variable.Definition, Operator.Assignment)
        yield r'let\b', Name.Builtin, cls.let_expr
        yield r'\.(?=$|\s)', Keyword, cls.arguments
        yield RE_NAME, findmember(TEXT, (
            (BASH_KEYWORDS, Keyword),
            (BASH_BUILTINS, Name.Builtin),
            (UNIX_COMMANDS, Name.Command),
            ), Name), cls.arguments
        yield r'\{(?=$|\s)', Bracket.Start, cls.group_command
        yield r'\[\[(?=$|\s)', Bracket.Start, cls.cond_expr
        yield from cls.common()

    @classmethod
    def common(cls):
        """Yield common stuff: comment, expression, expansions, etc."""
        yield '#', Comment, cls.comment
        yield RE_BRACE, using(cls.brace_expansion)
        yield r'\(\(', Delimiter.Start, cls.arith_expr
        yield r'\(', Delimiter.Start, cls.subshell

        yield from cls.substitution()
        yield from cls.quoting()
        yield r'-[\w-]+', Name.Property     # option
        yield RE_WORD, Text

    @classmethod
    def expression_common(cls):
        """Common things in expressions."""
        yield r'0\d+', Number.Octal
        yield r'0[xX][0-9a-fA-F]+', Number.Hexadecimal
        yield r'\d+#[0-9a-zA-Z@_]+', Number
        yield r'\d+', Number
        yield r'(\w+)[ \t]*(=)', bygroup(Name.Variable.Definition, Operator.Assignment)
        yield r'\w+', Name.Variable
        yield r',', Delimiter.Separator
        yield r'(?:[*/%+&\-|]|<<|>>)=', Operator.Assignment
        yield r'\+\+?|--?|\*\*?|<[=<]?|>[=>]?|&&?|\|\|?|[=!]=|[~!/%^?:]', Operator
        yield r'=', Operator.Assignment

    @classmethod
    def substitution(cls):
        """Variable expansion with ``$``."""
        yield r'(\$)(\(\()', bygroup(Name.Variable, Delimiter.Start), cls.arith_expr
        yield r'(\$)(\()',  bygroup(Name.Variable, Delimiter.Start), cls.subshell
        yield r'\$[*@#?\$!0-9-]', Name.Variable.Special
        yield r'\$\w+', Name.Variable
        yield r'\$\{', Name.Variable, cls.parameter
        yield r'`', Delimiter.Quote, cls.backtick

    @classmethod
    def quoting(cls):
        """Escape, single and double quotes."""
        yield r'\\.', Escape
        yield r'"', String.Start, cls.dqstring
        yield r"'", String.Start, cls.sqstring
        yield r"\$'", String.Start, cls.escape_string
        yield r'\$"', String.Start, cls.dqstring    # translated string

    @lexicon
    def brace_expansion(cls):
        """Used to parse a brace expansion."""
        yield from cls.substitution()
        yield from cls.quoting()
        yield default_action, Text.Preprocessed

    @lexicon(re_flags=re.MULTILINE)
    def arguments(cls):
        """Arguments after a command."""
        yield r';', Delimiter, -1
        yield r'$', None, -1
        yield r'\|\|?|\&\&?', Delimiter.Connection, -1
        yield from cls.common()
        yield '[ \t]+', skip
        yield default_target, -1

    @lexicon
    def dqstring(cls):
        """A double-quoted string."""
        yield r'"', String.End, -1
        yield r'\\[\\$`"\n]', String.Escape
        yield from cls.substitution()
        yield default_action, String

    @lexicon
    def sqstring(cls):
        """A single-quoted string."""
        yield r"'", String.End, -1
        yield default_action, String

    @lexicon
    def escape_string(cls):
        """A single-quoted string."""
        yield r"'", String.End, -1
        yield r'\\(?:[abeEfnrtv\\\"\'?]|\d{3}|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|c.)', String.Escape
        yield default_action, String

    @lexicon
    def backtick(cls):
        r"""Stuff between ````` ... `````."""
        yield r'`', Delimiter.Quote, -1
        yield from cls.root

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
        yield from cls.substitution()
        yield from cls.quoting()

    @lexicon
    def subshell(cls):
        """A subshell ``(`` ... ``)``."""
        yield r'\)', Delimiter.End, -1
        yield from cls.root

    @lexicon
    def group_command(cls):
        """A group command ``{ ...; }``."""
        yield r'\}', Bracket.End, -1
        yield from cls.root

    # expressions
    @lexicon(re_flags=re.MULTILINE)
    def let_expr(cls):
        """An expression after ``let``."""
        yield r'$', None, -1
        yield r';', Delimiter, -1
        yield from cls.expression_common()
        yield from cls.common()

    @lexicon
    def arith_expr(cls):
        """An arithmetic expression ``((`` ... ``))``."""
        yield r'\)\)', Delimiter.End, -1
        yield from cls.expression_common()
        yield from cls.common()

    @lexicon
    def cond_expr(cls):
        """A conditional expression ``[[`` ... ``]]``."""
        yield r'\]\]', Bracket.End, -1
        yield from cls.expression_common()
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

UNIX_COMMANDS = (
    "alias", "ar", "at", "awk", "basename", "bc", "bg", "cal", "cat", "cd",
    "chgrp", "chmod", "chown", "cksum", "cmp", "comm", "cp", "crontab",
    "csplit", "ctags", "cut", "dd", "df", "diff", "dirname", "du", "echo",
    "ed", "egrep", "env", "ex", "exit", "expr", "false", "fg", "file", "find",
    "fold", "fuser", "grep", "head", "iconv", "join", "kill", "lex", "ln",
    "logname", "lp", "ls", "m4", "make", "man", "mesg", "mkdir", "more", "mv",
    "nice", "nl", "nm", "od", "paste", "patch", "pax", "printf", "ps", "pwd",
    "rm", "rmdir", "sed", "sleep", "sort", "split", "strings", "strip", "tail",
    "talk", "tee", "test", "time", "touch", "tput", "tr", "true", "type",
    "umask", "uname", "uniq", "unset", "vi", "wait", "wc", "who", "write",
    "xargs", "yacc", "zip",
)

BASH_BUILTINS = (
    "source", "alias", "bg", "bind", "break", "builtin", "caller", "cd",
    "command", "compgen", "complete", "compopt", "continue", "declare",
    "typeset", "dirs", "disown", "echo", "enable", "exec", "exit", "export",
    "fc", "fg", "getopts", "hash", "help", "history", "jobs", "kill", "let",
    "local", "logout", "mapfile", "readarray", "popd", "printf", "pushd",
    "pwd", "read", "readonly", "return", "set", "shift", "shopt", "suspend",
    "test", "times", "trap", "type", "ulimit", "umask", "unalias", "unset",
    "wait",
)

