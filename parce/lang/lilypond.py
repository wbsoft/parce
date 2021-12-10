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

__all__ = ('LilyPond', 'LilyPondIndent')

import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import (
    Bracket, Character, Comment, Delimiter, Direction, Keyword, Literal, Name,
    Number, Operator, Separator, String, Text)
from parce.rule import (
    MATCH, TEXT, arg, bygroup, call, dselect, findmember, ifarg, ifeq, ifgroup,
    ifmember, select, using, words)
from parce.indent import Indent, ALIGN, INDENT, DEDENT, NO_DEDENT

from . import lilypond_words


SKIP_WHITESPACE = (r"\s+", skip)

RE_FRACTION = r"\d+/\d+"

RE_LILYPOND_ID_RIGHT_BOUND = r"(?![_-]?[^\W\d_])"
RE_LILYPOND_ID = r"[^\W\d_]+(?:[_-][^\W\d_]+)*"
RE_LILYPOND_SYMBOL = RE_LILYPOND_ID + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_COMMAND = r"\\(" + RE_LILYPOND_ID + ")" + RE_LILYPOND_ID_RIGHT_BOUND
RE_LILYPOND_MARKUP_TEXT = r'[^%{}"\\\s$#][^{}"\\\s$#]*'
RE_LILYPOND_LYRIC_TEXT = r'[^%={}"\\\s$#\d][^{}"\\\s$#\d]*'

# a string that could be a valid pitch name (or drum name)
RE_LILYPOND_PITCHWORD = r"(?<![^\W\d])[a-zé]+(?:[_-][a-zé]+)*(?![^\W\d_])"

