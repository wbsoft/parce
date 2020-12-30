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
This module provides Indenter to indent a Document.

To adapt the indenting behaviour, you only need to implement the
:meth:`AbstractIndenter.indent_events` method.

The following events can be yielded (simply module constants):

    ``BLANK``:
        this is a blank line, the current indent level is not changed

    ``CURRENT_INDENT, string``:
        the current indent string this line has.

    ``INDENT`` [``, string``]:
        next line should be indented a level. If string is given, that indent
        is used instead of the default indent (relatively to the start of the
        text in the current line excluding the current indent).

    ``NO_INDENT``:
        the indent of this line may not be changed at all, e.g. because it is
        part of a multiline string.

    ``DEDENT``:
        next line should be dedented a level. (If this event occurs before
        ``INDENT`` or ``NO_DEDENT``, the current line can be dedented.)

    ``NO_DEDENT``:
        further ``DEDENT`` events will not dedent the current line anymore, but
        rather affect the indentation of the next line.

    ``PREFER_INDENT``, ``string``:
        use this indent for the current line, but do not change the indent
        level or the current indent for the next line.


"""

### NOTE!  In docs/source/indent.rst all classes should be added, because
###        we do not use the :members: directive to improve documentation
###        for the IndentInfo named tuple.
### See: https://stackoverflow.com/questions/61572220/python-sphinx-namedtuple-documentation


import collections


BLANK           = 1
CURRENT_INDENT  = 2
INDENT          = 3
NO_INDENT       = 4
DEDENT          = 5
NO_DEDENT       = 6
PREFER_INDENT   = 7


Dedenters = collections.namedtuple("Dedenters", "start end")
"""Dedenters at the ``start`` and the ``end`` of the line."""


IndentInfo = collections.namedtuple("IndentInfo",
    "block is_blank indent allow_indent indenters dedenters prefer_indent")
"""Contains information about how to indent a block.

Created by :meth:`AbstractIndenter.indent_info`.

.. py:attribute:: block

    The text block (line)

.. py:attribute:: is_blank

    True if this is a blank line.

.. py:attribute:: indent

    The current indent string (probably consisting of spaces and tabs).

.. py:attribute:: allow_indent

    True if the indent of this block may be changed.

.. py:attribute:: indenters

    A list of string or None items. Every item means an indent level, if the
    item is not None, it is the string to use, otherwise a default indent
    string is used according to the indenter preferences.

.. py:attribute:: dedenters

    A named tuple Dedenters(start, end) of the levels that should be decreased
    at the beginning of this block, and after the end of this block.

.. py:attribute:: prefer_indent

    The indent to be used for this line, as a special case. The current indent
    level is not changed.


"""

class AbstractIndenter:
    """Indents (part of) a Document.

    """
    def __init__(self):
        pass

    def indent_info(self, block, prev_indents=()):
        """Return an IndentInfo object for the specified block."""

        blank = False
        allow_indent = True
        indent = ""
        indenters = []
        dedenters_start = 0
        dedenters_end = 0
        prefer_indent = None

        find_dedenters = True

        for event, *args in self.indent_events(block, prev_indents):
            if event is BLANK:
                blank = True
            elif event is CURRENT_INDENT:
                indent = args.pop()
            elif event is INDENT:
                indenters.append(args.pop() if args else None)
                find_dedenters = False
            elif event is NO_INDENT:
                allow_indent = False
            elif event is DEDENT:
                if find_dedenters:
                    dedenters_start += 1
                elif indenters:
                    indenters.pop()
                else:
                    dedenters_end += 1
            elif event is NO_DEDENT:
                find_dedenters = False
            elif event is PREFER_INDENT:
                prefer_indent = args.pop()

        dedenters = Dedenters(dedenters_start, dedenters_end)
        return IndentInfo(block, blank, indent, allow_indent, indenters, dedenters, prefer_indent)

    def indent_events(self, block, prev_indents=()):
        """Implement this method to yield indenting events for the block."""
        yield CURRENT_INDENT, ""




