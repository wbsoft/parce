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
Scheme.

Tries to adhere to the official Scheme syntax, especially the complicated
number syntax. See for more information:

* https://www.gnu.org/software/guile/manual/r5rs.html#Formal-syntax
* https://www.scheme.com/tspl4/grammar.html

"""

__all__ = ('Scheme', 'SchemeLily', 'scheme_number')

import re


from parce import Language, lexicon, skip, default_action, default_target
from parce.action import *
from parce.rule import *


RE_SCHEME_RIGHT_BOUND = r"(?=$|[()\s;]|#\()"

RE_SCHEME_ID_SPECIAL_INITIAL = r'!$%&*/:<=>?^_~'
RE_SCHEME_ID_INITIAL = r'(?:[^\W\d]|[' + RE_SCHEME_ID_SPECIAL_INITIAL + '])'
RE_SCHEME_ID_SUBSEQUENT = r'[\w' + RE_SCHEME_ID_SPECIAL_INITIAL + '@.+-]'
RE_SCHEME_ID_PECULIAR = r'[-+]|\.{3}'

RE_SCHEME_ID = r'(?:' + \
    RE_SCHEME_ID_PECULIAR + \
    '|' + RE_SCHEME_ID_INITIAL + '(?:' + RE_SCHEME_ID_SUBSEQUENT + ')*' + \
    ')' + RE_SCHEME_RIGHT_BOUND


class Scheme(Language):
    @lexicon
    def root(cls):
        yield from cls.common()

    @classmethod
    def common(cls, pop=0):
        """Yield common stuff. ``pop`` can be set to -1 for one-arg mode."""
        yield r"['`]|,@?", Delimiter.Scheme.Quote
        yield r"\(", Delimiter.OpenParen, pop, cls.list
        yield r"#\(", Delimiter.OpenVector, pop, cls.vector
        yield r'"', String, pop, cls.string
        yield r';', Comment, pop, cls.singleline_comment
        yield r'#!', Comment, pop, cls.multiline_comment

        yield r"#[tTfF]\b", Number.Boolean, pop
        yield r"#\\([a-z]+|.)", Character, pop
        yield RE_SCHEME_ID, cls.get_word_action(), pop

        yield r'(#[eEiI])?(#([bBoOxXdD]))(#[eEiI])?', findmember(MATCH[3], (
            ('bB', (bygroup(Number.Prefix, Number.Prefix.Binary, skip, Number.Prefix), pop, cls.number(2))),
            ('oO', (bygroup(Number.Prefix, Number.Prefix.Octal, skip, Number.Prefix), pop, cls.number(8))),
            ('xX', (bygroup(Number.Prefix, Number.Prefix.Hexadecimal, skip, Number.Prefix), pop, cls.number(16)))),
               (bygroup(Number.Prefix, Number.Prefix.Decimal, skip, Number.Prefix), pop, cls.number))
        yield r'#[eEiI]', Number.Prefix, pop, cls.number
        yield r'[-+]inf.0', Number.Infinity, pop, cls.number
        yield r'[-+]nan.0', Number.NaN, pop, cls.number
        yield r'[-+]', Operator.Sign, pop, cls.number
        yield r'(\.?)(\d+)', bygroup(Number.Dot, Number.Decimal), pop, cls.number

        if pop == 0:
            yield r"\.(?!\S)", Delimiter.Dot

    @lexicon(consume=True)
    def list(cls):
        yield r"\)", Delimiter.CloseParen, -1
        yield from cls.common()

    @lexicon(consume=True)
    def vector(cls):
        yield r"\)", Delimiter.CloseVector, -1
        yield from cls.common()

    @classmethod
    def get_word_action(cls):
        """Return a dynamic action that is chosen based on the text."""
        from . import scheme_words
        return ifmember(TEXT, scheme_words.keywords, Keyword, Name)

    # -------------- Number ---------------------
    @lexicon(consume=True, re_flags=re.I)
    def number(self):
        """Decimal numbers, derive with 2 for binary, 8 for octal, 16 for hexadecimal numbers."""
        yield RE_SCHEME_RIGHT_BOUND, None, -1
        _pat = lambda radix: '[{}]+'.format('0123456789abcdef'[:radix or 10])
        yield pattern(call(_pat, ARG)), \
            dselect(ARG, {2: Number.Binary, 8: Number.Octal, 16: Number.Hexadecimal}, Number.Decimal)
        yield r'[-+]inf.0', Number.Infinity
        yield r'[-+]nan.0', Number.NaN
        yield r'[-+]', Operator.Sign
        yield 'i', Number.Imaginary
        yield ifarg(None, '([esfdl])([-+])?'), bygroup(Number.Exponent, Operator.Sign)
        yield ifarg(None, r'\.'), Number.Dot
        yield '@', Separator.Polar
        yield '/', Separator.Fraction
        yield '#+', Number.Special.UnknownDigit
        yield default_action, Number.Invalid

    # -------------- String ---------------------
    @lexicon(consume=True)
    def string(cls):
        yield r'"', String, -1
        yield from cls.string_common()

    @classmethod
    def string_common(cls):
        yield r'\\[\\"|afnrtvb]', String.Escape
        yield default_action, String

    # -------------- Comment ---------------------
    @lexicon(consume=True)
    def multiline_comment(cls):
        yield r'!#', Comment, -1
        yield from cls.comment_common()

    @lexicon(re_flags=re.MULTILINE, consume=True)
    def singleline_comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1


class SchemeLily(Scheme):
    """Scheme used with LilyPond."""
    @lexicon(consume=True)
    def scheme(cls):
        """Pick one thing and pop back."""
        yield r'\s+', skip
        yield from cls.common(cls.argument)
        yield default_target, -1

    @lexicon(consume=True)
    def argument(cls):
        """One Scheme expression."""
        yield default_target, -2

    @classmethod
    def common(cls, pop=0):
        from . import lilypond
        yield r"#{", Bracket.LilyPond.Start, pop, lilypond.LilyPond.schemelily
        yield from super().common(pop)


def scheme_number(tokens):
    """Return the Python value of the Scheme number in the specified tokens
    iterable.

    All ``tokens`` that can be in the :meth:`Scheme.number` context are
    supported. Supports all features: nan, +/- inf, fractions, exactness,
    complex numbers and polar coordinates.

    Raises ValueError or ZeroDivisionError on faulty input.

    """

    import cmath, fractions, math
    from parce.util import split_list


    radix = 10
    exact = None
    tokens = list(tokens)

    _radix_map = {'b': 2, 'o': 8, 'd': 10, 'x': 16}


    def get_uint(tokens):
        """Get an unsigned integer from the tokens.

        Returns a float when there were unknown digits (``#``) and there was
        no exact prefix (``#e``)

        """
        v = 0
        for t in tokens:
            if t.action in (Number.Decimal, Number.Binary, Number.Octal, Number.Hexadecimal):
                v = int(t.text, radix)
            elif t.action is Number.Special.UnknownDigit:
                v *= radix * len(t.text)
                return float(v) if not exact else v
            else:
                break
        return v

    def get_decimal10(tokens):
        """Get a decimal10 value from the tokens. Only called in decimal mode."""
        v = []
        e = True
        i, z = 0, len(tokens)
        while i < z:
            t = tokens[i]
            if t.action is Number.Decimal:
                v.append(t.text)
            elif t.action is Number.Special.UnknownDigit:
                v.append('0' * len(t.text))
            elif t.action is Number.Dot:
                if '.' not in v:
                    v.append('.')
                    e = False
            elif t.action is Number.Exponent:
                v.append('e')
                e = False
                i += 1
                while i < z:
                    t = tokens[i]
                    if t.action is Operator.Sign:
                        v.append(t.text)
                    elif t.action is Number.Decimal:
                        v.append(t.text)
                        break
                    else:
                        break
                    i += 1
            i += 1
        s = ''.join(v)
        if e:
            return float(s) if exact is False else int(s)
        return fractions.Fraction(s) if exact else float(s)

    def get_real(tokens):
        """Return a real value from the tokens (can be int, float or Fraction.)."""
        # get a sign, inf or nan
        i, z = 0, len(tokens)
        sign = 1
        while i < z:
            t = tokens[i]
            if t.action is Operator.Sign:
                if t == '-':
                    sign *= -1
            elif t.action is Number.Infinity:
                return math.inf if t.text[0] == '+' else -math.inf
            elif t.action is Number.NaN:
                return math.nan
            else:
                break
            i += 1
        # now, get either uint, uint/uint or decimal10
        tokens, *fract = split_list(tokens[i:], '/')
        if fract:
            numerator = get_uint(tokens)
            denominator = get_uint(fract[0])
            if isinstance(numerator, float) or isinstance(denominator, float) or exact is False:
                v = numerator / denominator
            else:
                v = fractions.Fraction(numerator, denominator)
        elif radix == 10:
            v = get_decimal10(tokens)
        else:
            v = get_uint(tokens)
        return sign * v

    def get_complex(tokens):
        """Return a complex value from the tokens."""
        # find the imaginary part
        i = len(tokens) - 2
        while i:
            t = tokens[i]
            if t.action in (Number.Infinity, Number.NaN):
                break
            elif t.action is Operator.Sign and t.group is None:
                # (for a sign after an exponent, t.group is -1)
                break
            i -= 1
        else:
            return complex()
        real = tokens[:i]
        imag = tokens[i:-1]
        return complex(get_real(real), get_real(imag))

    ### main function body

    # get the prefixes
    i, z = 0, len(tokens)
    while i < z:
        t = tokens[i]
        if t.action in Number.Prefix:
            p = t.text[1].lower()
            if p == 'i':
                exact = False
            elif p == 'e':
                exact = True
            else:
                radix = _radix_map[p]
        else:
            break
        i += 1

    tokens, *polar = split_list(tokens[i:], '@')

    if polar:
        return cmath.rect(get_real(tokens), get_real(polar[0]))
    if tokens and tokens[-1].text.lower() == 'i':
        return get_complex(tokens)
    return get_real(tokens)

