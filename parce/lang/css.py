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

import re

from parce import *


RE_CSS_ESCAPE = r"\\(?:[0-9A-Fa-f]{1,6} ?|.)"
RE_CSS_NUMBER = (
    r"[+-]?"               # sign
    r"(?:\d*\.)?\d+"       # mantisse
    r"(?:[Ee][+-]\d+)?")   # exponent
RE_CSS_IDENTIFIER_LA = r"(?=-?(?:[^\W\d]|\\[0-9A-Fa-f])|--)" # lookahead
RE_CSS_IDENTIFIER = (
    r"(?:-?(?:[^\W\d]+|" + RE_CSS_ESCAPE + r")|--)"
    r"(?:[\w-]+|" + RE_CSS_ESCAPE + r")*")
RE_CSS_AT_KEYWORD = r"@" + RE_CSS_IDENTIFIER
# match either 8, 6, 4 or 3 hex digits
RE_HEX_COLOR = r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{5}|[0-9a-fA-F]{3}|[0-9a-fA-F]?)"


class Css(Language):
    @lexicon
    def root(cls):
        yield from cls.toplevel()

    @classmethod
    def toplevel(cls):
        yield r"@", Keyword, cls.atrule, cls.atrule_keyword
        yield r"/\*", Comment, cls.comment
        yield r"\s+", skip  # skip whitespace
        yield default_target, cls.prelude

    @lexicon
    def prelude(cls):
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
        yield r"\*", Keyword    # "any" element
        yield r"\|", Keyword    # css selector namespace prefix separator
        yield r"#", Name.Identifier.Definition, cls.id_selector
        yield r"\.(?!\d)", Keyword, cls.class_selector
        yield r"::", Keyword, cls.pseudo_element
        yield r":", Keyword, cls.pseudo_class
        yield r"\[", Delimiter, cls.attribute_selector, cls.attribute
        yield RE_CSS_IDENTIFIER_LA, None, cls.element_selector
        yield default_target, -1

    @lexicon
    def selector_list(cls):
        """The list of selectors in :is(bla, bla), etc."""
        yield r"\)", Delimiter, -1
        yield from cls.selectors()

    @lexicon
    def rule(cls):
        """Declarations of a qualified rule between { and }."""
        yield r"\}", Bracket, -1
        yield from cls.inline()

    @lexicon
    def inline(cls):
        """CSS that would be in a rule block, but also in a HTML style attribute."""
        yield RE_CSS_IDENTIFIER_LA, None, cls.declaration, cls.property
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
        """Stuff that can be everywhere."""
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
        yield r"\{", Bracket, cls.rule
        yield RE_CSS_NUMBER, Number, cls.unit
        yield RE_HEX_COLOR, Literal.Color
        yield r"(url)(\()", bygroup(Name, Delimiter), cls.url_function
        # an ident-token is found using a lookahead pattern, the whole ident-
        # token is in the identifier context
        yield RE_CSS_IDENTIFIER_LA, None, cls.identifier
        yield r"[:,;@%!]", Delimiter

    @lexicon
    def unit(cls):
        """Unit directly after a nunber, e.g. 100px, also %."""
        yield "%", Operator.Percent
        yield from cls.identifier_common(Name.Unit)

    # ------------ selectors for identifiers in different roles --------------
    @classmethod
    def identifier_common(cls, action):
        """Yield an ident-token and give it the specified action."""
        yield RE_CSS_ESCAPE, Escape
        yield r"[\w-]+", action
        yield default_target, -1

    @lexicon
    def element_selector(cls):
        """A tag name used as selector."""
        yield from cls.identifier_common(Name.Tag)

    @lexicon
    def property(cls):
        """A CSS property."""
        from .css_words import CSS3_ALL_PROPERTIES
        yield from cls.identifier_common(
            ifmember(CSS3_ALL_PROPERTIES, Name.Property.Definition, Name.Property))

    @lexicon
    def attribute(cls):
        """An attribute name."""
        yield from cls.identifier_common(Name.Attribute)

    @lexicon
    def id_selector(cls):
        """#id"""
        yield from cls.identifier_common(Name.Identifier.Definition)

    @lexicon
    def class_selector(cls):
        """.classname"""
        yield from cls.identifier_common(Name.Class)

    @lexicon
    def attribute_selector(cls):
        """Stuff between [ and ]."""
        yield r"\]", Delimiter, -1
        yield r"[~|^*&]?=", Operator
        yield from cls.common()

    @lexicon
    def pseudo_class(cls):
        """Things like :first-child etc."""
        yield r"\(", Delimiter, -1, cls.selector_list
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
        """a { } block from an @-rule."""
        yield r"\}", Bracket, -2  # immediately leave the atrule context
        yield from cls.inline()

    @lexicon
    def atrule_nested_block(cls):
        """a { } block from @media, @document or @supports."""
        yield r"\}", Bracket, -2  # immediately leave the atrule_nested context
        yield from cls.toplevel()

    @classmethod
    def atrule_common(cls):
        """Common stuff inside @-rules."""
        yield r";", Delimiter, -1
        yield r":", Keyword, cls.pseudo_class
        yield from cls.common()
        yield r'(?=</)', None, -1   # leave atrule when </style tag follows

    @lexicon
    def identifier(cls):
        """An ident-token is always just a context, it contains all parts."""
        from .css_words import CSS3_NAMED_COLORS
        yield r"\(", Delimiter, -1, cls.function
        yield RE_CSS_ESCAPE, Escape
        yield r"[\w-]+", ifmember(CSS3_NAMED_COLORS, Literal.Color, Name.Symbol)
        yield default_target, -1

    @lexicon
    def function(cls):
        """Contents between identifier( ... )."""
        yield r"\)", Delimiter, -1
        yield r"\(", Delimiter, 1
        yield from cls.common()
        yield r"[*/+-]", Operator

    @lexicon
    def url_function(cls):
        """url(....)"""
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

