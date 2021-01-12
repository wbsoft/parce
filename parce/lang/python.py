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
Parse Python.

"""

__all__ = ('Python', 'PythonConsole')

import re

from parce import lexicon, Language, skip, default_action, default_target
from parce.action import (
    Character, Comment, Data, Delimiter, Escape, Invalid, Keyword, Literal,
    Name, Number, Operator, String, Whitespace)
from parce.rule import (
    ARG, MATCH, TEXT, arg, bygroup, call, derive, dselect, findmember, ifarg,
    ifeq, ifgroup, ifmember, pattern, select, words)

from . import python_words


RE_PYTHON_IDENTIFIER = _I_ = r'[^\W\d]\w*'
RE_PYTHON_HORIZ_SPACE = _S_ = r'[^\S\n]'
RE_PYTHON_LINE_CONTINUATION = _N_ = r'\\\n'
_SN_ = fr'(?:{_S_}|{_N_})'


Bytes = Data.Bytes


class Python(Language):
    @lexicon(re_flags=re.MULTILINE)
    def root(cls):
        yield fr'^{_S_}+($|(?=#))?', ifgroup(1, Whitespace, Whitespace.Indent)
        yield r'@', Name.Decorator, cls.decorator
        yield fr'(class\b){_S_}*({_I_})', bygroup(Keyword,
            ifmember(MATCH[2], python_words.keywords, Invalid, Name.Class.Definition)), cls.classdef
        yield fr'(def\b){_S_}*({_I_})', bygroup(Keyword,
            ifmember(MATCH[2], python_words.keywords, Invalid, Name.Function.Definition)), cls.funcdef
        yield fr':(?={_S_}*(?:$|#))', Delimiter.Indent
        yield fr'({_I_})\s*(=)', bygroup(
            select(call(str.isupper, TEXT),
                   select(call(isclassname, TEXT), Name.Variable, Name.Class),
                   Name.Constant),
            Operator.Assignment)
        yield from cls.common()

    @classmethod
    def common(cls):
        yield r'#', Comment, cls.comment
        yield fr'({_N_})(\s*)', bygroup(Escape, Whitespace)
        yield r'\[', Delimiter, cls.list
        yield r'\(', Delimiter, cls.tuple
        yield r'\{', Delimiter, cls.dict

        ## string literals
        yield from cls.find_string_literals()
        yield from cls.find_bytes_literals()

        ## numerical values
        yield '0[oO](?:_?[0-7])+', Number.Octal
        yield '0[bB](?:_?[01])+', Number.Binary
        yield '0[xX](?:_?[0-9a-fA-F])+', Number.Hexadecimal
        yield r'(?:\.\d(?:_?\d)*|\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?)(?:[eE][-+]\d(?:_?\d)*)?[jJ]?', Number

        ## keywords, variables, functions
        yield words(python_words.keywords, prefix=r'\b', suffix=r'\b'), Keyword
        yield words(python_words.constants, prefix=r'\b', suffix=r'\b'), Name.Constant
        yield fr'\b(self|cls)\b(?:{_SN_}*([\[\(]))?', Name.Variable.Special, \
            dselect(MATCH[2], {'(': cls.call, '[': cls.item})
        # method, class or attribute (keywords after a . are also caught)
        yield fr'(\.){_SN_}*\b({_I_})\b(?:{_SN_}*([\[\(]))?', \
            bygroup(
                Delimiter,
                ifmember(MATCH[2], python_words.keywords,
                    Keyword,
                    dselect(MATCH[3], {'(': select(call(isclassname, TEXT), Name.Method, Name.Class)},
                         select(call(str.isupper, TEXT),
                             select(call(isclassname, TEXT), Name.Attribute, Name.Class),
                             Name.Constant))),
                Delimiter), \
            dselect(MATCH[3], {'(': cls.call, '[': cls.item})
        # function, class or variable
        yield fr'\b({_I_})\b(?:{_SN_}*([\[\(]))?', \
            bygroup(
                findmember(MATCH[1],
                    ((python_words.builtins, Name.Builtin),
                     (python_words.exceptions, Name.Exception)),
                    select(call(str.isupper, TEXT),
                        select(call(isclassname, TEXT),
                            dselect(MATCH[2], {'(': Name.Function}, Name.Variable),
                            Name.Class),
                        Name.Constant)),
                Delimiter), \
            dselect(MATCH[2], {'(': cls.call, '[': cls.item})

        ## delimiters, operators
        yield r'\.\.\.', Delimiter.Special.Ellipsis
        yield r'(?:\*\*|//|<<|>>|[-+*/%@&|^:])?=', Operator.Assignment
        yield r'\*\*|//|<<|>>|[<>=!]=|[-+*/%@&|^~<>]', Operator
        yield r'[.;,:]', Delimiter

    @lexicon(re_flags=re.MULTILINE)
    def decorator(cls):
        """A decorator."""
        yield _I_, Name.Decorator
        yield r'\[', Delimiter, cls.item
        yield r'\(', Delimiter, cls.call
        yield r'\.', Delimiter
        yield '$', None, -1
        yield r'\\\n', Escape
        yield r'#', Comment, -1, cls.comment

    @lexicon
    def funcdef(cls):
        """A function definition."""
        yield r'\(', Delimiter, cls.signature
        yield r'->', Delimiter.Annotation
        yield r':', Delimiter.Indent, -1
        yield r'#', Comment, -1, cls.comment
        yield from cls.common()

    @lexicon
    def signature(cls):
        """A function signature."""
        yield r'\)', Delimiter, -1
        yield r':', Delimiter.Annotation
        yield from cls.common()

    @lexicon
    def classdef(cls):
        """A class definition."""
        yield r'\(', Delimiter, cls.bases
        yield ":", Delimiter.Indent, -1
        yield r'#', Comment, -1, cls.comment
        yield from cls.common()

    @lexicon
    def bases(cls):
        """The base classes in a class definition."""
        yield r'\)', Delimiter, -1
        yield from cls.common()

    ## ------ expressions -----------
    @lexicon
    def item(cls):
        """Stuff between xxx[ and ] (getitem)."""
        yield r'\]', Delimiter, -1
        yield from cls.common()

    @lexicon
    def call(cls):
        """Stuff between xxx( and ) (call)."""
        yield r'\)', Delimiter, -1
        yield from cls.common()

    ## ----- item types -------------
    @lexicon
    def list(cls):
        yield r'\]', Delimiter, -1
        yield ',', Delimiter
        yield from cls.common()

    @lexicon
    def tuple(cls):
        yield r'\)', Delimiter, -1
        yield ',', Delimiter
        yield from cls.common()

    @lexicon
    def dict(cls):
        yield r'\}', Delimiter, -1
        yield '[,:]', Delimiter
        yield from cls.common()

    ## ------- strings --------------
    @classmethod
    def find_string_literals(cls, target=None, allow_newlines=None):
        """Find string literals."""
        # short strings not closed on the same line are invalid
        yield r'''[rRuUfF]{,2}["']$''', String.Invalid

        if target is None:
            target = cls.string(allow_newlines)

        # long strings
        yield r'(\b[rR])("""|'r"''')", \
            bygroup(String.Prefix, String.Start), \
            target, derive(cls.long_string_raw, MATCH[2])
        yield r'(\b(?:[fF][rR])|(?:[rR][fF]))("""|'r"''')", \
            bygroup(String.Prefix, String.Start), \
            target, derive(cls.long_string_raw_format, MATCH[2])
        yield r'(\b[uU])?("""|'r"''')", \
            bygroup(String.Prefix, String.Start), \
            target, derive(cls.long_string, MATCH[2])
        yield r'(\b[fF])("""|'r"''')", \
            bygroup(String.Prefix, String.Start), \
            target, derive(cls.long_string_format, MATCH[2])

        # short strings
        yield r'''(\b[rR])(['"])''', \
            bygroup(String.Prefix, String.Start), \
            target, derive(cls.short_string_raw, MATCH[2])
        yield r'''(\b(?:[fF][rR])|(?:[rR][fF]))(['"])''', \
            bygroup(String.Prefix, String.Start), \
            target, derive(cls.short_string_raw_format, MATCH[2])
        yield r'''(\b[uU])?(['"])''', \
            bygroup(String.Prefix, String.Start), \
            target, derive(cls.short_string, MATCH[2])
        yield r'''(\b[fF])(['"])''', \
            bygroup(String.Prefix, String.Start), \
            target, derive(cls.short_string_format, MATCH[2])

    @lexicon
    def string(cls):
        """All strings end here, check [slice] notation and concatenated literals."""
        yield _N_, Escape
        yield ifarg(r'\s+', r'[ \t]+'), skip    # allow newline inside arglists, tuples, etc
        yield from cls.find_string_literals(0)
        yield r'\[', Delimiter, cls.item
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def short_string(cls):
        yield from cls.string_escape()
        yield from cls.short_string_common()

    @lexicon(re_flags=re.MULTILINE)
    def short_string_raw(cls):
        yield from cls.short_string_raw_common()

    @lexicon(re_flags=re.MULTILINE)
    def short_string_format(cls):
        yield from cls.string_formatstring()
        yield from cls.string_escape()
        yield from cls.short_string_common()

    @lexicon(re_flags=re.MULTILINE)
    def short_string_raw_format(cls):
        yield from cls.string_formatstring()
        yield from cls.short_string_raw_common()

    @classmethod
    def short_string_common(cls):
        yield arg(), String.End, -1
        yield pattern(ifeq(ARG, "'", r"[^']*?$", r'[^"]*?$')), String.Invalid, -1
        yield default_action, String

    @classmethod
    def short_string_raw_common(cls):
        yield arg(), String.End, -1
        yield r'\\\\', String
        yield pattern(ifeq(ARG, "'", fr"([^\\']*?|\\'{_S_}*)$", fr'([^\\"]*?|\\"{_S_}*)$')), String.Invalid, -1
        yield arg(prefix=r'\\'), String  # escape quote, but the \ remains
        yield default_action, String

    @lexicon
    def long_string(cls):
        yield from cls.string_escape()
        yield from cls.long_string_common()

    @lexicon
    def long_string_raw(cls):
        yield arg(prefix=r'\\'), String  # escape quote, but the \ remains
        yield from cls.long_string_common()

    @lexicon
    def long_string_format(cls):
        yield from cls.string_formatstring()
        yield from cls.string_escape()
        yield from cls.long_string_common()

    @lexicon
    def long_string_raw_format(cls):
        yield arg(prefix=r'\\'), String  # escape quote, but the \ remains
        yield from cls.string_formatstring()
        yield from cls.long_string_common()

    @classmethod
    def long_string_common(cls):
        yield arg(), String.End, -1
        yield default_action, String

    # ------ stuff common for short and long strings ---------
    @classmethod
    def string_escape(cls):
        yield from cls.bytes_escape(String.Escape)
        yield r'\\N\{[^\}]+\}', String.Escape
        yield r'\\u[0-9a-fA-F]{4}', String.Escape
        yield r'\\U[0-9a-fA-F]{8}', String.Escape

    @classmethod
    def string_formatstring(cls):
        yield r'\{\{|\}\}', String.Escape
        yield r'\{', Delimiter.Template, cls.string_format_expr

    @lexicon
    def string_format_expr(cls):
        yield '![sra]', Character
        yield ':', Delimiter, cls.string_format_spec
        yield r'\}', Delimiter.Template, -1
        yield from cls.common()

    @lexicon
    def string_format_spec(cls):
        yield r'\{', Delimiter, cls.string_format_spec_nested
        yield r'\}', Delimiter.Template, -2
        yield from cls.common() # TODO maybe really parse format strings

    @lexicon
    def string_format_spec_nested(cls):
        yield r'\}', Delimiter, -1
        yield from cls.common()

    # ----------------- bytes --------------------
    @classmethod
    def find_bytes_literals(cls, target=None, allow_newlines=None):
        """Find bytes literals."""
        # short bytes not closed on the same line are invalid
        yield r'''[rRbB]{,2}["']$''', Bytes.Invalid

        if target is None:
            target = cls.bytes(allow_newlines)

        # long bytes
        yield r'(\b(?:[bB][rR])|(?:[rR][bB]))("""|'r"''')", \
            bygroup(Bytes.Prefix, Bytes.Start), \
            target, derive(cls.long_bytes_raw, MATCH[2])
        yield r'(\b[bB])("""|'r"''')", \
            bygroup(Bytes.Prefix, Bytes.Start), \
            target, derive(cls.long_bytes, MATCH[2])

        # short bytes
        yield r'''(\b(?:[bB][rR])|(?:[rR][bB]))(['"])''', \
            bygroup(Bytes.Prefix, Bytes.Start), \
            target, derive(cls.short_bytes_raw, MATCH[2])
        yield r'''(\b[bB])(['"])''', \
            bygroup(Bytes.Prefix, Bytes.Start), \
            target, derive(cls.short_bytes, MATCH[2])

    @lexicon
    def bytes(cls):
        """All bytes end here, check [slice] notation and concatenated literals."""
        yield _N_, Escape
        yield ifarg(r'\s+', r'[ \t]+'), skip    # allow newline inside arglists, tuples, etc
        yield from cls.find_bytes_literals(0)
        yield r'\[', Delimiter, cls.item
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def short_bytes(cls):
        yield from cls.bytes_escape()
        yield from cls.short_bytes_common()

    @lexicon(re_flags=re.MULTILINE)
    def short_bytes_raw(cls):
        yield from cls.short_bytes_raw_common()

    @lexicon
    def long_bytes(cls):
        yield from cls.bytes_escape()
        yield from cls.long_bytes_common()

    @lexicon
    def long_bytes_raw(cls):
        yield from cls.long_bytes_common()

    @classmethod
    def short_bytes_common(cls):
        yield arg(), Bytes.End, -1
        yield pattern(ifeq(ARG, "'", r"[^']*?$", r'[^"]*?$')), Bytes.Invalid, -1
        yield default_action, Bytes

    @classmethod
    def short_bytes_raw_common(cls):
        yield r'\\\\', Bytes
        yield pattern(ifeq(ARG, "'", fr"([^\\']*?|\\'{_S_}*)$", fr'([^\\"]*?|\\"{_S_}*)$')), Bytes.Invalid, -1
        yield arg(prefix=r'\\'), Bytes  # escape quote, but the \ remains
        yield from cls.long_bytes_common()

    @classmethod
    def long_bytes_common(cls):
        yield arg(), Bytes.End, -1
        yield default_action, Bytes

    @classmethod
    def bytes_escape(cls, action=Bytes.Escape):
        yield r'''\\[\n\\'"abfnrtv]''', action
        yield r'\\\d{1,3}', action
        yield r'\\x[0-9a-fA-F]{2}', action

    ## ------- comments -------------
    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1


class PythonConsole(Python):
    """Python console input and output with prompt."""
    @classmethod
    def common(cls):
        yield r'(?:(?<=\n)|^)(?:>>>|\.\.\.) ', Literal.Prompt
        yield from super().common()

    @classmethod
    def longstring_common(cls):
        yield r'(?:(?<=\n)|^)\.\.\. ', Literal.Prompt
        yield from super().longstring_common()

    @classmethod
    def longbytes_common(cls):
        yield r'(?:(?<=\n)|^)\.\.\. ', Literal.Prompt
        yield from super().longbytes_common()


def isclassname(text):
    """Return True if text starts with uppercase letter.

    Starting underscores are skipped.

    """
    for c in text:
        if c.isupper():
            return True
        elif c != '_':
            return False
    return False


