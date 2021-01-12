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

__all__ = ('LilyPond',)

import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import (
    Bracket, Character, Comment, Delimiter, Direction, Keyword, Name, Number,
    Operator, Separator, String, Text)
from parce.rule import (
    MATCH, TEXT, arg, bygroup, call, dselect, findmember, ifeq, ifgroup,
    ifmember, select, words)

from . import lilypond_words


SKIP_WHITESPACE = (r"\s+", skip)

RE_FRACTION = r"\d+/\d+"

RE_LILYPOND_ID_RIGHT_BOUND = r"(?![_-]?[^\W\d])"
RE_LILYPOND_ID = r"[^\W\d_]+(?:[_-][^\W\d_]+)*"
RE_LILYPOND_SYMBOL = RE_LILYPOND_ID + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_COMMAND = r"\\(" + RE_LILYPOND_ID + ")" + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_MARKUP_TEXT = r'[^{}"\\\s$#]+'
RE_LILYPOND_LYRIC_TEXT = r'[^{}"\\\s$#\d]+'
RE_LILYPOND_DYNAMIC = (
    r"\\[<!>]|"
    r"\\(f{1,5}|p{1,5}"
    r"|mf|mp|fp|spp?|sff?|sfz|rfz"
    r"|cresc|decresc|dim|cr|decr"
    r")(?![A-Za-z])")

RE_LILYPOND_REST = r"[rRs](?![^\W\d])"

# a string that could be a valid pitch name (or drum name)
RE_LILYPOND_PITCHWORD = r"(?<![^\W\d])[a-zé]+(?:[_-][a-zé]+)*(?![^\W\d_])"

# a pitch name followed by an optional octave (two capturing groups)
RE_LILYPOND_PITCH_OCT = "(" + RE_LILYPOND_PITCHWORD + r")\s*('+|,+)?"

RE_LILYPOND_DURATION = \
    r"(\\(maxima|longa|breve)\b|(1|2|4|8|16|32|64|128|256|512|1024|2048)(?!\d))"


# Standard actions defined/used here:
Rest = Text.Music.Rest
Pitch = Text.Music.Pitch
Octave = Pitch.Octave
OctaveCheck = Pitch.Octave.OctaveCheck
Accidental = Pitch.Accidental
Articulation = Name.Script.Articulation
Context = Name.Constant.Context
Grob = Name.Object.Grob
Duration = Number.Duration
Duration.Dot
Duration.Scaling
Dynamic = Name.Builtin.Dynamic
LyricText = Text.Lyric.LyricText
LyricHyphen = Delimiter.Lyric.LyricHyphen
LyricExtender = Delimiter.Lyric.LyricExtender
LyricSkip = Delimiter.Lyric.LyricSkip
Spanner = Name.Symbol.Spanner
Spanner.Slur
Spanner.Ligature
Spanner.Tie
Script = Character.Script
Fingering = Number.Fingering


