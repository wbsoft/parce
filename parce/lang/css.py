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

CSS3 Syntax: https://www.w3.org/TR/css-syntax-3/
Selector syntax: https://www.w3.org/TR/selectors-4/

We want also to use this parser inside parce, to be able to store default
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
RE_HEX_COLOR = r"#[0-9a-fA-F]+"


# used names
Name.Tag
Name.Attribute
Name.Class
Name.Identifier
Name.Property


class Css(Language):
    @lexicon
    def root(cls):
        yield from cls.toplevel()

    @classmethod
    def toplevel(cls):
        yield r"@", Keyword, cls.atrule, cls.atrule_keyword
        yield from cls.selectors()
        yield from cls.common()

    @classmethod
    def selectors(cls):
        yield r"\*", Keyword    # "any" element
        yield r"\|", Keyword    # css selector namespace prefix separator
        yield r"#", Keyword, cls.id_selector
        yield r"\.(?!\d)", Keyword, cls.class_selector
        yield r"::", Keyword, cls.pseudo_element
        yield r":", Keyword, cls.pseudo_class
        yield r"\[", Keyword, cls.attribute_selector, cls.attribute
        yield r"[>+~]|\|\|", Operator   # combinators
        yield RE_CSS_IDENTIFIER_LA, Name, cls.selector

    @lexicon
    def selector_list(cls):
        """The list of selectors in :is(bla bla), etc."""
        yield r"\)", Delimiter, -1
        yield from cls.selectors()
        yield from cls.common()

    @classmethod
    def common(cls):
        """Stuff that can be everywhere."""
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
        yield r"\{", Delimiter, cls.rule
        yield RE_CSS_NUMBER, Number
        yield RE_HEX_COLOR, Literal.Color
        yield r"(url)(\()", bygroup(Name, Delimiter), cls.url_function
        # an ident-token is found using a lookahead pattern, the whole ident-
        # token is in the identifier context
        yield RE_CSS_IDENTIFIER_LA, Name, cls.identifier
        yield r"[:,;@%!]", Delimiter

    @lexicon
    def rule(cls):
        """Declarations of a qualified rule between { and }."""
        yield r"\}", Delimiter, -1
        yield from cls.inline()

    @lexicon
    def inline(cls):
        """CSS that would be in a rule block, but also in a HTML style attribute."""
        yield r"@", Keyword, cls.atrule
        yield RE_CSS_IDENTIFIER_LA, Name, cls.declaration, cls.property
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

    # ------------ selectors for identifiers in different roles --------------
    @classmethod
    def identifier_common(cls):
        yield RE_CSS_ESCAPE, Escape
        yield default_target, -1

    @lexicon
    def selector(cls):
        """A tag name used as selector."""
        yield r"[\w-]+", Name.Tag
        yield from cls.identifier_common()

    @lexicon
    def property(cls):
        """A CSS property."""
        yield r"[\w-]+", Name.Property
        yield from cls.identifier_common()

    @lexicon
    def attribute(cls):
        """An attribute name."""
        yield r"[\w-]+", Name.Attribute
        yield from cls.identifier_common()

    @lexicon
    def id_selector(cls):
        """#id"""
        yield r"[\w-]+", Name.Identifier
        yield from cls.identifier_common()

    @lexicon
    def class_selector(cls):
        """.classname"""
        yield r"[\w-]+", Name.Class
        yield from cls.identifier_common()

    @lexicon
    def attribute_selector(cls):
        """Stuff between [ and ]."""
        yield r"\]", Keyword, -1
        yield r"[~|^*&]?=", Operator
        yield from cls.common()

    @lexicon
    def pseudo_class(cls):
        """Things like :first-child etc."""
        yield RE_CSS_ESCAPE, Escape
        yield r"[\w-]+", Name
        yield r"\(", Delimiter, -1, cls.selector_list
        yield default_target, -1

    @lexicon
    def pseudo_element(cls):
        """Things like ::first-letter etc."""
        yield RE_CSS_ESCAPE, Escape
        yield r"[\w-]+", Name
        yield default_target, -1

    @lexicon
    def atrule(cls):
        """Contents following '@'."""
        yield r";", Delimiter, -1
        yield r"\{", Delimiter, cls.block
        yield from cls.common()

    @lexicon
    def atrule_keyword(cls):
        """The first identifier word in an @-rule."""
        yield r"[\w-]+", Keyword
        yield from cls.identifier_common()

    @lexicon
    def block(cls):
        """a { } block from an @-rule."""
        yield r"\}", Delimiter, -2  # immediately leave the atrule context
        yield from cls.toplevel()

    @lexicon
    def identifier(cls):
        """An ident-token is always just a context, it contains all parts."""
        yield RE_CSS_ESCAPE, Escape
        yield r"[\w-]+", Name
        yield r"\(", Delimiter, -1, cls.function
        yield default_target, -1

    @lexicon
    def function(cls):
        """Contents between identifier( ... )."""
        yield r"\)", Delimiter, -1
        yield from cls.common()

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
        yield r"\n", Error, -1

    @lexicon
    def comment(cls):
        """A comment."""
        yield r"\*/", Comment, -1
        yield default_action, Comment



def unescape(text):
    """Return the unescaped character, text is the contents of an Escape token."""
    value = text[1:]
    if value == '\n':
        return ''
    try:
        codepoint = int(value, 16)
    except ValueError:
        return value
    return chr(codepoint)


