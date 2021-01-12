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
Parse XML.

"""

__all__ = ('Dtd', 'Xml')

import re

from parce import Language, lexicon, skip, default_action
from parce.action import (
    Bracket, Comment, Data, Delimiter, Escape, Invalid, Keyword, Name,
    Operator, String, Text, Whitespace)
from parce.rule import (
    MATCH, TEXT, bygroup, call, dselect, ifgroup, select, words)


# source: https://www.w3.org/TR/xml/#NT-NameStartChar
RE_XML_NAME_START_CHAR = (
    '_:A-Za-z\xC0-\xD6\xD8-\xF6'
    '\xF8-\u02FF\u0370-\u037D\u037F-\u1FFF'
    '\u200C\u200D\u2070-\u218F\u2C00-\u2FEF'
    '\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD'
    '\U00010000-\U000EFFFF'
)
RE_XML_NAME_CHAR = '-.0-9\xB7\u0300-\u036F\u203F-\u2040' + RE_XML_NAME_START_CHAR
RE_XML_NAME = _N_ = fr'[{RE_XML_NAME_START_CHAR}][{RE_XML_NAME_CHAR}]*'
RE_XML_NAME_TOKEN = _T_ = fr'[{RE_XML_NAME_CHAR}]*'

class _XmlBase(Language):
    """Common stuff between Xml and Dtd."""
    @lexicon
    def dqstring(cls):
        yield r'&\S*?;', String.Escape
        yield default_action, String.Double
        yield r'"', String.Double.End, -1

    @lexicon
    def sqstring(cls):
        yield r'&\S*?;', String.Escape
        yield default_action, String.Single
        yield r"'", String.Single.End, -1

    @lexicon
    def comment(cls):
        yield r'-->', Comment.End, -1
        yield r'--', Comment.Invalid
        yield from cls.comment_common()

    @classmethod
    def common_defs(cls):
        """Common stuff inside DOCTYPE or ENTITY declarations etc."""
        yield from cls.find_strings()
        yield fr'%{_N_};', Name.Entity.Escape

    @classmethod
    def find_strings(cls):
        yield r'"', String.Double.Start, cls.dqstring
        yield r"'", String.Single.Start, cls.sqstring

    @classmethod
    def find_comments(cls):
        yield r'<!--', Comment.Start, cls.comment


class Xml(_XmlBase):
    """Parse XML."""
    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        yield from cls.find_comments()
        yield r'(<!\[)(CDATA)(\[)', bygroup(Delimiter, Data.Definition, Delimiter), cls.cdata
        yield fr'(<!)(DOCTYPE)\b(?:\s*({_N_}))?', \
            bygroup(Delimiter, Keyword, Name.Tag.Definition), cls.doctype
        yield fr'(<\?)({_N_})?', bygroup(Bracket.Preprocessed.Start, Name.Tag.Preprocessed), \
            cls.processing_instruction
        yield fr'(<\s*?/)\s*({_N_})\s*(>)', bygroup(Delimiter, Name.Tag, Delimiter), -1
        yield fr'(<)\s*({_N_})(?:\s*((?:/\s*)?>))?', \
            bygroup(Delimiter, Name.Tag, Delimiter), dselect(MATCH[3], {
                None: cls.attrs,        # no ">" or "/>": go to attrs
                ">": cls.tag,           # a ">": go to tag
            })                          # by default ("/>"): stay in context
        yield r'&\S*?;', Escape
        yield default_action, select(call(str.isspace, TEXT), Text, Whitespace)

    @lexicon
    def tag(cls):
        yield from cls.root()

    @lexicon
    def cdata(cls):
        yield default_action, Data
        yield r'\]\]>', Delimiter, -1

    @lexicon
    def processing_instruction(cls):
        yield fr'({_N_})\s*?(=)(?=\s*?["\'])', bygroup(Name.Attribute, Operator)
        yield from cls.find_strings()
        yield r'&\S*?;', Escape
        yield r'\?>', Bracket.Preprocessed.End, -1
        yield default_action, Text.Preprocessed

    @lexicon
    def doctype(cls):
        yield words(("SYSTEM", "PUBLIC", "NDATA")), Keyword
        yield _N_, Name
        yield from cls.common_defs()
        yield r'\[', Bracket, cls.internal_dtd
        yield r'>', Delimiter, -1

    @lexicon
    def internal_dtd(cls):
        yield r'\]', Bracket, -1
        yield from Dtd.root

    @lexicon
    def attrs(cls):
        yield _N_, Name.Attribute
        yield r'=', Operator
        yield from cls.find_strings()
        yield r'/\s*>', Delimiter, -1
        yield r'>', Delimiter, -1, cls.tag
        yield r'\s+', skip
        yield default_action, Invalid


class Dtd(_XmlBase):
    """Parse a DTD (Document Type Definition)."""
    @lexicon
    def root(cls):
        yield from cls.find_comments()
        yield fr'(<!)(ENTITY)\b(?:\s*(%))?(?:\s*({_N_}))?', \
            bygroup(Delimiter, Keyword, Keyword, Name.Entity.Definition), cls.entity
        yield fr'(<!)(ELEMENT|ATTLIST|NOTATION)\b(?:\s*({_N_}))?', \
            bygroup(Delimiter, Keyword, Name.Element.Definition), \
            dselect(MATCH[2], {"ELEMENT": cls.element, "ATTLIST": cls.attlist}, cls.notation)
        yield fr'%{_N_};', Name.Entity.Escape
        yield default_action, select(call(str.isspace, TEXT), Text, skip)

    @lexicon
    def entity(cls):
        yield words(("SYSTEM", "PUBLIC", "NDATA")), Keyword
        yield _N_, Name.Entity
        yield from cls.common_defs()
        yield r'>', Delimiter, -1

    @lexicon
    def element(cls):
        yield r'\(', Bracket, cls.element_contents
        yield words(("ANY", "EMPTY")), Name.Keyword
        yield r'[,|?+*]', Operator
        yield from cls.common_defs()
        yield r'>', Delimiter, -1

    @lexicon
    def element_contents(cls):
        """Content definition inside a <!ELEMENT > declaration."""
        yield r'#PCDATA', Name.Builtin
        yield from cls.enumerate(r'[,|?+*]', Name.Element)

    @lexicon
    def attlist(cls):
        yield words(("#REQUIRED", "#IMPLIED", "#FIXED"), suffix=r'\b'), Name.Builtin
        yield words(('CDATA', 'ID', 'IDREF', 'IDREFS', 'ENTITY', 'ENTITIES',
            'NMTOKEN', 'NMTOKENS'), prefix=r'\b', suffix=r'\b'), Name.Type
        yield r'\b(NOTATION)\b(?:\s+(\())', bygroup(Name.Type, Bracket), \
            ifgroup(2, cls.attlist_notation)
        yield _N_, Name.Attribute.Definition
        yield r'\(', Bracket, cls.attlist_enumeration
        yield from cls.common_defs()
        yield r'>', Delimiter, -1

    @lexicon
    def attlist_enumeration(cls):
        yield from cls.enumerate(r'\|', Data)

    @lexicon
    def attlist_notation(cls):
        yield from cls.enumerate(r'\|', Name.Type)

    @lexicon
    def notation(cls):
        yield words(("SYSTEM", "PUBLIC")), Keyword
        yield from cls.common_defs()
        yield r'>', Delimiter, -1

    @classmethod
    def enumerate(cls, operators=r'\|', nametype=Name.Type):
        """Find names between ( ), and operators, string and parameter entities.

        ``operators`` is the regexp for the operators, ``nametype`` the action
        for the found names.

        """
        yield r'\(', Bracket, 1
        yield r'\)', Bracket, -1
        yield operators, Operator
        yield _T_, nametype
        yield from cls.common_defs()
