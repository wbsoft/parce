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


Doctype = Name.Type


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


class Xml(_XmlBase):
    """Parse XML."""
    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        yield r'<!--', Comment.Start, cls.comment
        yield r'<!\[CDATA\[', Data.Start, cls.cdata
        yield r'<!DOCTYPE\b', Doctype.Start, cls.doctype
        yield r'<\?', Delimiter.Preprocessed.Start, cls.pi
        yield r'(<\s*?/)\s*(\w+(?:[:.-]\w+)*)\s*(>)', bygroup(Delimiter, Name.Tag, Delimiter), -1
        yield r'(<)\s*(\w+(?:[:.-]\w+)*)(?:\s*((?:/\s*)?>))?', \
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
        yield r'\]\]>', Data.End, -1

    @lexicon
    def pi(cls):
        yield r'(\w+(?:[:.-]\w+)*)\s*?(=)(?=\s*?")', bygroup(Name.Attribute, Operator)
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield default_action, Preprocessed
        yield r'\?>', Delimiter.Preprocessed.End, -1

    @lexicon
    def doctype(cls):
        yield r'\w+', Text
        yield r'"', String, cls.dqstring
        yield r'\[', Doctype.Start, cls.internal_dtd
        yield r'>', Doctype.End, -1

    @lexicon
    def internal_dtd(cls):
        yield r'\]', Doctype.End, -1
        yield from Dtd.root

    @lexicon
    def attrs(cls):
        yield r'\w+([:.-]\w+)*', Name.Attribute
        yield r'=', Operator
        yield r'"', String.Double.Start, cls.dqstring
        yield r"'", String.Single.Start, cls.sqstring
        yield r'/\s*>', Delimiter, -1
        yield r'>', Delimiter, -1, cls.tag
        yield r'\s+', skip
        yield default_action, Invalid


class Dtd(_XmlBase):
    """Parse a DTD (Document Type Definition)."""
    @lexicon
    def root(cls):
        yield r'<!--', Comment.Start, cls.comment
        yield r'<!ENTITY\b', Name.Entity.Definition.Start, cls.entity
        yield default_action, Text  # TODO include more dtd language

    @lexicon
    def entity(cls):
        yield r'\w+', Name.Entity
        yield r'"', String, cls.dqstring
        yield r'>', Name.Entity.Definition.End, -1

