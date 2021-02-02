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
    MATCH, TEXT, arg, bygroup, call, dselect, findmember, ifarg, ifeq, ifgroup,
    ifmember, select, words)

from . import lilypond_words


SKIP_WHITESPACE = (r"\s+", skip)

RE_FRACTION = r"\d+/\d+"

RE_LILYPOND_ID_RIGHT_BOUND = r"(?![_-]?[^\W\d_])"
RE_LILYPOND_ID = r"[^\W\d_]+(?:[_-][^\W\d_]+)*"
RE_LILYPOND_SYMBOL = RE_LILYPOND_ID + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_COMMAND = r"\\(" + RE_LILYPOND_ID + ")" + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_MARKUP_TEXT = r'[^%{}"\\\s$#][^{}"\\\s$#]*'
RE_LILYPOND_LYRIC_TEXT = r'[^%{}"\\\s$#\d][^{}"\\\s$#\d]*'

RE_LILYPOND_REST = r"[rRs](?![^\W\d])"

# a string that could be a valid pitch name (or drum name)
RE_LILYPOND_PITCHWORD = r"(?<![^\W\d])[a-zé]+(?:[_-][a-zé]+)*(?![^\W\d_])"


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
Spanner.Id
Spanner.PesOrFlexa
Script = Character.Script
Fingering = Number.Fingering


