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

import re


from parce import *

RE_XML_NAME = _N_ = r'[^\W\d]\w*'
RE_XML_ELEMENT_NAME = _T_ = fr'(?:{_N_}:)?{_N_}\b'
RE_XML_ATTRIBUTE_NAME = _A_ = fr'(?:{_N_}:)?{_N_}\b'


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
        yield from cls.comment_common()

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
        yield r'<\?', Delimiter.Preprocessed.Start, cls.pi
        yield fr'(<\s*?/)\s*({_T_})\s*(>)', bygroup(Delimiter, Name.Tag, Delimiter), -1
        yield fr'(<)\s*({_T_})(?:\s*((?:/\s*)?>))?', \
            bygroup(Delimiter, Name.Tag, Delimiter), mapgroup(3, {
                None: cls.attrs,        # no ">" or "/>": go to attrs
                ">": cls.tag,           # a ">": go to tag
            })                          # by default ("/>"): stay in context
        yield r'&\S*?;', Escape
        yield default_action, bytext(str.isspace, Text, Whitespace)

    @lexicon
    def tag(cls):
        yield from cls.root()

    @lexicon
    def cdata(cls):
        yield default_action, Data
        yield r'\]\]>', Delimiter, -1

    @lexicon
    def pi(cls):
        yield fr'({_A_})\s*?(=)(?=\s*?")', bygroup(Name.Attribute, Operator)
        yield from cls.find_strings()
        yield default_action, Preprocessed
        yield r'\?>', Delimiter.Preprocessed.End, -1

    @lexicon
    def doctype(cls):
        yield words(("SYSTEM", "PUBLIC", "NDATA")), Keyword
        yield _N_, Name
        yield from cls.find_strings()
        yield r'\[', Bracket, cls.internal_dtd
        yield fr'%{_N_};', Name.Entity.Escape
        yield r'>', Delimiter, -1

    @lexicon
    def internal_dtd(cls):
        yield r'\]', Bracket, -1
        yield from Dtd.root

    @lexicon
    def attrs(cls):
        yield _A_, Name.Attribute
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
        yield fr'(<!)(ELEMENT)\b(?:\s*({_N_}))?', \
            bygroup(Delimiter, Keyword, Name.Element.Definition), cls.element
        yield fr'(<!)(ATTLIST)\b(?:\s*({_N_}))?', \
            bygroup(Delimiter, Keyword, Name.Element.Definition), cls.attlist
        yield fr'%{_N_};', Name.Entity.Escape
        yield default_action, bytext(str.isspace, Text, skip)

    @lexicon
    def entity(cls):
        yield words(("SYSTEM", "PUBLIC", "NDATA")), Keyword
        yield _N_, Name.Entity
        yield from cls.find_strings()
        yield fr'%{_N_};', Name.Entity.Escape
        yield r'>', Delimiter, -1

    @lexicon
    def element(cls):
        yield from cls.find_strings()
        yield fr'%{_N_};', Name.Entity.Escape
        yield r'>', Delimiter, -1

    @lexicon
    def attlist(cls):
        yield from cls.find_strings()
        yield fr'%{_N_};', Name.Entity.Escape
        yield r'>', Delimiter, -1

