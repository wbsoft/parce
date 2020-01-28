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
Maps standard actions to CSS classes.
"""


from . import *


mapping = {

    # these are the base standard actions
    Whitespace              : "whitespace",
    Text                    : "text",
    Escape                  : "escape",
    Keyword                 : "keyword",
    Name                    : "name",
    Literal                 : "literal",
    Delimiter               : "delimiter",
    Comment                 : "comment",
    Error                   : "error",

    # these inherit from the base standard actions
    Literal.Boolean         : "boolean",
    Literal.Char            : "char",
    Literal.Number          : "number",
    Literal.String          : "string",
    Literal.String.Escape   : "escape",
    Literal.Verbatim        : "verbatim",

    Delimiter.Operator      : "operator",

    Name.Attribute          : "attribute",
    Name.Builtin            : "builtin",
    Name.Class              : "class",
    Name.Constant           : "constant",
    Name.Element            : "element",
    Name.Function           : "function",
    Name.Identifier         : "identifier",
    Name.Property           : "property",
    Name.Tag                : "tag",
    Name.Variable           : "variable",

}


def css_classes(action):
    """Return a tuple of CSS class names for the specified action."""
    def gen():
        for a in action:
            try:
                yield mapping[a]
            except KeyError:
                pass
    return tuple(gen())


