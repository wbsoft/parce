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


"""A CSS parser.

| CSS3 Syntax:     https://www.w3.org/TR/css-syntax-3/
| Selector syntax: https://www.w3.org/TR/selectors-4/

We also use this parser inside parce, to be able to store default
highlighting formats in css files.

"""

__all__ = ('Css', 'CssIndent', 'CssIO')

import collections
import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import (
    Bracket, Comment, Delimiter, Escape, Invalid, Keyword, Literal, Name,
    Number, Operator, String)
from parce.rule import TEXT, bygroup, ifmember, ifeq, anyof
from parce.indent import Indent, INDENT, DEDENT
from parce import docio


RE_CSS_ESCAPE = r"\\(?:[0-9A-Fa-f]{1,6} ?|.)"
RE_CSS_NUMBER = (
    r"[+-]?"               # sign
    r"(?:\d*\.)?\d+"       # mantisse
    r"(?:[Ee][+-]\d+)?")   # exponent
# match either 8, 6, 4 or 3 hex digits
RE_HEX_COLOR = r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{5}|[0-9a-fA-F]{3}|[0-9a-fA-F]?)"


class Css(Language):
    @lexicon
    def root(cls):
        """Toplevel items: at-rules, comments, normal rules."""
        yield from cls.toplevel()

    @classmethod
    def toplevel(cls):
        """Find toplevel items: at-rules, comments, normal rules."""
        yield r"@", Keyword, cls.atrule, cls.atrule_keyword
        yield r"/\*", Comment, cls.comment
        yield r"\s+", skip  # skip whitespace
        yield default_target, cls.prelude

    @lexicon
    def prelude(cls):
        """The prelude of a rule: one or more selectors. On ``{`` parse the rule."""
        yield r"\{", Bracket, -1, cls.rule
        yield r"(?=</)", None, -1   # back off if HTML </style> tag follows...
        yield from cls.selectors()

    @classmethod
    def selectors(cls):
        """Yield selectors, used in prelude and selector_list."""
        yield r"\s+", skip              # skip whitespace
        yield r"[>+~]|\|\|", Operator   # combinators
        yield r",", Delimiter           # comma
        yield r"/\*", Comment, cls.comment
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield default_target, cls.selector

    @lexicon
    def selector(cls):
        """All types of CSS selectors"""
        yield r"\*", Keyword    # "any" element
        yield r"\|", Keyword    # css selector namespace prefix separator
        yield r"#", Name.Identifier.Definition, cls.id_selector
        yield r"\.(?!\d)", Keyword, cls.class_selector
        yield r"::", Keyword, cls.pseudo_element
        yield r":", Keyword, cls.pseudo_class
        yield r"\[", Delimiter, cls.attribute_selector, cls.attribute
        yield from anyof(cls.element_selector)
        yield default_target, -1

    @lexicon
    def selector_list(cls):
        """The list of selectors in :is(bla, bla), etc."""
        yield r"\)", Delimiter, -2  # also leave the pseudo_class context
        yield from cls.selectors()

    @lexicon
    def rule(cls):
        """Declarations of a qualified rule between { and }."""
        yield r"\}", Bracket, -1
        yield from cls.inline()

    @lexicon
    def inline(cls):
        """CSS in a rule block, or in an HTML style attribute."""
        yield from anyof(cls.property, cls.declaration, cls.property)
        yield from cls.common()

    @lexicon
    def declaration(cls):
        """A property: value;  declaration."""
        yield r":", Delimiter
        yield r";", Delimiter, -1
        yield r"!important\b", Keyword, -1
        yield from cls.common()
        yield r"\s+", skip  # stay here on whitespace only
        yield default_target, -1

    @classmethod
    def common(cls):
        """Find stuff that can be everywhere, string, comment, color, identifier"""
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
        yield r"\{", Bracket, cls.rule
        yield RE_CSS_NUMBER, Number, cls.unit
        yield RE_HEX_COLOR, Literal.Color
        yield r"(url)(\()", bygroup(Name, Delimiter), cls.url_function
        yield from anyof(cls.identifier)
        yield r"[:,;@%!]", Delimiter

    @lexicon
    def unit(cls):
        """Unit directly after a number, e.g. the ``px`` in 100px, also ``%``."""
        yield "%", Operator.Percent, -1
        yield from cls.identifier_common(Name.Unit)

    # ------------ selectors for identifiers in different roles --------------
    @classmethod
    def identifier_common(cls, action):
        """Yield an ident-token and give it the specified action."""
        yield RE_CSS_ESCAPE, Escape
        yield r"[\w-]+", action
        yield default_target, -1

    @lexicon(consume=True)
    def element_selector(cls):
        """A tag name used as selector."""
        yield from cls.identifier_common(Name.Tag)

    @lexicon(consume=True)
    def property(cls):
        """A CSS property."""
        from .css_words import CSS3_ALL_PROPERTIES
        action = ifmember(TEXT, CSS3_ALL_PROPERTIES, Name.Property.Definition, Name.Property)
        yield from cls.identifier_common(action)

    @lexicon
    def attribute(cls):
        """An attribute name."""
        yield from cls.identifier_common(Name.Attribute)

    @lexicon
    def id_selector(cls):
        """An ID selecter: ``#id``."""
        yield from cls.identifier_common(Name.Identifier.Definition)

    @lexicon
    def class_selector(cls):
        """A class selector: ``.classname``."""
        yield from cls.identifier_common(Name.Class)

    @lexicon
    def attribute_selector(cls):
        """Stuff between ``[`` and ``]``."""
        yield r"\]", Delimiter, -1
        yield r"[~|^$*]?=", Operator
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield from anyof(cls.ident_token)
        yield r'\s+', skip
        yield default_action, Invalid

    @lexicon
    def pseudo_class(cls):
        """Things like :first-child etc."""
        yield r"\(", Delimiter, cls.selector_list
        yield from cls.identifier_common(Name.Class.Pseudo)

    @lexicon
    def pseudo_element(cls):
        """Things like ::first-letter etc."""
        yield from cls.identifier_common(Name.Tag.Pseudo)

    # --------------------- @-rule ------------------------
    @lexicon
    def atrule(cls):
        """Contents following '@'."""
        yield r"\{", Bracket, cls.atrule_block
        yield from cls.atrule_common()

    @lexicon
    def atrule_nested(cls):
        """An atrule that has nested toplevel contents (@media, etc.)"""
        yield r"\{", Bracket, cls.atrule_nested_block
        yield from cls.atrule_common()

    @lexicon
    def atrule_keyword(cls):
        """The first identifier word in an @-rule."""
        yield r"(media|supports|document)\b", Keyword, -1, cls.atrule_nested
        yield from cls.identifier_common(Keyword)

    @lexicon
    def atrule_block(cls):
        """A ``{`` ``}`` block from an @-rule."""
        yield r"\}", Bracket, -2  # immediately leave the atrule context
        yield from cls.inline()

    @lexicon
    def atrule_nested_block(cls):
        """A ``{`` ``}`` block from @media, @document or @supports."""
        yield r"\}", Bracket, -2  # immediately leave the atrule_nested context
        yield from cls.toplevel()

    @classmethod
    def atrule_common(cls):
        """Find common stuff inside @-rules."""
        yield r";", Delimiter, -1
        yield r":", Keyword, cls.pseudo_class
        yield from cls.common()
        yield r'(?=</)', None, -1   # leave atrule when </style tag follows

    @lexicon(consume=True)
    def ident_token(cls):
        """An ident-token where quoted or unquoted text is allowed."""
        yield from cls.identifier_common(Name.Symbol)

    @lexicon(consume=True)
    def identifier(cls):
        """An ident-token that could be a color or a function()."""
        from .css_words import CSS3_NAMED_COLORS
        action = ifeq(TEXT, "transparent", Literal.Color,
            ifmember(TEXT, CSS3_NAMED_COLORS, Literal.Color, Name.Symbol))
        yield r"\(", Delimiter, cls.function
        yield from cls.identifier_common(action)

    @lexicon
    def function(cls):
        """Contents between identifier( ... )."""
        yield r"\)", Delimiter, -2  # go straight out of the identifier context
        yield r"\(", Delimiter, 1
        yield from cls.common()
        yield r"[*/+-]", Operator

    @lexicon
    def url_function(cls):
        """The ``url`` function: ``url(``...``)``."""
        yield r"\)", Delimiter, -1
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
        yield RE_CSS_ESCAPE, Escape
        yield default_action, Literal.Url

    @lexicon
    def dqstring(cls):
        """A double-quoted string."""
        yield r'"', String, -1
        yield from cls.string()

    @lexicon
    def sqstring(cls):
        """A single-quoted string."""
        yield r"'", String, -1
        yield from cls.string()

    @classmethod
    def string(cls):
        """Common rules for string."""
        yield default_action, String
        yield RE_CSS_ESCAPE, String.Escape
        yield r"\\\n", String.Escape
        yield r"\n", Invalid, -1

    @lexicon
    def comment(cls):
        """A comment."""
        yield r"\*/", Comment, -1
        yield from cls.comment_common()


class CssIndent(Indent):
    """Indenter for Css."""
    def events(self, block, tokens, prev_indents):
        for t in tokens:
            if t.action is Bracket:
                if t == "{":
                    yield INDENT
                elif t == "}":
                    yield DEDENT


class CssIO(docio.IO):
    """I/O handling for Css."""
    def default_encoding(self):
        """Return "utf-8" by default."""
        return "utf-8"

    def find_encoding(self, text):
        """Find encoding in Css."""
        m = re.search(r'@charset\s*"([\w_-]+)"', text)
        if m:
            return m.group(1)


