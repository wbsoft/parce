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
Parser for LilyPond syntax.
"""


import re


from parce import *


RE_LILYPOND_ID_RIGHT_BOUND = r"(?![_-]?[^\W\d])"
RE_LILYPOND_ID = r"[^\W\d_]+(?:[_-][^\W\d_]+)*"
RE_LILYPOND_VARIABLE = RE_LILYPOND_ID + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_COMMAND = r"\\(" + RE_LILYPOND_ID + ")" + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_MARKUP_TEXT = r'[^{}"\\\s#%]+'


class LilyPond(Language):

    @lexicon
    def root(cls):
        """Toplevel LilyPond document."""
        yield from cls.common()
        yield from cls.blocks()
        yield RE_LILYPOND_VARIABLE, Variable, cls.varname
        yield "=", Operator.Assignment
        yield r"\\version\b", Keyword

    @classmethod
    def blocks(cls):
        yield r"(\\book(?:part)?)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.book
        yield r"(\\score)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.score
        yield r"(\\header)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.header
        yield r"(\\paper)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.paper
        yield r"(\\layout)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.layout
        yield r"(\\midi)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.midi

    @lexicon
    def book(cls):
        """Book or bookpart."""
        yield r'\}', Delimiter.CloseBrace, -1
        yield from cls.common()
        yield from cls.blocks()

    @lexicon
    def score(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield from cls.blocks()

    @lexicon
    def header(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield RE_LILYPOND_VARIABLE, Variable, cls.varname
        yield "=", Operator.Assignment
        yield from cls.common()

    @lexicon
    def paper(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield from cls.base()

    @lexicon
    def layout(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield from cls.base()

    @lexicon
    def midi(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield from cls.base()


    @classmethod
    def base(cls):
        """Find comment, string and scheme."""
        yield r'%\{', Comment, cls.multiline_comment
        yield r'%', Comment, cls.singleline_comment
        yield r'"', String, cls.string
        yield r'[#$]', Delimiter.SchemeStart, cls.scheme

    @classmethod
    def common(cls):
        """Find comment, string, scheme and markup."""
        yield from cls.base()
        yield r"\\markup(lines|list)?" + RE_LILYPOND_ID_RIGHT_BOUND, Keyword.Markup, cls.markup

    @lexicon
    def varname(cls):
        """bla.bla.bla syntax."""
        yield r'\s*(\.)\s*(' + RE_LILYPOND_VARIABLE + ')', bygroup(Delimiter.Dot, Variable)
        yield default_target, -1
        
    # -------------------- markup --------------------
    @lexicon
    def markup(cls):
        """Markup without environment. Try to guess the n of arguments."""
        yield r'\{', Delimiter.OpenBrace, -1, cls.markup_environ
        yield RE_LILYPOND_COMMAND, cls.get_markup_action(), cls.get_markup_target()
        yield r'"', String, -1, cls.string
        yield r'[#$]', Delimiter.SchemeStart, -1, cls.scheme
        yield r'%\{', Comment, cls.multiline_comment
        yield r'%', Comment, cls.singleline_comment
        yield RE_LILYPOND_MARKUP_TEXT, Text, -1

    @classmethod
    def get_markup_target(cls):
        """Get the target for a markup command."""
        def test(m):
            command = m.group(m.lastindex + 1)
            return cls.get_markup_argument_count(command)
        return tomatch(test, -1, 0, 1, 2, 3)

    @classmethod
    def get_markup_argument_count(cls, command):
        """Return the number of arguments the markup command (without \\) expects."""
        from . import lilypond_words
        for i in range(5):
            if command in lilypond_words.markupcommands_nargs[i]:
                return i
        return 1    # assume a user command has no arguments

    @lexicon
    def markup_environ(cls):
        """Markup until } ."""
        yield r'\}', Delimiter.CloseBrace, -1
        yield r'\{', Delimiter.OpenBrace, 1
        yield RE_LILYPOND_COMMAND, cls.get_markup_action()
        yield from cls.base()
        yield RE_LILYPOND_MARKUP_TEXT, Text

    @classmethod
    def get_markup_action(cls):
        """Get the action for a command in \markup { }."""
        def test(m):
            from . import lilypond_words
            text = m.group(m.lastindex + 1)
            return text in lilypond_words.markupcommands
        return bymatch(test, Function, Function.Markup)


    # -------------- Scheme ---------------------
    @lexicon
    def scheme(cls):
        from .scheme import SchemeLily
        yield from SchemeLily.one_arg()
        yield default_target, -1
        
    @lexicon
    def schemelily(cls):
        """LilyPond from scheme.SchemeLily #{ #}."""
        yield r"#}", Delimiter.LilyPond, -1
        yield from cls.root

    # -------------- String ---------------------
    @lexicon
    def string(cls):
        yield r'"', String, -1
        yield from cls.string_common()

    @classmethod
    def string_common(cls):
        yield r'\\[\\"]', String.Escape
        yield default_action, String

    # -------------- Comment ---------------------
    @lexicon
    def multiline_comment(cls):
        yield r'%}', Comment, -1
        yield from cls.comment_common()

    @lexicon(re_flags=re.MULTILINE)
    def singleline_comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1

    @classmethod
    def comment_common(cls):
        yield default_action, Comment


