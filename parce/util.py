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
Various utility functions.
"""

import codecs


def abbreviate_repr(s, length=30):
    """Elegantly abbreviate repr text."""
    if len(s) > length:
        return repr(s[:length-2]) + "..."
    return repr(s)


def merge_adjacent_actions(tokens):
    """Yield four-tuples (pos, end, action, language).

    Adjacent actions that are the same are merged into
    one range.

    """
    stream = ((t.pos, t.end, t.action, t.parent.lexicon.language) for t in tokens)
    for pos, end, action, lang in stream:
        for npos, nend, naction, nlang in stream:
            if naction != action or npos > end or nlang != lang:
                yield pos, end, action, lang
                pos, action, lang = npos, naction, nlang
            end = nend
        yield pos, end, action, lang


def get_bom_encoding(data):
    """Get the BOM (Byte Order Mark) of data, if any.

    A two-tuple is returned (encoding, data). If the data starts with a BOM
    mark, its encoding is determined and the BOM mark is stripped off.
    Otherwise, the returned encoding is None and the data is returned
    unchanged.

    """
    for bom, encoding in (
        (codecs.BOM_UTF8, 'utf-8'),
        (codecs.BOM_UTF16_LE, 'utf_16_le'),
        (codecs.BOM_UTF16_BE, 'utf_16_be'),
        (codecs.BOM_UTF32_LE, 'utf_32_le'),
        (codecs.BOM_UTF32_BE, 'utf_32_be'),
            ):
        if data.startswith(bom):
            return encoding, data[len(bom):]
    return None, data


def split_list(l, separator):
    """Split list on items that compare equal to separator.

    Yields result lists that may be empty.

    """
    try:
        i = l.index(separator)
    except ValueError:
        yield l
    else:
        yield l[:i]
        yield from split_list(l[i+1:], separator)


