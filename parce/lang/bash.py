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


RE_NAME = r'[^\W\d]\w*(?:[-.+]\w+)*'
RE_COMMAND = r'''[^\s|&;()<>$"'`#][^\s|&;()<>$"'`]*'''
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
        """Find one or mode command lines.

        This lexicon is derived with the special character ````` if called from
        the :meth:`backtick` lexicon, or with ```)``` from the :meth:`subshell`
        lexicon.

        """
        yield r'\A#!.*?$', Comment.Special
        yield '#', Comment, cls.comment
        yield '\n', skip
        yield default_target, derive(cls.command, ARG)

    @lexicon(re_flags=re.MULTILINE)
    def command(cls):
        """Find commands and arguments, pops back on line end or when ARG is ahead."""
        arguments = derive(cls.arguments, ARG)  # pass on the ` to arguments lexicon
        yield r'\\\n', Whitespace.Escape
        yield r'[ \t]+', skip
        yield '$', None, -1
        yield r';', Delimiter, -1
        yield arg(prefix='(?=', suffix=')'), None, -1
        yield '#', Comment, cls.comment
        yield r'(\w+)(=)', bygroup(Name.Variable.Definition, Operator.Assignment), cls.assignment
        yield r'let\b', Name.Builtin, cls.let_expr
        yield r'\.(?=$|\s)', Keyword, arguments
        yield r'exec\b', Name.Builtin
        yield r'(local|export)[ \t]+(\w+)(=)?', bygroup(Name.Builtin, Name.Variable.Definition, Operator.Assignment), \
            ifgroup(3, cls.assignment)
        yield r'({})(\(\))?(?=\s|$)'.format(RE_NAME), ifgroup(2,
            bygroup(findmember(TEXT, (
                (BASH_KEYWORDS, Keyword.Invalid),
                (BASH_BUILTINS, Name.Builtin.Invalid),
                ), Name.Function.Definition), Bracket),
            findmember(TEXT, (
                (BASH_KEYWORDS, Keyword),
                (BASH_BUILTINS, (Name.Builtin, arguments)),
                (UNIX_COMMANDS, (Name.Command.Definition, arguments)),
                ), (Name.Command, arguments)))
        yield r'\{(?=$|\s)', Bracket.Start, cls.group_command
        yield r'\[\[(?=$|\s)', Bracket.Start, cls.cond_expr
        yield r'\[(?=$|\s)', Bracket.Start, cls.test_expr
        yield RE_COMMAND, Name.Command, arguments
        yield r'\(', Delimiter.Start, cls.subshell
        yield r'\|\|?|\&\&?', Delimiter.Connection, -1
        yield default_target, arguments

    @lexicon(re_flags=re.MULTILINE)
    def arguments(cls):
        """Arguments after a command, called from root."""
        yield arg(prefix='(?=', suffix=')'), None, -2
        yield r'\\\n', Whitespace.Escape
        yield r'[ \t]+', skip
        yield from cls.common()
        yield default_target, -1

    @classmethod
    def common(cls):
        """Yield common stuff: comment, expression, expansions, etc."""
        yield '#', Comment, cls.comment
        yield RE_BRACE, using(cls.brace_expansion)
        yield r'\(\(', Delimiter.Start, cls.arith_expr

        yield r'(\{\w+\}|\d+)?(<<<)[ \t]*', bygroup(Name.Identifier, Delimiter.Direction), cls.here_string
        yield r'(\{\w+\}|\d+)?(<<-?)[ \t]*(?=(\w+)|"([^"\n]+)"|' r"'([^'\n]+)')", \
            bygroup(Name.Identifier, Delimiter.Direction), \
            derive(ifgroup(3, cls.here_document, cls.here_document_quoted),
                   call(cls.make_heredoc_regex, MATCH)), \
            cls.command, cls.arguments
        yield r'(\{\w+\}|\d+)?(&>>?|[<>][&>]?)(\d?-?)', bygroup(Name.Identifier, Delimiter.Direction, Name.Identifier)
        yield from cls.substitution()
        yield from cls.quoting()
        yield r'-[\w-]+', Name.Property     # option
        is_pattern = lambda t: '*' in t or '?' in t or '[' and ']' in t
        yield RE_WORD, select(call(is_pattern, TEXT), Text, Text.Template)

    @classmethod
    def numeric_common(cls):
        """Nummeric values."""
        yield r'0\d+', Number.Octal
        yield r'0[xX][0-9a-fA-F]+', Number.Hexadecimal
        yield r'\d+#[0-9a-zA-Z@_]+', Number
        yield r'\d+', Number

    @classmethod
    def expression_common(cls):
        """Common things in expressions."""
        yield from cls.numeric_common()
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
        yield r'(\$\{)([!#@*])?(\w*)', bygroup(Name.Variable, Delimiter.ModeChange, Name.Variable), cls.parameter
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

    @classmethod
    def make_heredoc_regex(cls, m):
        """Make a regular expression to terminate the here doc with.

        The returned pattern is used to terminate the both here_document
        lexicons with.

        """
        pat = m.group(m.lastindex + 5) or m.group(m.lastindex + 4) or m.group(m.lastindex + 3)
        if m.group(m.lastindex + 2) == "<<-":
            # allow stripping tabs from doc and delimiter
            return r'^\t*(' + re.escape(pat) +  r')[\t ]*$'
        else:
            return r'^(' + re.escape(pat) + r')[\t ]*$'

    @lexicon(re_flags=re.MULTILINE)
    def here_document(cls):
        """A here document that is expanded, terminated by ARG."""
        yield arg(escape=False), bygroup(Name.Identifier), -1
        yield from cls.substitution()
        yield default_action, Verbatim

    @lexicon(re_flags=re.MULTILINE)
    def here_document_quoted(cls):
        """A here document that's not expanded, terminated by ARG."""
        yield arg(escape=False), bygroup(Name.Identifier), -1
        yield default_action, Verbatim

    @lexicon(re_flags=re.MULTILINE)
    def here_string(cls):
        """A here-string, the text after ``<<<``."""
        yield from cls.substitution()
        yield from cls.quoting()
        yield RE_WORD, Verbatim
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def assignment(cls):
        """An assignment, the text after ``=``."""
        yield from cls.substitution()
        yield from cls.quoting()
        yield from cls.numeric_common()
        yield RE_WORD, Verbatim
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
        yield from cls.root('`')

    @lexicon
    def parameter(cls):
        """Contents of ``${`` ... ``}``."""
        yield r'\}', Name.Variable, -1
        yield r'\d+', Number
        yield from cls.substitution()
        yield r'\[', Delimiter.Bracket.Start, cls.subscript
        yield r':[-=?+]?|##?|%%?|\^\^?|,,?|@', Delimiter.ModeChange
        is_pattern = lambda t: '*' in t or '?' in t or '[' and ']' in t
        yield r'[\w*\.?\[\]]+',  select(call(is_pattern, TEXT), Name.Variable, Text.Template)

    @lexicon
    def subscript(cls):
        """Contents of ``[`` ... ``]`` in an array reference."""
        yield r'\]', Delimiter.Bracket.End, -1
        yield '[@*]', Character.Special # makes sense in ${bla[@]}
        yield from cls.expression_common()
        yield from cls.substitution()
        yield from cls.quoting()

    @lexicon
    def subshell(cls):
        """A subshell ``(`` ... ``)``."""
        yield r'\)', Delimiter.End, -1
        yield from cls.root(')')

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

    @lexicon
    def test_expr(cls):
        """A test expression ``[`` ... ``]``."""
        yield r'\]', Bracket.End, -1
        yield r'-[\w-]+', Name.Property     # option
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

