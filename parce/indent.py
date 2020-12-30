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
``indent_events()`` method.

The following events can be yielded (simply constants):

    IS_BLANK:
        this is a blank line

    CURRENT_INDENT, string:
        the current indent string this line has

    INDENT:
        next line should be indented a level

    DEDENT:
        next line should be dedented a level. (If this event occurs before
        INDENT or REGULAR_TEXT, the current line can be dedented.)

    ALIGN, pos:
        when yielded after INDENT, allows the indenter to position
        text exactly instead of using the default indent

    REGULAR_TEXT:
        further DETENT events will not dedent the current line anymore.

    PREFER_INDENT, string:
        use this indent for the current line, but do not change the current
        indent for the next line.


"""


IS_BLANK        = 1
CURRENT_INDENT  = 2
INDENT          = 3
DEDENT          = 4
ALIGN           = 5
REGULAR_TEXT    = 6
PREFER_INDENT   = 7



class AbstractIndenter:
    """Indents (part of) a Document.

    """
    def __init__(self):
        pass

    def indent_events(self, block, previous_indent=None):
        """Implement this method to yield indenting events for the block."""

