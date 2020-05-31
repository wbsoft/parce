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
This module defines a fairly large amount of standard actions.
Most are used by the bundled language definitions and may also be used
or inherited from by your own language definitions.

The themes built into *parce* also use the names of these standard actions
to determine the visual appearance of parsed text pieces.

See for a full listing :doc:`stdactions`. See the :mod:`~parce.standardaction`
module for more information about standard actions.

"""

from . import standardaction

# Note: the marked part below of this file is literally shown in the
# documentation (stdactions.rst)

# BEGIN_ACTIONS

a = standardaction.StandardAction

# Base actions, derive from these:

Text            = a("Text")
Whitespace      = a("Whitespace")
Keyword         = a("Keyword")
Delimiter       = a("Delimiter")
Name            = a("Name")             # see below for many derived actions
Literal         = a("Literal")          # see below for many derived actions
Comment         = a("Comment")


# Mixin actions, yield subtle style changes:

Alert           = a("Alert")
Important       = a("Important")
Unimportant     = a("Unimportant")
Special         = a("Special")

Definition      = a("Definition")       # a thing is defined (vs referred to)
Invalid         = a("Invalid")          # invalid input
Escape          = a("Escape")           # escaped text like \n in a string
Template        = a("Template")         # a template for something else
Pseudo          = a("Pseudo")           # e.g. a pseudo-class or -comment
Preprocessed    = a("Preprocessed")

Inserted        = a("Inserted")         # inserted text (e.g. in a diff)
Deleted         = a("Deleted")          # deleted text (e.g. in a diff)
Quoted          = a("Quoted")           # e.g. a blockquote
Bold            = a("Bold")             # Bold text
Emphasized      = a("Emphasized")       # Emphasized text


# Mixin actions that are not styled by default:

Start           = a("Start")            # start of something
End             = a("End")              # end of something
Indent          = a("Indent")           # denotes an indent
Dedent          = a("Dedent")           # denotes a dedent


# Actions that derive of Name:

Name.Attribute
Name.Builtin
Name.Class
Name.Command
Name.Constant
Name.Decorator
Name.Entity
Name.Exception
Name.Function
Name.Identifier
Name.Macro
Name.Markup
Name.Method
Name.Namespace
Name.Object
Name.Property
Name.Symbol
Name.Tag
Name.Type
Name.Variable


# Actions that derive of Literal:

Data            = Literal.Data
Verbatim        = Literal.Verbatim
String          = Literal.String        # a quoted string
Character       = Literal.Character     # a single character
Number          = Literal.Number        # a numeric value
Literal.Color
Literal.Email
Literal.Url
Literal.Timestamp
Literal.Input
Literal.Output
Literal.Error
Literal.Prompt


# Actions that derive of String:

String.Double
String.Single


# Actions that derive of Number:

Number.Decimal
Number.Int
Number.Float
Number.Binary
Number.Hexadecimal
Number.Octal
Number.Fraction
Number.Boolean
Number.Infinity
Number.NaN


# Actions that derive of Delimiter:

Connection      = Delimiter.Connection  # connects things
Direction       = Delimiter.Direction   # implicates a direction
Bracket         = Delimiter.Bracket     # for { }, ( ), [ ] etc.
ModeChange      = Delimiter.ModeChange  # a special char that changes mode
Operator        = Delimiter.Operator    # an arithmetic operator
Quote           = Delimiter.Quote       # a quote, e.g. " or «
Separator       = Delimiter.Separator   # a separator, like \\ or | in LaTeX

Operator.Assignment                     # e.g. = to denote an assignment


# END_ACTIONS
del a, standardaction
