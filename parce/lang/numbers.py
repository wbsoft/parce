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
Parse numerals in different languages.

The Language definitions in this module do not make much sense for syntax
highlighting, but can be used to read numbers from text in various languages,
and serve as a proof-of-concept that nesting Contexts can be used to give a
meaning to the contained text, which shows how *parce* can go beyond basic
tokenizing.

Here is an example, showing the nesting of the matched tokens (that all have
the :obj:`~parce.action.Number` standard action)::

    >>> from parce.lang.numbers import Deutsch, English, Francais, Nederlands
    >>> from parce import root
    >>> root(Nederlands.root, "eenentwintig").dump()
    <Context Nederlands.root at 0-12 (1 child)>
     ╰╴<Context Nederlands.number at 0-12 (1 child)>
        ╰╴<Context Nederlands.p6 at 0-12 (1 child)>
           ╰╴<Context Nederlands.p3 at 0-12 (1 child)>
              ╰╴<Context Nederlands.p2 at 0-12 (1 child)>
                 ╰╴<Context Nederlands.n99 at 0-12 (2 children)>
                    ├╴<Token 'een' at 0:3 (Literal.Number)>
                    ╰╴<Token 'twintig' at 5:12 (Literal.Number)>
    >>> root(Nederlands.root, "twaalfhonderdeenentwintig").dump()
    <Context Nederlands.root at 0-25 (1 child)>
     ╰╴<Context Nederlands.number at 0-25 (1 child)>
        ╰╴<Context Nederlands.p6 at 0-25 (1 child)>
           ╰╴<Context Nederlands.p3 at 0-25 (2 children)>
              ├╴<Context Nederlands.p2 at 0-13 (2 children)>
              │  ├╴<Context Nederlands.n99 at 0-6 (1 child)>
              │  │  ╰╴<Token 'twaalf' at 0:6 (Literal.Number)>
              │  ╰╴<Token 'honderd' at 6:13 (Literal.Number)>
              ╰╴<Context Nederlands.n99 at 13-25 (2 children)>
                 ├╴<Token 'een' at 13:16 (Literal.Number)>
                 ╰╴<Token 'twintig' at 18:25 (Literal.Number)>
    >>> root(English.root, "FiftySixThousandSevenHundredEightyNine").dump()
    <Context English.root at 0-38 (1 child)>
     ╰╴<Context English.number at 0-38 (1 child)>
        ╰╴<Context English.p6 at 0-38 (4 children)>
           ├╴<Context English.p3 at 0-16 (2 children)>
           │  ├╴<Context English.p2 at 0-8 (2 children)>
           │  │  ├╴<Context English.n99 at 0-5 (1 child)>
           │  │  │  ╰╴<Token 'Fifty' at 0:5 (Literal.Number)>
           │  │  ╰╴<Context English.p1 at 5-8 (1 child)>
           │  │     ╰╴<Token 'Six' at 5:8 (Literal.Number)>
           │  ╰╴<Token 'Thousand' at 8:16 (Literal.Number)>
           ├╴<Context English.p2 at 16-28 (2 children)>
           │  ├╴<Context English.n99 at 16-21 (1 child)>
           │  │  ╰╴<Token 'Seven' at 16:21 (Literal.Number)>
           │  ╰╴<Token 'Hundred' at 21:28 (Literal.Number)>
           ├╴<Context English.n99 at 28-34 (1 child)>
           │  ╰╴<Token 'Eighty' at 28:34 (Literal.Number)>
           ╰╴<Context English.p1 at 34-38 (1 child)>
              ╰╴<Token 'Nine' at 34:38 (Literal.Number)>

The accompanying Transform classes are used to get the parsed results. Multiple
values are automatically detected (the result is always a list), and case does
not matter. For example::

    >>> from parce.transform import transform_text
    >>> transform_text(English.root, "one two THREE")
    [1, 2, 3]
    >>> transform_text(Nederlands.root, "eenentwintig")
    [21]