class LilyPond(Language):

    @lexicon
    def root(cls):
        """Toplevel LilyPond document."""
        yield from cls.blocks()
        yield RE_LILYPOND_SYMBOL, Name.Variable.Definition, cls.identifier
        yield from cls.find_string(cls.identifier)
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
        yield from cls.score

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
        yield from cls.common()

    @lexicon(consume=True)
    def paper(cls):
        """A paper block."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, Name.Variable, cls.identifier
        yield r'\d+', Number, cls.unit
        yield RE_FRACTION, Number
        yield from cls.common()
        yield from cls.commands()

    @lexicon(consume=True)
    def layout(cls):
        """A layout block."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, Name.Variable, cls.identifier
        yield r'\d+', Number, cls.unit
        yield r"(\\context)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.layout_context
        yield from cls.music()

    @lexicon(consume=True)
    def midi(cls):
        """A midi block."""
        yield from cls.layout

    @lexicon(consume=True)
    def layout_context(cls):
        r"""Contents of ``\layout`` or ``\midi { \context { } }`` or ``\with. { }``."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, findmember(TEXT, (
                (lilypond_words.contexts, Context),
                (lilypond_words.grobs, Grob)), (Name.Variable, cls.identifier))
        yield r'\d+', Number, cls.unit
        yield from cls.common()
        yield from cls.commands()

    # ------------------ commands that can occur in all input modes --------
    @classmethod
    def commands(cls):
        """Yield commands that can occur in all input modes."""
        yield r"(\\with)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.layout_context
        yield r'(' + RE_LILYPOND_COMMAND + r')(?=\s*(?:(\.)|([$#"])))?', ifgroup(3,
            # part of a \bla.bla or \bla.1 construct, always a user command
            (Name.Command, cls.identifier),
            # no "." or "," , can be a builtin
            dselect(MATCH[2], {
                # input modes
                "lyricsto": (Keyword.Lyric, cls.lyricsto, cls.start_with_scheme_or_string),
                "addlyrics": (Keyword.Lyric, cls.lyricmode),
                "lyrics": (Keyword.Lyric, cls.lyricmode),
                "lyricmode": (Keyword.Lyric, cls.lyricmode),
                "chords": (Keyword, cls.chordmode),
                "chordmode": (Keyword, cls.chordmode),
                "drums": (Keyword, cls.drummode),
                "drummode": (Keyword, cls.drummode),
                "figures": (Keyword, cls.figuremode),
                "figuremode": (Keyword, cls.figuremode),
                "notemode": (Keyword, cls.notemode),    # \notes doesn't exist anymore
                # commands that expect some symbols in all input modes
                "set": (Keyword, cls.property_set),
                "unset": (Keyword, cls.property, cls.start_with_scheme_or_string),
                "override": (Keyword, cls.property_set),
                "revert": (Keyword, cls.property, cls.start_with_scheme_or_string),
                "new": (Keyword, cls.property_set),
                "change": (Keyword, cls.property_set),
                "context": (Keyword, cls.property_set),
                "repeat": (Keyword, cls.repeat),
            },
            (findmember(MATCH[2], (
                (lilypond_words.keywords, Keyword),
                (lilypond_words.music_commands, Name.Builtin),
                (lilypond_words.all_articulations, Articulation),
                (lilypond_words.contexts, Name.Builtin.Context),
                (lilypond_words.dynamics, Dynamic),
                (lilypond_words.modes, Name.Type),
            ), Name.Command), ifgroup(4, cls.start_with_scheme_or_string))))
        # seldom used, but nevertheless allowed in LilyPond: \"blabla"
        yield r'(\\)(")', bygroup(Name.Command, String), cls.identifier, cls.string

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
        yield r"\\~", Spanner.PesOrFlexa
        yield r"\\[<>!]", Dynamic
        yield r"[-_^]", Direction, cls.script
        yield r"(\\=)\s*(?:(\d+)|({}))?".format(RE_LILYPOND_SYMBOL), \
            bygroup(Spanner.Id, Number, cls.ifpitch(Name.Symbol.Invalid, Name.Symbol))
        yield r"q(?![^\W\d])", Pitch
        yield RE_LILYPOND_REST, Rest
        yield RE_LILYPOND_SYMBOL, findmember(TEXT, (
                (lilypond_words.all_pitch_names, (Pitch, cls.pitch)),
                (lilypond_words.contexts, Context),
                (lilypond_words.grobs, Grob)), Name.Symbol)
        yield r'[.,]', Delimiter
        yield r'(:)\s*(8|16|32|64|128|256|512|1024|2048)?(?!\d)', bygroup(Delimiter.Tremolo, Duration.Tremolo)
        yield RE_FRACTION, Number
        yield words(lilypond_words.durations, suffix = r'(?!\d)'), Duration, cls.duration
        yield r"\d+", Number
        yield from cls.commands()

    @lexicon(consume=True)
    def musiclist(cls):
        """A ``{`` ... ``}`` or ``<<`` ... ``>>`` musical construct.

        Derive with the end arg (``}`` or ``>>``).

        """
        yield arg(), Bracket.End, -1
        yield from cls.music()

    @lexicon(consume=True)
    def chord(cls):
        """A ``<`` chord ``>`` construct."""
        yield r">", Delimiter.Chord.End, -1
        yield from cls.music()

    # ------------------ properties ---------------------
    @classmethod
    def property_action(cls, text):
        """Return a proper dynamic action for the name of a symbol."""
        return findmember(text, (
                (lilypond_words.grobs, Grob),
                (lilypond_words.contexts, Context),
                ), Name.Variable)

    @lexicon
    def property_set(cls):
        """Read property names, delimiters, strings and scheme.

        Calls :meth:`property_action` to get an action for the text.
        Quits on ``"="`` or any non-word and non-whitespace character.

        """
        yield '=', Operator.Assignment, -1
        yield from cls.find_string()
        yield from cls.find_scheme()
        yield from cls.find_comment()
        yield RE_LILYPOND_SYMBOL, cls.property_action(TEXT)
        yield r'[.,]', Separator
        yield r'(?=[^\w\s])', None, -1

    @lexicon
    def property(cls):
        """Read property names, delimiters, strings and scheme.

        Calls :meth:`property_action` to get an action for the text.

        """
        yield SKIP_WHITESPACE
        yield RE_LILYPOND_SYMBOL + r"(?=\s*([,.])?)", cls.property_action(TEXT), ifeq(MATCH[1], None, -1)
        yield r'([.,])\s*(?=[#$"])', Separator, cls.start_with_scheme_or_string
        yield r'([.,])\s*(' + RE_LILYPOND_SYMBOL +  ')', bygroup(Separator, cls.property_action(MATCH[2]))
        yield default_target, -1

    # ------------------ repeat -------------------------
    @lexicon
    def repeat(cls):
        """\\repeat mode n."""
        yield SKIP_WHITESPACE
        yield words(("volta", "unfold", "percent", "tremolo"), suffix=r'\b'), Name.Type
        yield from cls.find_string()
        yield from cls.find_comment()
        yield r'\d+', Number, -1
        yield default_target, -1

    # ------------------ script -------------------------
    @lexicon
    def script(cls):
        """A script abbreviation or fingering digit."""
        yield r"[+|!>._^-]", Script, -1
        yield r"\d+", Fingering, -1
        yield SKIP_WHITESPACE
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
        yield r",(?:\s*?,)*|'(?:\s*?')*", Octave
        yield r"[?!]", Accidental
        yield r"=(?:,(?:\s*?,)*|'(?:\s*?')*)?", OctaveCheck, -1
        yield SKIP_WHITESPACE
        yield from cls.find_comment()
        yield default_target, -1

    # ------------------ duration ------------------------
    @lexicon
    def duration(cls):
        """Zero or more dots after a duration. """
        yield SKIP_WHITESPACE
        yield r'\.', Duration.Dot
        #yield from cls.find_comment()
        yield default_target, cls.duration_scaling

    @lexicon
    def duration_scaling(cls):
        """ ``*n/m`` after a duration. """
        yield SKIP_WHITESPACE
        #yield from cls.find_comment()
        yield r"(\*)\s*(\d+(?:/\d+)?)", bygroup(Duration, Duration.Scaling)
        yield default_target, -2


    # --------------------- lyrics -----------------------
    @lexicon
    def lyricmode(cls):
        """Yield contents in lyric mode."""
        yield SKIP_WHITESPACE
        yield r"\\s(sequential|imultaneous)\b", Keyword
        yield r"<<", Bracket.Start, -1, cls.lyriclist('>>')
        yield r"\{", Bracket.Start, -1, cls.lyriclist('}')
        yield from cls.find_comment()
        yield default_target, -1

    @lexicon
    def lyricsto(cls):
        r"""Find the argument of a ``\lyricsto`` command."""
        yield RE_LILYPOND_SYMBOL, Name.Symbol, -1, cls.lyricmode
        yield default_target, -1, cls.lyricmode

    @lexicon(consume=True)
    def lyriclist(cls):
        """Lyrics between ``{`` ... ``}``.

        Derive with the desired closing delimiter (``}`` or ``>>``).

        """
        yield arg(), Bracket.End, -1
        yield r"<<", Bracket.Start, cls.lyriclist('>>')
        yield r"\{", Bracket.Start, cls.lyriclist('}')
        yield RE_LILYPOND_LYRIC_TEXT, dselect(TEXT, {
                "--": LyricHyphen,
                "__": LyricExtender,
                "_": LyricSkip,
            }, LyricText)
        yield from cls.common()
        yield from cls.commands()


    # ---------------------- drummode ---------------------
    @lexicon
    def drummode(cls):
        """\\drummode and \\drums."""
        yield SKIP_WHITESPACE
        yield r"\\s(sequential|imultaneous)\b", Keyword
        yield r"\{", Bracket.Start, -1, cls.drumlist('}')
        yield r"<<", Bracket.Start, -1, cls.drumlist('>>')
        yield from cls.find_comment()
        yield default_target, -1

    @lexicon(consume=True)
    def drumlist(cls):
        """Drum music between ``{`` ... ``}`` or ``<<`` ... ``>>``."""
        yield arg(), Bracket.End, -1
        yield r"\{", Bracket.Start, cls.drumlist('}')
        yield r"<<", Bracket.Start, cls.drumlist('>>')
        yield RE_LILYPOND_REST, Rest
        yield RE_LILYPOND_PITCHWORD, ifmember(TEXT, lilypond_words.drum_pitch_names_set, Pitch.Drum, Name.Symbol)
        yield from cls.music()

    # ---------------------- chordmode ---------------------
    @lexicon
    def chordmode(cls):
        """\\chordmode and \\chords."""
        yield SKIP_WHITESPACE
        yield r"\\s(sequential|imultaneous)\b", Keyword
        yield r"\{", Bracket.Start, -1, cls.chordlist('}')
        yield r"<<", Bracket.Start, -1, cls.chordlist('>>')
        yield from cls.find_comment()
        yield default_target, -1

    @lexicon(consume=True)
    def chordlist(cls):
        """Chordmode music between ``{`` ... ``}`` or ``<<`` ... ``>>``."""
        yield arg(), Bracket.End, -1
        yield r"\{", Bracket.Start, cls.chordlist('}')
        yield r"<<", Bracket.Start, cls.chordlist('>>')
        yield r"[:^]", Separator.Chord, cls.chord_modifier
        yield r"(/\+?)\s*(" + RE_LILYPOND_PITCHWORD + ")?", bygroup(Separator.Chord, cls.ifpitch())
        yield from cls.music()

    @lexicon
    def chord_modifier(cls):
        """Stuff in chord mode after a `:`"""
        yield SKIP_WHITESPACE
        yield r"((?<![a-z])|^)(?:aug|dim|sus|min|maj|m)(?![a-z])", Name.Symbol
        yield r"(\d+)([-+])?", bygroup(Number, Operator.Alteration)
        yield r"\.", Separator.Dot
        yield default_target, -1

    # --------------------- notemode -------------------
    @lexicon
    def notemode(cls):
        """Notemode switches back to music e.g. in lyrics."""
        yield SKIP_WHITESPACE
        yield r"\\s(sequential|imultaneous)\b", Keyword
        yield r"\{", Bracket.Start, -1, cls.musiclist('}')
        yield r"<<", Bracket.Start, -1, cls.musiclist('>>')
        yield from cls.find_comment()
        yield default_target, -1

    # --------------------- figuremode -------------------
    @lexicon
    def figuremode(cls):
        """\\figuremode and \\figures."""
        yield SKIP_WHITESPACE
        yield r"\\s(sequential|imultaneous)\b", Keyword
        yield r"\{", Bracket.Start, -1, cls.figurelist('}')
        yield r"<<", Bracket.Start, -1, cls.figurelist('>>')
        yield from cls.find_comment()
        yield default_target, -1

    @lexicon(consume=True)
    def figurelist(cls):
        """figuremode music between ``{`` ... ``}`` or ``<<`` ... ``>>``."""
        yield arg(), Bracket.End, -1
        yield r"\{", Bracket.Start, cls.figurelist('}')
        yield r"<<", Bracket.Start, cls.figurelist('>>')
        # TODO

    # -------------------- base stuff --------------------
    @classmethod
    def common(cls):
        """Find comment, string, scheme, the ``=`` operator and  markup."""
        yield from cls.base()
        yield "=", Operator.Assignment
        yield r"\\markup(?:lines|list)?" + RE_LILYPOND_ID_RIGHT_BOUND, Keyword.Markup, cls.markup

    @classmethod
    def base(cls):
        """Find comment, string and scheme."""
        yield from cls.find_string()
        yield from cls.find_scheme()
        yield from cls.find_comment()

    @lexicon(consume=True)
    def identifier(cls):
        """bla.bla.bla syntax."""
        yield SKIP_WHITESPACE
        yield r'(\.)\s*(\d+)' + RE_LILYPOND_ID_RIGHT_BOUND, bygroup(Separator, Number)
        yield r'(\.)\s*(' + RE_LILYPOND_ID + r')' + RE_LILYPOND_ID_RIGHT_BOUND, bygroup(Separator, Name.Variable)
        yield r'(\.)\s*(?=[#$"])', Separator, cls.start_with_scheme_or_string
        yield default_target, -1

    @lexicon
    def start_with_scheme_or_string(cls):
        """Pick a scheme expression or a string.

        Immediately pops back, so this context is never actually created.

        """
        yield SKIP_WHITESPACE
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


