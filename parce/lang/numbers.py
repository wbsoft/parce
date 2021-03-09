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

Use the accompanying Transform to get the parsed result.

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
)


ENGLISH_TO19 = (
    'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
    'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
    'sixteen', 'seventeen', 'eighteen', 'nineteen',
)

ENGLISH_TENS = (
    'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty',
    'ninety',
)

NEDERLANDS_TO19 = (
    'nul', 'een', 'twee', 'drie', 'vier', 'vijf', 'zes', 'zeven', 'acht',
    'negen', 'tien', 'elf', 'twaalf', 'dertien', 'veertien', 'vijftien',
    'zestien', 'zeventien', 'achttien', 'negentien',
)

NEDERLANDS_TENS = (
    'twintig', 'dertig', 'veertig', 'vijftig', 'zestig', 'zeventig', 'tachtig',
    'negentig',
)

DEUTSCH_TO19 = (
    'null', 'ein', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht',
    'neun', 'zehn', 'elf', 'zwölf', 'dreizehn', 'vierzehn', 'fünfzehn',
    'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn',
)

DEUTSCH_TENS = (
    'zwanzig', 'dreißig', 'vierzig', 'fünfzig', 'sechzig', 'siebzig', 'achtzig',
    'neunzig',
)

_SKIP = r'[\s-]+', skip


def _values(tens, to19):
    """Get a dictionary mapping numerals to their value."""
    d = {}
    d.update((t, n) for n, t in enumerate(to19))
    d.update((t, n * 10) for n, t in enumerate(tens, 2))
    return d


class _Numbers(Language):
    """Parse numbers from text in different languages."""

    TO19 = ()
    TENS = ()
    HUNDRED = THOUSAND = MILLION = ''

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
        yield cls.HUNDRED, Number, -1, cls.n99
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p3(cls):
        """'Thousand' or values below 1000."""
        yield _SKIP
        yield cls.THOUSAND, Number, -1, cls.p2, cls.n99
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p6(cls):
        """'Million' or values below 1000000."""
        yield _SKIP
        yield cls.MILLION, Number, -1, cls.p3, cls.p2, cls.n99
        yield default_target, -1


class _NumbersTransform(Transform):
    """Generic transform for numbers.

    Creates a list of the numbers that were found.

    """
    VALUES = {}

    def root(self, items):
        """The list of numbers."""
        return [i.obj for i in items]

    def number(self, items):
        """A number."""
        return sum(i.obj for i in items)

    def n99(self, items):
        """The numerical value of a text string."""
        return self.VALUES[items[0].text.lower()]

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


class English(_Numbers):
    """Parse English numbers."""
    TENS = ENGLISH_TENS
    TO19 = ENGLISH_TO19
    HUNDRED, THOUSAND, MILLION = "hundred", "thousand", "million"

    @lexicon(re_flags=re.IGNORECASE)
    def n99(cls):
        """Numerical value below 100."""
        yield _SKIP
        yield words(cls.TENS), Number, -1, cls.p1
        yield words(cls.TO19), Number, -1
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p1(cls):
        """Numerical value after a tenfold (e.g. 'three' after 'eighty')."""
        yield _SKIP
        yield words(cls.TO19[1:10]), Number, -1
        yield default_target, -1


class EnglishTransform(_NumbersTransform):
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
    VALUES = _values(ENGLISH_TENS, ENGLISH_TO19)

    p1 = _NumbersTransform.n99


class Nederlands(_Numbers):
    """Parse Dutch numbers."""
    TENS = NEDERLANDS_TENS
    TO19 = NEDERLANDS_TO19
    HUNDRED, THOUSAND, MILLION = "honderd", "duizend", "miljoen"

    @lexicon(re_flags=re.IGNORECASE)
    def n99(cls):
        """Numerical value below 100."""
        yield _SKIP
        yield words(cls.TO19[10:]), Number, -1
        yield r'({})(?:\s*[eë]n\s*({}))?'.format(
            words(cls.TO19[1:10]),
            words(cls.TENS)), bygroup(Number, Number), -1
        yield words(cls.TENS), Number, -1
        yield cls.TO19[0], Number, -1
        yield default_target, -1


class NederlandsTransform(_NumbersTransform):
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
    VALUES = _values(NEDERLANDS_TENS, NEDERLANDS_TO19)

    def n99(self, items):
        """The numerical value (below 100) of a text string."""
        return sum(self.VALUES[i.text.lower()] for i in items)


class Deutsch(_Numbers):
    """Parse German numbers.

    Both ``'ein'`` and ``eins`` are allowed, and besides ``'dreißig'`` also
    ``'dreissig'`` is supported.

    """
    TENS = DEUTSCH_TENS
    TO19 = DEUTSCH_TO19
    HUNDRED, THOUSAND, MILLION = "hundert", "tausend", "million"

    @lexicon(re_flags=re.IGNORECASE)
    def n99(cls):
        """Numerical value below 100."""
        yield _SKIP
        TENS = cls.TENS + ('dreissig',)
        yield words(cls.TO19[10:]), Number, -1
        yield r'({})(?:\s*und\s*({}))?'.format(
            words(cls.TO19[1:10]),
            words(TENS)), bygroup(Number, Number), -1
        yield words(TENS + cls.TO19[:1] + ('eins',)), Number, -1
        yield default_target, -1


class DeutschTransform(_NumbersTransform):
    """Compute the value for German numbers.

    Both ``'ein'`` and ``eins`` are allowed, and besides ``'dreißig'`` also
    ``'dreissig'`` is supported.

    The result is a list of the numbers that were found. Whitespace and
    hyphens are skipped; multiple values are automatically detected.
    Case does not matter.

    For example::

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
    VALUES = _values(DEUTSCH_TENS, DEUTSCH_TO19)
    VALUES['eins'] = VALUES['ein']
    VALUES['dreissig'] = VALUES['dreißig']

    def n99(self, items):
        """The numerical value (below 100) of a text string."""
        return sum(self.VALUES[i.text.lower()] for i in items)


