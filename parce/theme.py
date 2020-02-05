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
This module provides the Theme class, which provides text formatting
properties based on the action (standard action) of a Token.

These properties can be used to colorize text according to a language
definition.

By default, the properties are read from a normal CSS file, although
other storage backends could be devised.

"""

def css_classes(action):
    """Return a tuple of lower-case CSS class names for the specified standard action."""
    return tuple(a._name.lower() for a in action)


