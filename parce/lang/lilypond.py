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
Parser for LilyPond syntax.
"""


import re

from parce import *

from . import lilypond_words


SKIP_WHITESPACE = (r"\s+", skip)

RE_FRACTION = r"\d+/\d+"

RE_LILYPOND_ID_RIGHT_BOUND = r"(?![_-]?[^\W\d])"
RE_LILYPOND_ID = r"[^\W\d_]+(?:[_-][^\W\d_]+)*"
RE_LILYPOND_VARIABLE = RE_LILYPOND_ID + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_COMMAND = r"\\(" + RE_LILYPOND_ID + ")" + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_MARKUP_TEXT = r'[^{}"\\\s#%]+'

RE_LILYPOND_DYNAMIC = (
    r"\\[<!>]|"
    r"\\(f{1,5}|p{1,5}"
    r"|mf|mp|fp|spp?|sff?|sfz|rfz"
    r"|cresc|decresc|dim|cr|decr"
    r")(?![A-Za-z])")

RE_LILYPOND_REST = r"[rRs](?![^\W\d])"

# a string that could be a valid pitch name (or drum name)
RE_LILYPOND_PITCHWORD = r"(?<![^\W\d])[a-zé]+(?:-[a-zé]+)*(?![^\W\d])"

# a pitch name followed by an optional octave (two capturing groups)
RE_LILYPOND_PITCH_OCT = "(" + RE_LILYPOND_PITCHWORD + r")\s*('+|,+)?"

RE_LILYPOND_DURATION = \
    r"(\\(maxima|longa|breve)\b|(1|2|4|8|16|32|64|128|256|512|1024|2048)(?!\d))"


# Standard actions used here:
Rest = Name.Rest
Pitch = Name.Pitch
Octave = Pitch.Octave
OctaveCheck = Pitch.Octave.OctaveCheck
Accidental = Pitch.Accidental
Context = Name.Constant.Context
Grob = Name.Object.Grob
Duration = Number.Duration
Duration.Dot
Duration.Scaling
Dynamic = Name.Command.Dynamic
LyricText = Text.LyricText
Spanner = Delimiter.Spanner
Spanner.Slur
Spanner.Ligature
Spanner.Tie
Direction = Delimiter.Direction
Script = Char.Script
Fingering = Number.Fingering


class LilyPond(Language):

    @lexicon
    def root(cls):
        """Toplevel LilyPond document."""
        yield from cls.blocks()
        yield RE_LILYPOND_VARIABLE, Name.Variable
        yield "[,.]", Delimiter
        yield "=", Operator.Assignment
        yield r"\\version\b", Keyword
        yield from cls.music()

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
        yield from cls.music()

    @lexicon
    def header(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield RE_LILYPOND_VARIABLE, Name.Variable
        yield "[,.]", Delimiter
        yield "=", Operator.Assignment
        yield from cls.common()

    @lexicon
    def paper(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield RE_LILYPOND_VARIABLE, Name.Variable
        yield "[,.]", Delimiter
        yield "=", Operator.Assignment
        yield from cls.common()
        yield from cls.commands()

    @lexicon
    def layout(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield r"(\\context)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.layout_context
        yield from cls.music()

    @lexicon
    def midi(cls):
        yield r'\}', Delimiter.CloseBrace, -1
        yield r"(\\context)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.layout_context
        yield from cls.music()

    @lexicon
    def layout_context(cls):
        r"""Contents of \layout or \midi { \context { } } or \with. { }."""
        yield r'\}', Delimiter.CloseBrace, -1
        yield words(lilypond_words.contexts, prefix=r"\\", suffix=r"\b"), Context
        yield words(lilypond_words.grobs), Grob
        yield words(lilypond_words.keywords, prefix=r"\\", suffix=r"(?![^\W\d])"), Keyword
        yield RE_LILYPOND_VARIABLE, Name.Variable, cls.varname
        yield "(=)(?:\s*("+RE_FRACTION+"|\d+))?", bygroup(Operator.Assignment, Number)
        yield from cls.common()
        yield from cls.commands()

    # ------------------ commands that can occur in all input modes --------
    @classmethod
    def commands(cls):
        """Yield commands that can occur in all input modes."""
        pitch = bytext(cls.is_pitch, Name.Symbol, Pitch)
        yield RE_LILYPOND_DYNAMIC, Dynamic
        # TODO: find special commands like, \repeat
        yield r"\\(?:un)?set(?![^\W\d])", Keyword, cls.set_unset
        yield r"\\(?:override|revert)(?![^\W\d])", Keyword, cls.override
        yield r"\\(?:new|change|context)(?![^\W\d])", Keyword, cls.context
        yield r"(\\with)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), cls.layout_context
        yield r"(\\relative)(?![^\W\d])(?:\s+" + RE_LILYPOND_PITCH_OCT + ")?", \
            bygroup(Keyword, pitch, Octave)
        yield (r"(\\transpose)(?![^\W\d])(?:\s+" + RE_LILYPOND_PITCH_OCT + ")?"
               "(?:\s*" + RE_LILYPOND_PITCH_OCT + ")?"), \
               bygroup(Keyword, pitch, Octave, pitch, Octave)
        yield r"\\tempo(?![^\W\d])", Keyword, cls.tempo
        yield r"(\\lyric(?:mode|s))\b\s*(\\s(?:equential|imultaneous)\b)?\s*(\{|<<)?", \
            bygroup(Keyword.Lyric, Keyword, Delimiter.OpenBrace), \
            ifgroup(3, cls.lyrics)
        yield r"\\lyricsto\b", Keyword.Lyric, cls.lyricsto
        yield words(lilypond_words.keywords, prefix=r"\\", suffix=r"(?![^\W\d])"), Keyword
        yield RE_LILYPOND_COMMAND, Name.Command

    # ------------------ music ----------------------
    @classmethod
    def music(cls):
        """Musical items."""
        yield from cls.common()
        yield r"<<", Delimiter.OpenBrace, cls.simultaneous
        yield r"<", Delimiter.OpenChord, cls.chord
        yield r"\{", Delimiter.OpenBrace, cls.sequential
        yield r"\\\\", Delimiter.VoiceSeparator
        yield r"\\[\[\]]", Spanner.Ligature
        yield r"[\[\]]", Spanner.Beam
        yield r"\\[()]", Spanner.Slur.Phrasing
        yield r"[()]", Spanner.Slur
        yield r"~", Spanner.Tie
        yield r"[-_^]", Direction, cls.script
        yield r"q(?![^\W\d])", Pitch
        yield RE_LILYPOND_REST, Rest
        yield RE_LILYPOND_PITCHWORD, bytext(cls.is_pitch, (Name.Symbol,), (Pitch, cls.pitch))
        yield words(lilypond_words.contexts), Context
        yield words(lilypond_words.grobs), Grob
        yield r'[.,]', Delimiter
        yield r'=', Operator.Assignment
        yield RE_FRACTION, Number
        yield RE_LILYPOND_DURATION, Duration, cls.duration_dots
        yield r"\d+", Number
        yield from cls.commands()

    @lexicon
    def sequential(cls):
        """A { } construct."""
        yield r"\}", Delimiter.CloseBrace, -1
        yield from cls.music()

    @lexicon
    def simultaneous(cls):
        """A << >> construct."""
        yield r">>", Delimiter.CloseBrace, -1
        yield from cls.music()

    @lexicon
    def chord(cls):
        """A < chord > construct."""
        yield r">", Delimiter.CloseChord, -1
        yield from cls.music()

    # ------------------ special commands ---------------
    @lexicon
    def tempo(cls):
        """Find content after a tempo command."""
        yield SKIP_WHITESPACE
        yield from cls.common() # markup, scheme, string, comment
        yield RE_LILYPOND_DURATION, Duration, cls.duration_dots
        yield r"(=)\s*(?:(\d+)(?:\s*(-)\s*(\d+))?)?", bygroup(
            Operator.Assignment, Number, Operator, Number), -1
        yield default_target, -1

    @lexicon
    def context(cls):
        """\\new, \\change, \\context Context [="name"] stuff."""
        yield SKIP_WHITESPACE
        yield words(lilypond_words.contexts), Context
        yield "=", Operator.Assignment
        yield r"(\\with)\s*(\{)", bygroup(Keyword, Delimiter.OpenBrace), -1, cls.layout_context
        yield from cls.common()
        yield default_target, -1

    @lexicon
    def set_unset(cls):
        """\\set, \\unset."""
        yield SKIP_WHITESPACE
        yield words(lilypond_words.contexts), Context
        yield r'[.,]', Delimiter
        yield "(=)(?:\s*("+RE_FRACTION+"|\d+))?", bygroup(Operator.Assignment, Number)
        yield RE_LILYPOND_VARIABLE + "(?=\s*([,.=])?)", Name.Variable, bymatch(
            (lambda m: bool(m.group(m.lastindex + 1))), -1, 0)
        yield default_target, -1

    @lexicon
    def override(cls):
        """\\override, \\revert."""
        yield SKIP_WHITESPACE
        yield words(lilypond_words.contexts), Context
        yield words(lilypond_words.grobs), Grob
        yield r'[.,]', Delimiter
        yield "(=)(?:\s*("+RE_FRACTION+"|\d+))?", bygroup(Operator.Assignment, Number)
        yield RE_LILYPOND_VARIABLE + "(?=\s*([,.=])?)", Name.Variable, bymatch(
            (lambda m: bool(m.group(m.lastindex + 1))), -1, 0)
        yield default_target, -1

    # ------------------ script -------------------------
    @lexicon
    def script(cls):
        yield r"[+|!>._^-]", Script, -1
        yield r"\d+", Fingering, -1
        yield default_target, -1

    # ------------------ pitch --------------------------
    @classmethod
    def is_pitch(cls, text):
        return text in lilypond_words.all_pitchnames

    @lexicon
    def pitch(cls):
        yield r",+|'+", Octave
        yield r"[?!]", Accidental
        yield r"=(,+|'+)?", OctaveCheck, -1
        yield SKIP_WHITESPACE
        yield default_target, -1

    # ------------------ duration ------------------------
    @lexicon
    def duration_dots(cls):
        """ zero or more dots after a duration. """
        yield SKIP_WHITESPACE
        yield r'\.', Duration.Dot
        yield default_target, cls.duration_scaling

    @lexicon
    def duration_scaling(cls):
        """ * n / m after a duration. """
        yield SKIP_WHITESPACE
        yield from cls.comments()
        yield r"(\*)\s*(\d+(?:/\d+)?)", bygroup(Duration, Duration.Scaling)
        yield default_target, -2


    # --------------------- lyrics -----------------------
    @lexicon
    def lyrics(cls):
        """Yield contents in lyric mode."""
        yield from cls.common()
        yield r">>|\}", Delimiter.CloseBrace, -1
        yield r"<<|\{", Delimiter.OpenBrace, 1
        yield r"[^\\\s\d{}$#]+", LyricText
        yield RE_FRACTION, Number
        yield RE_LILYPOND_DURATION, Duration, cls.duration_dots
        yield from cls.commands()

    @lexicon
    def lyricsto(cls):
        """Find the argument of a \\lyricsto command."""
        yield from cls.base()
        yield r"\\s(sequential|imultaneous)\b", Keyword
        yield r"\{|<<", Delimiter.OpenBrace, -1, cls.lyrics
        yield SKIP_WHITESPACE
        yield default_target, -1

    # -------------------- base stuff --------------------
    @classmethod
    def base(cls):
        """Find comment, string and scheme."""
        yield r'"', String, cls.string
        yield r'[#$]', Delimiter.SchemeStart, cls.get_scheme_target()
        yield from cls.comments()

    @classmethod
    def common(cls):
        """Find comment, string, scheme and markup."""
        yield from cls.base()
        yield r"\\markup(lines|list)?" + RE_LILYPOND_ID_RIGHT_BOUND, Keyword.Markup, cls.markup

    @lexicon
    def varname(cls):
        """bla.bla.bla syntax."""
        yield r'\s*(\.)\s*(' + RE_LILYPOND_VARIABLE + ')', bygroup(Delimiter.Dot, Name.Variable)
        yield default_target, -1

    # -------------------- markup --------------------
    @lexicon
    def markup(cls):
        """Markup without environment. Try to guess the n of arguments."""
        yield r'\{', Delimiter.OpenBrace, -1, cls.markup_environ
        yield RE_LILYPOND_COMMAND, cls.get_markup_action(), cls.get_markup_target()
        yield r'"', String, -1, cls.string
        yield r'[#$]', Delimiter.SchemeStart, -1, cls.get_scheme_target()
        yield from cls.comments()
        yield RE_LILYPOND_MARKUP_TEXT, Text, -1

    @classmethod
    def get_markup_target(cls):
        """Get the target for a markup command."""
        def test(m):
            command = m.group(m.lastindex + 1)
            return cls.get_markup_argument_count(command)
        return bymatch(test, -1, 0, 1, 2, 3)

    @classmethod
    def get_markup_argument_count(cls, command):
        """Return the number of arguments the markup command (without \\) expects."""
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
        test = lambda text: text in lilypond_words.markupcommands
        return bytext(test, Name.Function, Name.Function.Markup)


    # -------------- Scheme ---------------------
    @classmethod
    def get_scheme_target(cls):
        from .scheme import SchemeLily
        return SchemeLily.one_arg

    @lexicon
    def schemelily(cls):
        """LilyPond from scheme.SchemeLily #{ #}."""
        yield r"#}", Delimiter.LilyPond, -1
        yield from cls.root()

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
    @classmethod
    def comments(cls):
        yield r'%\{', Comment, cls.multiline_comment
        yield r'%', Comment, cls.singleline_comment

    @lexicon
    def multiline_comment(cls):
        yield r'%}', Comment, -1
        yield from cls.comment_common()

    @lexicon(re_flags=re.MULTILINE)
    def singleline_comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1


def ifgroup(n, *target):
    """Return a dynamic target that only is followed if group n in the match is not empty."""
    def predicate(m):
        if m.group(m.lastindex + n):
            return 1
        else:
            return 0
    return bymatch(predicate, 0, target)


