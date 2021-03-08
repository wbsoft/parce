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
Parse numbers.

Use the accompanying Transform to get the parsed result.

"""

import re

from parce import Language, lexicon, skip, default_target
from parce.action import Number
from parce.rule import words
from parce.transform import Transform


EN_TO_19 = (
    'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
    'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
    'sixteen', 'seventeen', 'eighteen', 'nineteen',
)

EN_TENFOLDS = (
    'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty',
    'ninety',
)

SKIP = r'[\s-]+', skip

EN_VALUES = {}
EN_VALUES.update((t, n) for n, t in enumerate(EN_TO_19))
EN_VALUES.update((t, n * 10) for n, t in enumerate(EN_TENFOLDS, 2))


class English(Language):
    """Parse english numbers."""
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
        """Numerical value below 100."""
        yield SKIP
        yield words(EN_TENFOLDS), Number, -1, cls.p1
        yield words(EN_TO_19), Number, -1
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p1(cls):
        """Numerical value after a tenfold (e.g. 'three' after 'eighty')."""
        yield SKIP
        yield words(EN_TO_19[1:10]), Number, -1
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p2(cls):
        """'Hundred' or values below 100."""
        yield SKIP
        yield "hundred", Number, -1, cls.n99
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p3(cls):
        """'Thousand' or values below 1000."""
        yield SKIP
        yield "thousand", Number, -1, cls.p2, cls.n99
        yield default_target, -1

    @lexicon(re_flags=re.IGNORECASE)
    def p6(cls):
        """'Million' or values below 1000000."""
        yield SKIP
        yield "million", Number, -1, cls.p3, cls.p2, cls.n99
        yield default_target, -1


class EnglishTransform(Transform):
    """Compute the value for english numbers.

    The result is a list of the numbers that were found. Whitespace and
    hyphens are skipped; multiple values are automatically detected.

    For example::

        >>> from parce.transform import transform_text
        >>> from parce.lang.numbers import English
        >>> transform_text(English.root, "one two three")
        [1, 2, 3]
        >>> transform_text(English.root, "fiftysix")
        [56]
        >>> transform_text(English.root, "fiftysixthousandsevenhundredeightynine")
        [56789]
        >>> transform_text(English.root, "twelve hundred thirty four")
        [1234]
        >>> transform_text(English.root, "twelve hundred thirty four five")
        [1234, 5]
        >>> transform_text(English.root, "twelve hundred thirty four twenty five")
        [1234, 25]


    """
    def root(self, items):
        return [i.obj for i in items]

    def number(self, items):
        return sum(i.obj for i in items)

    def n99(self, items):
        for t in items:
            return EN_VALUES[t.text]

    p1 = n99

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
        return p

    p2 = _factor_func(100)
    p3 = _factor_func(1000)
    p6 = _factor_func(1000000)

    del _factor_func