# all durations
RE_LILYPOND_DURATION = (
    words(set(filter(lambda w: w.startswith('\\'), lilypond_words.durations)), suffix = RE_LILYPOND_ID_RIGHT_BOUND) +
    "|" + words(set(filter(lambda w: not w.startswith('\\'), lilypond_words.durations)), suffix = r'(?!\d)'))

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
        yield RE_LILYPOND_SYMBOL, findmember(TEXT, (
                (lilypond_words.rests, Rest),
                (lilypond_words.all_pitch_names, (Pitch, cls.pitch)),
                (lilypond_words.contexts, (Context, cls.list)),
                (lilypond_words.grobs, (Grob, cls.list)),
            ), (Name.Variable.Definition, cls.list))
        yield from cls.find_string(cls.list)
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands(list_target=cls.start_list)

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
        """A score block."""
        yield r'\}', Bracket.End, -1
        yield from cls.blocks()
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands()

    @lexicon(consume=True)
    def header(cls):
        """A header block."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, Name.Attribute, cls.list
        yield RE_FRACTION, Number.Fraction
        yield r'\d+\.\d+', Number.Float
        yield from cls.common()
        yield from cls.commands()

    @lexicon(consume=True)
    def paper(cls):
        """A paper block."""
        yield from cls.header

    @lexicon(consume=True)
    def layout(cls):
        """A layout block."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, Name.Attribute, cls.list
        yield r"(\\context)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.layout_context
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands(list_target=cls.start_list)

    @lexicon(consume=True)
    def midi(cls):
        """A midi block."""
        yield from cls.layout

    @lexicon(consume=True)
    def layout_context(cls):
        r"""Contents of ``\layout`` or ``\midi { \context { } }`` or ``\with. { }``."""
        yield r'\}', Bracket.End, -1
        yield RE_LILYPOND_SYMBOL, findmember(TEXT, (
                (lilypond_words.rests, Rest),
                (lilypond_words.all_pitch_names, (Pitch, cls.pitch)),
                (lilypond_words.contexts, (Context, cls.list)),
                (lilypond_words.grobs, (Grob, cls.list)),
            ), (Name.Variable, cls.list))
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands(list_target=cls.start_list)

    # ------------------ commands that can occur in all input modes --------
    @classmethod
    def commands(cls, *, list_target=0):
        """Yield commands that can occur in all input modes.

        If a ``list_target`` is given, that lexicon is pushed after a Keyword,
        to be able to parse symbols, strings, numbers or scheme. This makes
        sense in e.g. lyrics mode.

        """
        yield r"(\\with)\s*(\{)", bygroup(Keyword, Bracket.Start), cls.layout_context
        yield r'(' + RE_LILYPOND_COMMAND + r')(?=\s*(\.))?', ifgroup(3,
            # part of a \bla.bla or \bla.1 construct, always a user command
            (Name.Variable, cls.identifier_ref),
            # no "." or "," , can be a builtin
            dselect(MATCH[2], {
                # input modes
                "lyricsto": (Keyword.Lyric, cls.lyricsto, cls.start_list),
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
                "repeat": (Name.Builtin, cls.repeat),
            },
            (findmember(MATCH[2], (
                (lilypond_words.keywords, (Keyword, list_target)),
                (lilypond_words.all_articulations, Articulation),
                (lilypond_words.dynamics, Dynamic),
                (lilypond_words.units, Name.Builtin.Unit),
                (lilypond_words.music_commands, Name.Builtin),
                (lilypond_words.contexts, Name.Builtin.Context),
                (lilypond_words.modes, Name.Type),
            ), (Name.Variable, cls.identifier_ref)))))
        # seldom used, but nevertheless allowed in LilyPond: \"blabla"
        yield r'(\\)(?=")', Name.Variable, cls.identifier_ref

    # ------------------ music ----------------------
    @classmethod
    def music(cls):
        """Musical items."""
        yield from cls.find_string(cls.list)
        yield from cls.find_scheme(cls.list)
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
        yield RE_LILYPOND_SYMBOL, findmember(TEXT, (
                ('q', Pitch),
                (lilypond_words.rests, Rest),
                (lilypond_words.all_pitch_names, (Pitch, cls.pitch)),
                (lilypond_words.contexts, (Context, cls.list)),
                (lilypond_words.grobs, (Grob, cls.list)),
            ), (Name.Symbol, cls.list))
        yield r'[.,]', Delimiter
        yield r'(:)\s*(8|16|32|64|128|256|512|1024|2048)?(?!\d)', bygroup(Delimiter.Tremolo, Duration.Tremolo)
        yield RE_FRACTION, Number.Fraction
        yield r'\d+\.\d+', Number.Float
        yield r'(\d+)(?=\s*,)', Number, cls.list
        yield RE_LILYPOND_DURATION, Duration, cls.duration
        yield r"\d+", Number, cls.list

    @lexicon(consume=True)
    def musiclist(cls):
        """A ``{`` ... ``}`` or ``<<`` ... ``>>`` musical construct.

        Derive with the end arg (``}`` or ``>>``).

        """
        yield arg(), Bracket.End, -1
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands()

    @lexicon(consume=True)
    def chord(cls):
        """A ``<`` chord ``>`` construct."""
        yield r">", Delimiter.Chord.End, -1
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands()

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

    # --------------------- input modes ------------------
    @classmethod
    def inputmode(cls, lexicon):
        """Yield boilerplate rules for an input mode."""
        yield SKIP_WHITESPACE
        yield r"\\s(equential|imultaneous)\b", Keyword
        yield r"<<", Bracket.Start, -1, lexicon('>>')
        yield r"\{", Bracket.Start, -1, lexicon('}')
        yield from cls.find_comment()
        yield default_target, -1

    @classmethod
    def inputmode_list(cls, lexicon):
        """Yield boilerplate rules for the contents of an input mode."""
        yield arg(), Bracket.End, -1
        yield r"<<", Bracket.Start, lexicon('>>')
        yield r"\{", Bracket.Start, lexicon('}')

    # --------------------- lyrics -----------------------
    @lexicon
    def lyricmode(cls):
        """Yield contents in lyric mode."""
        yield from cls.inputmode(cls.lyriclist)

    @lexicon
    def lyricsto(cls):
        r"""Find the argument of a ``\lyricsto`` command."""
        yield default_target, -1, cls.lyricmode

    @lexicon(consume=True)
    def lyriclist(cls):
        """Lyrics between ``{`` ... ``}``.

        Derive with the desired closing delimiter (``}`` or ``>>``).

        """
        yield from cls.inputmode_list(cls.lyriclist)
        yield RE_LILYPOND_LYRIC_TEXT, dselect(TEXT, {
                "--": LyricHyphen,
                "__": LyricExtender,
                "_": LyricSkip,
            }, using(cls.lyricword))
        yield RE_FRACTION, Number.Fraction
        yield RE_LILYPOND_DURATION, Duration, cls.duration
        yield from cls.common()
        yield from cls.commands(list_target=cls.start_list)

    @lexicon
    def lyricword(cls):
        """Contents of lyric word, highlight tie and space separately."""
        yield '~', LyricText.Tie
        yield '_', LyricText.Space
        yield default_action, LyricText

    # ---------------------- drummode ---------------------
    @lexicon
    def drummode(cls):
        """\\drummode and \\drums."""
        yield from cls.inputmode(cls.drumlist)

    @lexicon(consume=True)
    def drumlist(cls):
        """Drum music between ``{`` ... ``}`` or ``<<`` ... ``>>``."""
        yield from cls.inputmode_list(cls.drumlist)
        yield RE_LILYPOND_SYMBOL, findmember(TEXT, (
                (lilypond_words.rests, Rest),
                (lilypond_words.drum_pitch_names, Pitch.Drum),
                (lilypond_words.contexts, (Context, cls.list)),
                (lilypond_words.grobs, (Grob, cls.list))), (Name.Symbol, cls.list))
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands()

    # ---------------------- chordmode ---------------------
    @lexicon
    def chordmode(cls):
        """\\chordmode and \\chords."""
        yield from cls.inputmode(cls.chordlist)

    @lexicon(consume=True)
    def chordlist(cls):
        """Chordmode music between ``{`` ... ``}`` or ``<<`` ... ``>>``."""
        yield from cls.inputmode_list(cls.chordlist)
        yield r"[:^]", Separator.Chord, cls.chord_modifier
        yield r"(/\+?)\s*(" + RE_LILYPOND_PITCHWORD + ")?", bygroup(Separator.Chord, cls.ifpitch())
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands()

    @lexicon
    def chord_modifier(cls):
        """Stuff in chord mode after a `:`"""
        yield SKIP_WHITESPACE
        yield r"((?<![a-z])|^)(?:aug|dim|sus|min|maj|m)(?![a-z])", Name.Symbol
        yield r"(\d+)([-+])?", bygroup(Number, Operator.Alteration)
        yield r"\.", Separator.Dot
        yield from cls.find_comment()
        yield default_target, -1

    # --------------------- notemode -------------------
    @lexicon
    def notemode(cls):
        """Notemode switches back to music e.g. in lyrics."""
        yield from cls.inputmode(cls.musiclist)

    # --------------------- figuremode -------------------
    @lexicon
    def figuremode(cls):
        """\\figuremode and \\figures."""
        yield from cls.inputmode(cls.figurelist)

    @lexicon(consume=True)
    def figurelist(cls):
        """figuremode music between ``{`` ... ``}`` or ``<<`` ... ``>>``."""
        yield from cls.inputmode_list(cls.figurelist)
        yield r'<', Delimiter.Chord.Start, cls.figure
        yield RE_LILYPOND_DURATION, Duration, cls.duration
        yield from cls.music()
        yield from cls.common()
        yield from cls.commands()

    @lexicon(consume=True)
    def figure(cls):
        """Stuff between ``<`` and ``>`` in figure mode."""
        yield r'>', Delimiter.Chord.End, -1
        yield r'\[', Bracket.Start, cls.figurebracket
        yield from cls._figure_rules()

    @lexicon(consume=True)
    def figurebracket(cls):
        """Stuff between ``[`` and ``]`` in a bass figure."""
        yield r'>', Delimiter.Chord.End, -2
        yield r'\]', Bracket.End, -1
        yield from cls._figure_rules()

    @classmethod
    def _figure_rules(cls):
        """Rules for figures in [ ] and < >."""
        yield r'_|\d+', Pitch.Figure
        yield r'--?|\+\+?|!', Accidental
        yield r'\\[\\!+]|/', Character.Alteration
        yield from cls.common()

    # -------------------- base stuff --------------------
    @classmethod
    def common(cls):
        """Find comment, string, scheme, the ``=`` operator and  markup."""
        yield from cls.base()
        yield "=", Operator.Assignment, cls.start_list
        yield from cls.find_markup()

    @classmethod
    def base(cls):
        """Find comment, string and scheme."""
        yield from cls.find_string()
        yield from cls.find_scheme()
        yield from cls.find_comment()

    @lexicon(consume=True)
    def list(cls):
        r"""A list of numbers, symbols, strings or scheme expressions.

        Consumes both . and , as separators.

        Jump here:

        * plainly: start_list
        * when a ", # or $ is ahead: start_list
        * from a number followed by , (but don't consume the ,)
        * from a symbol

        """
        yield SKIP_WHITESPACE
        yield r'([.,])\s*(\d+)(?!(?:/|\.\d+))' + RE_LILYPOND_ID_RIGHT_BOUND, bygroup(Separator, Number)
        yield r'([.,])\s*(' + RE_LILYPOND_ID + r')' + RE_LILYPOND_ID_RIGHT_BOUND, \
            bygroup(Separator, cls.get_symbol_action(MATCH[2], Name.Variable))
        yield r'([.,])\s*(?=[#$"])', bygroup(Separator), cls._continue_list
        yield from cls.find_comment()
        yield default_target, -1

    @lexicon
    def start_list(cls):
        """Start a list, this context is never created: all contents go to ``list``."""
        yield SKIP_WHITESPACE
        yield from cls.find_string(-1, cls.list)
        yield from cls.find_scheme(-1, cls.list)
               # vvvvvvvv not a real or fraction
        yield r'(?=\d+[\./])', None, -1
        yield r'\d+', Number, -1, cls.list
        yield RE_LILYPOND_SYMBOL, cls.get_symbol_action(TEXT, Name.Variable), -1, cls.list
        yield default_target, -1

    @lexicon
    def _continue_list(cls):
        """Continue a list, this context is never created: all contents remain in ``list``."""
        yield from cls.find_string(-1)
        yield from cls.find_scheme(-1)
        yield default_target, -1

    @lexicon(consume=True)
    def identifier_ref(cls):
        r"""\bla.bla.bla syntax."""
        yield r'(?<=\\)"', String, cls.string   # only after '\'
        yield from cls.list

    @classmethod
    def get_symbol_action(self, text, default=Name.Symbol):
        """Return a proper dynamic action for the name of a symbol."""
        return findmember(text, (
                (lilypond_words.grobs, Grob),
                (lilypond_words.contexts, Context),
                ), default)

    # -------------------- markup --------------------
    @classmethod
    def find_markup(cls):
        r"""Find ``\markup``, ``\markuplines`` and ``\markuplist``."""
        yield r"\\markup(?:lines|list)?" + RE_LILYPOND_ID_RIGHT_BOUND, Keyword.Markup, cls.markup

    @lexicon(consume=True)
    def markup(cls):
        """Markup without environment. Try to guess the n of arguments."""
        yield from cls._markup_rules(-1)

    @lexicon(consume=True)
    def markuplist(cls):
        """Markup in environment from ``{`` until ``}``."""
        yield r'\}', Bracket.Markup.End, -1
        yield from cls._markup_rules()

    @lexicon(consume=True)
    def markupscore(cls):
        r"""``\score { }`` or ``\score-lines { }`` in markup."""
        yield from cls.score

    @classmethod
    def _markup_rules(cls, *extra_target):
        r"""Markup rules. Specify ``-1`` if outside an environment."""
        yield (r'\{', Bracket.Markup.Start, *extra_target, cls.markuplist)
        yield (r"(\\score(?:-lines)?)\s*(\{)", bygroup(Name.Function.Markup, Bracket.Start), *extra_target, cls.markupscore)
        if extra_target:
            # count the arguments of markup commands and stack markup contexts
            yield RE_LILYPOND_COMMAND, cls.get_markup_action(), \
                select(call(cls.get_markup_argument_count, MATCH[1]), -1, 0, 1, 2, 3)
        else:
            # in an environment; no need to count the arguments.
            yield RE_LILYPOND_COMMAND, cls.get_markup_action()
        yield from cls.find_string(*extra_target)
        yield from cls.find_scheme(*extra_target)
        yield from cls.find_comment()
        yield (RE_LILYPOND_MARKUP_TEXT, Text, *extra_target)

    @classmethod
    def get_markup_argument_count(cls, command):
        r"""Return the number of arguments of a markup command (without ``\``) expects.

        The default implementation returns 1 for unknown commands. You could
        re-implement this method if you have some special commands to add.

        """
        try:
            return lilypond_words.markup_commands[command]
        except KeyError:
            return 1    # assume a user command has one argument

    @classmethod
    def get_markup_action(cls):
        r"""Get the action for a command in \markup { }."""
        return ifmember(MATCH[1], lilypond_words.markup_commands, Name.Function.Markup, Name.Function)

    # -------------- Scheme ---------------------
    @classmethod
    def find_scheme(cls, *extra_target):
        """Find scheme."""
        yield (r'[#$]@?', Delimiter.ModeChange.SchemeStart, *extra_target, cls.get_scheme_target())

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
    def find_string(cls, *extra_target):
        """Find a string."""
        yield ('"', String, *extra_target, cls.string)

    @lexicon(consume=True)
    def string(cls):
        """A double-quoted string."""
        yield r'"', String, -1
        yield r'\\[\\"]', String.Escape
        yield default_action, String

    # -------------- Comment ---------------------
    @classmethod
    def find_comment(cls, *extra_target):
        """Find single-line or block comments."""
        yield (r'%\{', Comment, *extra_target, cls.multiline_comment)
        yield (r'%', Comment, *extra_target, cls.singleline_comment)

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


class LilyPondIndent(Indent):
    """Indenter for LilyPond."""

    def events(self, block, tokens, prev_indents):
        """Yield indent events."""
        for t in tokens:
            if t.action in Delimiter:
                if t in ('{', '<<'):
                    yield INDENT
                elif t in ('}', '>>'):
                    yield DEDENT
                else:
                    yield NO_DEDENT
            else:
                yield NO_DEDENT