"""

import re

from parce import Language, lexicon, skip, default_target
from parce.action import Number
from parce.rule import bygroup, words
from parce.transform import Transform


__all__ = (
    "English", "EnglishTransform", "ENGLISH_TENS", "ENGLISH_TO19",
    "Nederlands", "NederlandsTransform", "NEDERLANDS_TENS", "NEDERLANDS_TO19",
    "Deutsch", "DeutschTransform", "DEUTSCH_TENS", "DEUTSCH_TO19",
    "Français", "FrançaisTransform", "FRANCAIS_TENS", "FRANCAIS_TO19",
)

#: English numerals from 0 to 19
ENGLISH_TO19 = (
    'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
    'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
    'sixteen', 'seventeen', 'eighteen', 'nineteen',
)

#: English tens from 20 upto and including 90
ENGLISH_TENS = (
    'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty',
    'ninety',
)

#: Dutch numerals from 0 to 19
NEDERLANDS_TO19 = (
    'nul', 'een', 'twee', 'drie', 'vier', 'vijf', 'zes', 'zeven', 'acht',
    'negen', 'tien', 'elf', 'twaalf', 'dertien', 'veertien', 'vijftien',
    'zestien', 'zeventien', 'achttien', 'negentien',
)

#: Dutch tens from 20 upto and including 90
NEDERLANDS_TENS = (
    'twintig', 'dertig', 'veertig', 'vijftig', 'zestig', 'zeventig', 'tachtig',
    'negentig',
)

#: German numerals from 0 to 19
DEUTSCH_TO19 = (
    'null', 'ein', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht',
    'neun', 'zehn', 'elf', 'zwölf', 'dreizehn', 'vierzehn', 'fünfzehn',
    'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn',
)

#: German tens from 20 upto and including 90
DEUTSCH_TENS = (
    'zwanzig', 'dreißig', 'vierzig', 'fünfzig', 'sechzig', 'siebzig', 'achtzig',
    'neunzig',
)

#: French numerals from 0 to 19
FRANCAIS_TO19 = (
    'zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit',
    'neuf', 'dix', 'onze', 'douze', 'treize', 'quatorze', 'quinze',
    'seize', 'dix-sept', 'dix-huit', 'dix-neuf',
)

#: French tens from 20 upto and including 90
FRANCAIS_TENS = (
    'vingt', 'trente', 'quarante', 'cinquante', 'soixante', 'soixante-dix',
    'quatre-vingt', 'quatre-vingt-dix',
)

_SKIP = r'[\s-]+', skip


def _values(tens, to19):
    """Get a dictionary mapping numerals to their value."""
    d = {}
    d.update((t, n) for n, t in enumerate(to19))
    d.update((t, n * 10) for n, t in enumerate(tens, 2))
    return d


class Numbers(Language):
    """Abstract base class to parse numbers from text in different languages."""

    _TO19 = ()
    _TENS = ()
    _HUNDRED = _THOUSAND = _MILLION = ''

    @lexicon
    def root(cls):
        """Find zero or more numbers."""
        yield default_target, cls.number, cls.p6, cls.p3, cls.p2, cls.n99

    @lexicon
    def number(cls):
        """A number."""
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def n99(cls):
        """Implement to parse a numerical value below 100."""

    @lexicon(re_flags=re.IGNORECASE)
    def p2(cls):
        """'Hundred' or values below 100."""
        yield _SKIP
        yield cls._HUNDRED, Number, -1, cls.n99
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p3(cls):
        """'Thousand' or values below 1000."""
        yield _SKIP
        yield cls._THOUSAND, Number, -1, cls.p2, cls.n99
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p6(cls):
        """'Million' or values below 1000000."""
        yield _SKIP
        yield cls._MILLION, Number, -1, cls.p3, cls.p2, cls.n99
        yield default_target, -1


class NumbersTransform(Transform):
    """Abstract base class for a Transform for numbers.

    Creates a list of zero or more numbers that were found.

    """
    _VALUES = {}

    def root(self, items):
        """The list of numbers."""
        return [i.obj for i in items]

    def number(self, items):
        """A number."""
        return sum(i.obj for i in items)

    def n99(self, items):
        """The numerical value (below 100) of a text string."""
        return sum(self._VALUES[i.text.lower()] for i in items)

    def _factor_func(factor):
        """Return the method to use for the specified factor."""
        def p(self, items):
            values = []
            for i in items:
                if i.is_token:  # always 'hundred'/'thousand', always the last one
                    return factor * sum(values) if values else factor
                else:
                    values.append(i.obj)
            return sum(values)
        p.__doc__ = "The value {0} or the sum of nested values below {0}.".format(factor)
        return p

    p2 = _factor_func(100)
    p3 = _factor_func(1000)
    p6 = _factor_func(1000000)

    del _factor_func


class English(Numbers):
    """Parse English numbers."""
    _TENS = ENGLISH_TENS
    _TO19 = ENGLISH_TO19
    _HUNDRED, _THOUSAND, _MILLION = "hundred", "thousand", "million"

    @lexicon(re_flags=re.IGNORECASE)
    def n99(cls):
        """Numerical value below 100."""
        yield _SKIP
        yield words(cls._TENS), Number, -1, cls.p1
        yield words(cls._TO19), Number, -1
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p1(cls):
        """Numerical value after a tenfold (e.g. 'three' after 'eighty')."""
        yield _SKIP
        yield words(cls._TO19[1:10]), Number, -1
        yield default_target, -1


class EnglishTransform(NumbersTransform):
    """Compute the value for English numbers.

    The result is a list of the numbers that were found. Whitespace and
    hyphens are skipped; multiple values are automatically detected.
    Case does not matter.

    For example::

        >>> from parce.transform import transform_text
        >>> from parce.lang.numbers import English
        >>> transform_text(English.root, "one two THREE")
        [1, 2, 3]
        >>> transform_text(English.root, "fiftysix")
        [56]
        >>> transform_text(English.root, "FiftySixThousandSevenHundredEightyNine")
        [56789]
        >>> transform_text(English.root, "twelve hundred thirty four")
        [1234]
        >>> transform_text(English.root, "twelve hundred thirty four five")
        [1234, 5]
        >>> transform_text(English.root, "Twelve Hundred Thirty Four Twenty Five")
        [1234, 25]

    """
    _VALUES = _values(ENGLISH_TENS, ENGLISH_TO19)

    p1 = NumbersTransform.n99


class Nederlands(Numbers):
    """Parse Dutch numbers."""
    _TENS = NEDERLANDS_TENS
    _TO19 = NEDERLANDS_TO19
    _HUNDRED, _THOUSAND, _MILLION = "honderd", "duizend", "miljoen"

    @lexicon(re_flags=re.IGNORECASE)
    def n99(cls):
        """Numerical value below 100."""
        yield _SKIP
        yield words(cls._TO19[10:]), Number, -1
        yield r'({})(?:\s*[eë]n\s*({}))?'.format(
            words(cls._TO19[1:10]),
            words(cls._TENS)), bygroup(Number, Number), -1
        yield words(cls._TENS), Number, -1
        yield cls._TO19[0], Number, -1
        yield default_target, -1


class NederlandsTransform(NumbersTransform):
    """Compute the value for Dutch numbers.

    The result is a list of the numbers that were found. Whitespace and
    hyphens are skipped; multiple values are automatically detected.
    Case does not matter.

    For example::

        >>> from parce.transform import transform_text
        >>> from parce.lang.numbers import Nederlands
        >>> transform_text(Nederlands.root, "een twee DRIE")
        [1, 2, 3]
        >>> transform_text(Nederlands.root, "zesenvijftig")
        [56]
        >>> transform_text(Nederlands.root, "ZesenVijftigDuizendZevenhonderdNegenenTachtig")
        [56789]
        >>> transform_text(Nederlands.root, "twaalfhonderd vier en dertig")
        [1234]
        >>> transform_text(Nederlands.root, "twaalfhonderd vier en dertig vijf")
        [1234, 5]
        >>> transform_text(Nederlands.root, "twaalfhonderd vier en dertig vijf en twintig")
        [1234, 25]

    """
    _VALUES = _values(NEDERLANDS_TENS, NEDERLANDS_TO19)


class Deutsch(Numbers):
    """Parse German numbers.

    Both ``'ein'`` and ``eins`` are allowed, and besides ``'dreißig'`` also
    ``'dreissig'`` is supported.

    """
    _TENS = DEUTSCH_TENS
    _TO19 = DEUTSCH_TO19
    _HUNDRED, _THOUSAND, _MILLION = "hundert", "tausend", "million"

    @lexicon(re_flags=re.IGNORECASE)
    def n99(cls):
        """Numerical value below 100."""
        yield _SKIP
        TENS = cls._TENS + ('dreissig',)
        yield words(cls._TO19[10:]), Number, -1
        yield r'({})(?:\s*und\s*({}))?'.format(
            words(cls._TO19[1:10]),
            words(TENS)), bygroup(Number, Number), -1
        yield words(TENS + cls._TO19[:1] + ('eins',)), Number, -1
        yield default_target, -1


class DeutschTransform(NumbersTransform):
    """Compute the value for German numbers.

    Both ``'ein'`` and ``eins`` are allowed, and besides ``'dreißig'`` also
    ``'dreissig'`` is supported.

    The result is a list of the numbers that were found. Whitespace and
    hyphens are skipped; multiple values are automatically detected.
    Case does not matter.

    For example::

        >>> from parce.transform import transform_text
        >>> from parce.lang.numbers import Deutsch
        >>> transform_text(Deutsch.root, "ein zwei DREI")
        [1, 2, 3]
        >>> transform_text(Deutsch.root, "eins zwei DREI")
        [1, 2, 3]
        >>> transform_text(Deutsch.root, "Sechsundfünfzig")
        [56]
        >>> transform_text(Deutsch.root, "Sechsundfünfzig Tausend Siebenhundert NeunundAchtzig")
        [56789]
        >>> transform_text(Deutsch.root, "Zwölfhundert Vierunddreißig")
        [1234]
        >>> transform_text(Deutsch.root, "Zwölfhundert Vierunddreissig Fünf")
        [1234, 5]
        >>> transform_text(Deutsch.root, "Zwölfhundert Vierunddreißig Fünf und Zwanzig")
        [1234, 25]

    """
    _VALUES = _values(DEUTSCH_TENS, DEUTSCH_TO19)
    _VALUES['eins'] = _VALUES['ein']
    _VALUES['dreissig'] = _VALUES['dreißig']


class Français(Numbers):
    """Parse French numbers.

    Supports both ``'zéro'`` and ``'zero'``, and allows for the ``'s'`` after
    ``"quatre-vingt"``, ``"cent"``, ``"million"``.

    """
    _TENS = FRANCAIS_TENS
    _TO19 = FRANCAIS_TO19
    _HUNDRED, _THOUSAND, _MILLION = "cents?", "mille", "millions?"

    @lexicon(re_flags=re.IGNORECASE)
    def n99(cls):
        """Numerical value below 100."""
        yield _SKIP
        tens = (cls._TENS[4], cls._TENS[6]) # soixante, quatre-vingt + 10-19
        yield r'({})[\s-]*({})'.format(
            words(tens), words(cls._TO19[1:10])), bygroup(Number, Number), -1
        # vingt, treize, quatorze, cinquante, soixante, quatre-vingt (+ 0-9)
        tens = cls._TENS[:5] + cls._TENS[6:7]
        yield r'({})(?:[\s-]*(?:et)?[\s-]*({}))?'.format(
            words(tens), words(cls._TO19[1:10])), bygroup(Number, Number), -1
        yield words(cls._TO19), Number, -1
        yield words(('quatre-vingts', 'zero')), Number, -1
        yield default_target, -1


class FrançaisTransform(NumbersTransform):
    """Compute the value for French numbers.

    Supports both ``'zéro'`` and ``'zero'``, and allows for the ``'s'`` after
    ``"quatre-vingt"``, ``"cent"``, ``"million"``.

    The result is a list of the numbers that were found. Whitespace and
    hyphens are skipped; multiple values are automatically detected.
    Case does not matter.

    For example::

        >>> from parce.transform import transform_text
        >>> from parce.lang.numbers import Francais
        >>> transform_text(Francais.root, 'un deux TROIS')
        [1, 2, 3]
        >>> transform_text(Francais.root, 'cinquante-six')
        [56]
        >>> transform_text(Francais.root, 'cinquante-six mille sept-cents quatre-vingt neuf')
        [56789]
        >>> transform_text(Francais.root, 'mille deux cent trente-quatre')
        [1234]
        >>> transform_text(Francais.root, 'mille deux cent trente-quatre cinq')
        [1234, 5]
        >>> transform_text(Francais.root, 'mille deux cent trente-quatre vingt-cinq')
        [1234, 25]

    """
    _VALUES = _values(FRANCAIS_TENS, FRANCAIS_TO19)
    _VALUES['zero'] = _VALUES['zéro']
    _VALUES['quatre-vingts'] = _VALUES['quatre-vingt']