class LilyPond(Language):

    @lexicon
    def root(cls):
        """Toplevel LilyPond document."""
        yield from cls.blocks()
        yield RE_LILYPOND_SYMBOL, Name.Variable.Definition, cls.identifier
        yield from cls.find_string(cls.identifier)
        yield "=", Operator.Assignment
        yield from cls.music()

    @classmethod
    def blocks(cls):
        yield r"(\\book(?:part)?)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.book
        yield r"(\\score)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.score
        yield r"(\\header)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.header
        yield r"(\\paper)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.paper
        yield r"(\\layout)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.layout
        yield r"(\\midi)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.midi

    @lexicon(consume=True)
    def book(cls):
        """Book or bookpart."""
        yield r'\}', Bracket.End, -1
        yield from cls.common()
        yield from cls.blocks()
        yield from cls.music()

    @lexicon(consume=True)
    def score(cls):
        """A score block, can also occur inside markup."""
        yield r'\}', Bracket.End, -1
        yield from cls.blocks()
        yield from cls.music()

    @lexicon(consume=True)
    def header(cls):
        """A header block."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, Name.Variable, cls.identifier
        yield "=", Operator.Assignment
        yield from cls.common()

    @lexicon(consume=True)
    def paper(cls):
        """A paper block."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, Name.Variable, cls.identifier
        yield "=", Operator.Assignment
        yield r'\d+', Number, cls.unit
        yield RE_FRACTION, Number
        yield from cls.common()
        yield from cls.commands()

    @lexicon(consume=True)
    def layout(cls):
        """A layout block."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, Name.Variable, cls.identifier
        yield "=", Operator.Assignment
        yield r'\d+', Number, cls.unit
        yield r"(\\context)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.layout_context
        yield from cls.music()

    @lexicon(consume=True)
    def midi(cls):
        """A midi block."""
        yield from cls.layout

    @lexicon(consume=True)
    def layout_context(cls):
        r"""Contents of \layout or \midi { \context { } } or \with. { }."""
        yield r'\}', Bracket.End, -1
        yield words(lilypond_words.contexts, prefix=r"\\", suffix=r"\b"), Context
        yield words(lilypond_words.grobs), Grob
        yield words(lilypond_words.keywords, prefix=r"\\", suffix=r"(?![^\W\d])"), Keyword
        yield RE_LILYPOND_SYMBOL, Name.Variable, cls.identifier
        yield "=", Operator.Assignment
        yield r'\d+', Number, cls.unit
        yield from cls.common()
        yield from cls.commands()

    # ------------------ commands that can occur in all input modes --------
    @classmethod
    def commands(cls):
        """Yield commands that can occur in all input modes."""
        yield RE_LILYPOND_DYNAMIC, Dynamic
        yield r"(\\repeat)\b(?:\s+([a-z]+)\s*(\d+)?)?", bygroup(Keyword, Name.Symbol, Number)
        yield r"\\(?:un)?set(?![^\W\d])", Keyword, cls.set_unset
        yield r"\\(?:override|revert)(?![^\W\d])", Keyword, cls.override
        yield r"\\(?:new|change|context)(?![^\W\d])", Keyword, cls.context
        yield r"(\\with)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.layout_context
        yield r"(\\key)(?![^\W\d])(?:\s+(" + RE_LILYPOND_PITCHWORD +"))?", \
            bygroup(Name.Builtin, cls.ifpitch())
        yield r"(\\relative)(?![^\W\d])(?:\s+" + RE_LILYPOND_PITCH_OCT + ")?", \
            bygroup(Name.Builtin, cls.ifpitch(), Octave)
        yield (r"(\\transpose)(?![^\W\d])(?:\s+" + RE_LILYPOND_PITCH_OCT + ")?"
               r"(?:\s*" + RE_LILYPOND_PITCH_OCT + ")?"), \
               bygroup(Name.Builtin, cls.ifpitch(), Octave, cls.ifpitch(), Octave)
        yield r"\\tempo(?![^\W\d])", Name.Builtin, cls.tempo
        yield r"(\\chord(?:s|mode))\b\s*(\{)?", bygroup(Keyword, Bracket.Start), \
            ifgroup(2, cls.chordmode)
        yield from cls.notemode_rule()
        yield from cls.lyricmode_rules()
        yield from cls.drummode_rule()
        yield RE_LILYPOND_COMMAND, findmember(MATCH[1], (
            (lilypond_words.keywords, Keyword),
            (lilypond_words.music_commands, Name.Builtin),
            (lilypond_words.all_articulations, Articulation),
            ), Name.Command)

    # ------------------ music ----------------------
    @classmethod
    def music(cls):
        """Musical items."""
        yield from cls.common()
        yield r"\{", Bracket.Start, cls.musiclist('}')
        yield r"<<", Bracket.Start, cls.musiclist('>>')
        yield r"<", Delimiter.Chord.Start, cls.chord
        yield r"\\\\", Separator.VoiceSeparator
        yield r"\|", Separator.PipeSymbol
        yield r"\\[\[\]]", Spanner.Ligature
        yield r"[\[\]]", Spanner.Beam
        yield r"\\[()]", Spanner.Slur.Phrasing
        yield r"[()]", Spanner.Slur
        yield r"~", Spanner.Tie
        yield r"[-_^]", Direction, cls.script
        yield r"q(?![^\W\d])", Pitch
        yield RE_LILYPOND_REST, Rest
        yield RE_LILYPOND_PITCHWORD, cls.ifpitch((Pitch, cls.pitch))
        yield words(lilypond_words.contexts), Context
        yield words(lilypond_words.grobs), Grob
        yield r'[.,]', Delimiter
        yield r'(:)\s*(8|16|32|64|128|256|512|1024|2048)(?!\d)', bygroup(Delimiter.Tremolo, Duration.Tremolo)
        yield RE_FRACTION, Number
        yield RE_LILYPOND_DURATION, Duration, cls.duration_dots
        yield r"\d+", Number
        yield from cls.commands()

    @lexicon(consume=True)
    def musiclist(cls):
        """A { } or << >> construct; derive with the end arg (} or >>)."""
        yield arg(), Bracket.End, -1
        yield from cls.music()

    @lexicon(consume=True)
    def chord(cls):
        """A < chord > construct."""
        yield r">", Delimiter.Chord.End, -1
        yield from cls.music()

    # ------------------ special commands ---------------
    @lexicon(consume=True)
    def tempo(cls):
        """Find content after a tempo command."""
        yield SKIP_WHITESPACE
        yield from cls.common() # markup, scheme, string, comment
        yield RE_LILYPOND_SYMBOL, Name.Symbol
        yield RE_LILYPOND_DURATION, Duration, cls.duration_dots
        yield r"(=)\s*(?:(\d+)(?:\s*(-)\s*(\d+))?)?", bygroup(
            Operator.Assignment, Number, Operator, Number), -1
        yield default_target, -1

    @lexicon(consume=True)
    def context(cls):
        """\\new, \\change, \\context Context [="name"] stuff."""
        yield SKIP_WHITESPACE
        yield words(lilypond_words.contexts), Context
        yield "=", Operator.Assignment
        yield RE_LILYPOND_SYMBOL, Name.Symbol
        yield r"(\\with)\s*(\{)", bygroup(Keyword, Bracket.Start), -1, cls.layout_context
        yield from cls.common()
        yield default_target, -1

    @lexicon(consume=True)
    def set_unset(cls):
        """\\set, \\unset."""
        yield SKIP_WHITESPACE
        yield words(lilypond_words.contexts), Context
        yield r'[.,]', Delimiter
        yield r"(=)(?:\s*(" + RE_FRACTION + r"|\d+))?", bygroup(Operator.Assignment, Number)
        yield RE_LILYPOND_SYMBOL + r"(?=\s*([,.=])?)", Name.Variable.Definition, ifeq(MATCH[1], None, -1)
        yield default_target, -1

    @lexicon(consume=True)
    def override(cls):
        """\\override, \\revert."""
        yield SKIP_WHITESPACE
        yield words(lilypond_words.contexts), Context
        yield words(lilypond_words.grobs), Grob
        yield r'[.,]', Delimiter
        yield r"=", Operator.Assignment, -1
        yield RE_LILYPOND_SYMBOL + r"(?=\s*([,.=])?)", Name.Variable, ifeq(MATCH[1], None, -1)
        yield from cls.find_scheme()
        yield default_target, -1

    # ------------------ script -------------------------
    @lexicon
    def script(cls):
        """A script abbreviation or fingering digit."""
        yield r"[+|!>._^-]", Script, -1
        yield r"\d+", Fingering, -1
        yield default_target, -1

    # ------------------ pitch --------------------------
    @classmethod
    def ifpitch(cls, itemlist=None, else_itemlist=None):
        """Return a rule item that by default yields Name.Pitch for a pitch, else Name.Symbol."""
        if itemlist is None:
            itemlist = Name.Pitch
        if else_itemlist is None:
            else_itemlist = Name.Symbol
        return ifmember(TEXT, lilypond_words.all_pitch_names, itemlist, else_itemlist)

    @lexicon
    def pitch(cls):
        """A note name, find octave/accidental etc after it."""
        yield r",+|'+", Octave
        yield r"[?!]", Accidental
        yield r"=(,+|'+)?", OctaveCheck, -1
        yield SKIP_WHITESPACE
        yield default_target, -1

    # ------------------ duration ------------------------
    @lexicon
    def duration_dots(cls):
        """Zero or more dots after a duration. """
        yield SKIP_WHITESPACE
        yield r'\.', Duration.Dot
        #yield from cls.find_comment()
        yield default_target, cls.duration_scaling

    @lexicon
    def duration_scaling(cls):
        """ * n / m after a duration. """
        yield SKIP_WHITESPACE
        #yield from cls.find_comment()
        yield r"(\*)\s*(\d+(?:/\d+)?)", bygroup(Duration, Duration.Scaling)
        yield default_target, -2


    # --------------------- lyrics -----------------------
    @classmethod
    def lyricmode_rules(cls):
        """Find lyric mode music."""
        yield r"(\\(?:lyric(?:mode|s)|addlyrics))\b\s*(\\s(?:equential|imultaneous)\b)?\s*(\{|<<)?", \
            bygroup(Keyword.Lyric, Keyword, Bracket.Start), \
            dselect(MATCH[3], {'{': cls.lyricmode('}'), '<<': cls.lyricmode('>>')})
        yield r"\\lyricsto\b", Keyword.Lyric, cls.lyricsto

    @lexicon(consume=True)
    def lyricmode(cls):
        """Yield contents in lyric mode."""
        yield arg(), Bracket.End, -1
        yield from cls.common()
        yield r"<<", Bracket.Start, cls.lyricmode('>>')
        yield r"\{", Bracket.Start, cls.lyricmode('}')
        yield RE_LILYPOND_LYRIC_TEXT, dselect(TEXT, {
                "--": LyricHyphen,
                "__": LyricExtender,
                "_": LyricSkip,
            }, LyricText)
        yield RE_FRACTION, Number
        yield RE_LILYPOND_DURATION, Duration, cls.duration_dots
        yield from cls.commands()

    @lexicon(consume=True)
    def lyricsto(cls):
        """Find the argument of a \\lyricsto command."""
        yield from cls.base()
        yield RE_LILYPOND_SYMBOL, Name.Symbol
        yield r"\\s(sequential|imultaneous)\b", Keyword
        yield r"<<", Bracket.Start, -1, cls.lyricmode('>>')
        yield r"\{", Bracket.Start, -1, cls.lyricmode('}')
        yield SKIP_WHITESPACE
        yield default_target, -1

    # ---------------------- notemode ---------------------
    @classmethod
    def notemode_rule(cls):
        """Yield the rule for \\notemode / \\notes."""
        yield r"(\\note(?:s|mode))\b\s*(\{|<<)?", bygroup(Keyword, Bracket.Start), \
            dselect(MATCH[2], {
                "{": (cls.notemode, cls.musiclist('}')),
                "<<": (cls.notemode, cls.musiclist('>>')),
            })

    @lexicon
    def notemode(cls):
        """\\notemode and \\notes."""
        yield default_target, -1

    # ---------------------- drummode ---------------------
    @classmethod
    def drummode_rule(cls):
        """Yield the rule for \\drummode / \\drums."""
        yield r"(\\drum(?:s|mode))\b\s*(\{|<<)?", bygroup(Keyword.Drum, Bracket.Start), \
            dselect(MATCH[2], {
                "{": (cls.drummode('}')),
                "<<": (cls.drummode('>>')),
            })

    @lexicon(consume=True)
    def drummode(cls):
        """\\drummode and \\drums."""
        yield r"\{", Bracket.Start, cls.drummode('}')
        yield r"<<", Bracket.Start, cls.drummode('>>')
        yield arg(), Bracket.End, -1
        yield RE_LILYPOND_REST, Rest
        yield RE_LILYPOND_PITCHWORD, ifmember(TEXT, lilypond_words.drum_pitch_names_set, Pitch.Drum, Name.Symbol)
        yield from cls.music()

    # ---------------------- chordmode ---------------------
    @lexicon(consume=True)
    def chordmode(cls):
        """\\chordmode and \\chords."""
        yield r":|/\+?", Separator.Chord, cls.chord_modifier
        yield r"\}", Bracket.End, -1
        yield r"\{", Bracket.Start, 1
        yield from cls.music()

    @lexicon
    def chord_modifier(cls):
        """Stuff in chord mode after a `:`"""
        yield r"((?<![a-z])|^)(?:aug|dim|sus|min|maj|m)(?![a-z])", Name.Symbol
        yield r"(\d+)([-+])?", bygroup(Number, Operator.Alteration)
        yield r"\.", Separator.Dot
        yield r"/\+?", Separator.Chord
        yield RE_LILYPOND_PITCHWORD, cls.ifpitch()
        yield default_target, -1

    # -------------------- base stuff --------------------
    @classmethod
    def common(cls):
        """Find comment, string, scheme and markup."""
        yield from cls.base()
        yield r"\\markup(?:lines|list)?" + RE_LILYPOND_ID_RIGHT_BOUND, Keyword.Markup, cls.markup

    @classmethod
    def base(cls):
        """Find comment, string and scheme."""
        yield r'"', String, cls.string
        yield from cls.find_scheme()
        yield from cls.find_comment()

    @lexicon(consume=True)
    def identifier(cls):
        """bla.bla.bla syntax."""
        yield SKIP_WHITESPACE
        yield r'([.,])\s*(\d+)' + RE_LILYPOND_ID_RIGHT_BOUND, bygroup(Separator, Number)
        yield r'([.,])\s*(' + RE_LILYPOND_ID + r')' + RE_LILYPOND_ID_RIGHT_BOUND, bygroup(Separator, Name.Variable)
        yield r'([.,])\s*(?=[#$"])', Separator, cls.identifier_scheme_or_string
        yield default_target, -1

    @lexicon
    def identifier_scheme_or_string(cls):
        """Pick a scheme expression or a string.

        Immediately pops back, so this context is never actually created.

        """
        yield from cls.find_string(-1)
        yield from cls.find_scheme(-1)
        yield default_target, -1

    @lexicon(consume=True)
    def unit(cls):
        """A unit that might occur after a numeric value in a paper block."""
        yield SKIP_WHITESPACE
        yield r'\\(mm|in|pt|cm)' + RE_LILYPOND_ID_RIGHT_BOUND, Name.Builtin, -1
        yield default_target, -1

    # -------------------- markup --------------------
    @lexicon(consume=True)
    def markup(cls):
        """Markup without environment. Try to guess the n of arguments."""
        yield r'\{', Bracket.Markup.Start, -1, cls.markuplist
        yield r"(\\score)\s*(\{)", bygroup(Name.Function.Markup, Bracket.Start), -1, cls.score
        yield RE_LILYPOND_COMMAND, cls.get_markup_action(), \
            select(call(cls.get_markup_argument_count, MATCH[1]), -1, 0, 1, 2, 3)
        yield from cls.find_string(-1)
        yield from cls.find_scheme(-1)
        yield from cls.find_comment()
        yield RE_LILYPOND_MARKUP_TEXT, Text, -1

    @classmethod
    def get_markup_argument_count(cls, command):
        """Return the number of arguments the markup command (without \\) expects."""
        for i in range(5):
            if command in lilypond_words.markup_commands_nargs[i]:
                return i
        return 1    # assume a user command has one argument

    @lexicon(consume=True)
    def markuplist(cls):
        """Markup until } ."""
        yield r'\}', Bracket.Markup.End, -1
        yield r'\{', Bracket.Markup.Start, 1
        yield r"(\\score)\s*(\{)", bygroup(Name.Function.Markup, Bracket.Start), cls.score
        yield RE_LILYPOND_COMMAND, cls.get_markup_action()
        yield from cls.base()
        yield RE_LILYPOND_MARKUP_TEXT, Text

    @classmethod
    def get_markup_action(cls):
        r"""Get the action for a command in \markup { }."""
        return ifmember(MATCH[1], lilypond_words.markup_commands, Name.Function.Markup, Name.Function)

    # -------------- Scheme ---------------------
    @classmethod
    def find_scheme(cls, extra_target=0):
        """Find scheme."""
        yield r'[#$]', Delimiter.ModeChange.SchemeStart, extra_target, cls.get_scheme_target()

    @classmethod
    def get_scheme_target(cls):
        """Return the ``one_arg`` lexicon for one Scheme expression."""
        from .scheme import SchemeLily
        return SchemeLily.scheme

    @lexicon(consume=True)
    def schemelily(cls):
        """LilyPond from scheme.SchemeLily #{ #}."""
        yield r"#}", Bracket.LilyPond.End, -1
        yield from cls.root()

    # -------------- String ---------------------
    @classmethod
    def find_string(cls, extra_target=0):
        """Find a string."""
        yield '"', String, extra_target, cls.string

    @lexicon(consume=True)
    def string(cls):
        """A double-quoted string."""
        yield r'"', String, -1
        yield r'\\[\\"]', String.Escape
        yield default_action, String

    # -------------- Comment ---------------------
    @classmethod
    def find_comment(cls):
        """Find single-line or block comments."""
        yield r'%\{', Comment, cls.multiline_comment
        yield r'%', Comment, cls.singleline_comment

    @lexicon(consume=True)
    def multiline_comment(cls):
        """A multiple line (block) comment."""
        yield r'%}', Comment, -1
        yield from cls.comment_common()

    @lexicon(re_flags=re.MULTILINE, consume=True)
    def singleline_comment(cls):
        """A comment till the end of the line."""
        yield from cls.comment_common()
        yield r'$', Comment, -1


