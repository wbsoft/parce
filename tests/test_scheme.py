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
Test the scheme language definition and the scheme number parsing.
"""


import cmath
import math
import pytest
import fractions

## find parce

import sys
sys.path.insert(0, '.')



def scheme_numbers():
    """Test scheme numbers."""
    from parce.lang.scheme import scheme_number_from_text as s

    # common value
    assert s("123") == 123

    # octal
    assert s('#o30071') == 12345

    # fractions inside hex :-)
    assert s('#xdead/beef') == fractions.Fraction(57005, 48879)

    # decimal fraction
    assert s('1/3') == fractions.Fraction(1, 3)

    # inexact creates a float
    assert s('#i1/3') == 1/3

    # binary
    assert s('#b1111') == 15

    # exact forces float into fraction
    assert s('#e1e-1') == fractions.Fraction(1, 10)

    # inf/nan
    assert s('+inf.0') == math.inf
    assert s('-inf.0') == -math.inf
    assert s('+nan.0') is math.nan

    # complex numbers
    assert s('+i') == s('0+1i') == complex(0, 1)
    assert s('-i') == s('0-1i') == complex(0, -1)
    assert s('23+45i') == complex(23, 45)
    assert s('+inf.0+inf.0i') == complex(math.inf, math.inf)

    # polar coordinates
    assert s('2@2') == cmath.rect(2, 2)
    assert s('12.34@56.78') == cmath.rect(12.34, 56.78)

    # a dot too much
    with pytest.raises(ValueError):
        s('123.34.5')

    # a '2' is not valid in binary input
    with pytest.raises(ValueError):
        s('#b2111')

    # missing exponent
    with pytest.raises(ValueError):
        s('1e')

    # zero division
    with pytest.raises(ZeroDivisionError):
        s('1/0')


def test_main():
    """Test scheme stuff."""
    scheme_numbers()


if __name__ == "__main__":
    test_main()

