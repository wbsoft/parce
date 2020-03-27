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
Standard actions defined in the parce module namespace.
"""

from . import action

# Note: this file is literally shown in the documentation (stdactions.rst)
# from line 30 on.
# ------------------------------------------------------------------------


# Base actions:

Whitespace = action.StandardAction("Whitespace")
Text = action.StandardAction("Text")

Comment = action.StandardAction("Comment")
Delimiter = action.StandardAction("Delimiter")
Error = action.StandardAction("Error")
Escape = action.StandardAction("Escape")
Keyword = action.StandardAction("Keyword")
Literal = action.StandardAction("Literal")
Name = action.StandardAction("Name")
Pseudo = action.StandardAction("Pseudo")
Template = action.StandardAction("Template")

# Actions that derive from Name:

Name.Attribute
Name.Builtin
Name.Class
Name.Command
Name.Constant
Name.Decorator
Name.Exception
Name.Function
Name.Identifier
Name.Macro
Name.Method
Name.Namespace
Name.Object
Name.Property
Name.Symbol
Name.Tag
Name.Variable

# Actions that derive from Literal:

Verbatim = Literal.Verbatim
Value = Literal.Value
String = Literal.String
Number = Literal.Number
Boolean = Literal.Boolean
Char = Literal.Char
Literal.Color
Literal.Email
Literal.Url

# Actions that derive from String:

String.Double
String.Single
String.Escape

# Other derived actions:

Comment.Alert
Operator = Delimiter.Operator
Template.Preprocessed
Text.Deleted
Text.Inserted

