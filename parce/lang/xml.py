# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2019 by Wilbert Berendsen <info@wilbertberendsen.nl>
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


import re


from parce import *


CDATA = Literal.CDATA
DOCTYPE = Keyword.DOCTYPE
ENTITY = Keyword.ENTITY
PI = Comment.PI


class Xml(Language):
    """Parse XML."""
    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        yield r'<!--', Comment.Start, cls.comment
        yield r'<!\[CDATA\[', CDATA.Start, cls.cdata
        yield r'<!DOCTYPE\b', DOCTYPE.Start, cls.doctype
        yield r'<\?', PI.Start, cls.pi
        yield r'(<\s*?/)\s*(\w+(?:[:.-]\w+)*)\s*(>)', bygroup(Delimiter, Name.Tag, Delimiter), -1
        yield r'(<)\s*(\w+(?:[:.-]\w+)*)\s*(>)', bygroup(Delimiter, Name.Tag, Delimiter), cls.tag
        yield r'(<)\s*(\w+(?:[:.-]\w+)*)', bygroup(Delimiter, Name.Tag), cls.attrs
        yield r'&\S*?;', Escape.Entity
        yield default_action, Text

    @lexicon
    def tag(cls):
        yield from cls.root()

    @lexicon
    def comment(cls):
        yield default_action, Comment
        yield r'-->', Comment.End, -1

    @lexicon
    def cdata(cls):
        yield default_action, CDATA
        yield r'\]\]>', CDATA.End, -1

    @lexicon
    def pi(cls):
        yield r'(\w+(?:[:.-]\w+)*)\s*?(=)(?=\s*?")', bygroup(Name.Attribute, Operator)
        yield r'"', String, cls.dqstring
        yield default_action, PI
        yield r'\?>', PI.End, -1

    @lexicon
    def doctype(cls):
        yield r'\w+', Text
        yield r'"', String, cls.dqstring
        yield r'\[', DOCTYPE.Start, cls.internal_dtd
        yield r'>', DOCTYPE.End, -1

    @lexicon
    def internal_dtd(cls):
        yield r'<!ENTITY\b', ENTITY.Start, cls.entity
        yield r'<![^>]*>', DOCTYPE
        yield default_action, Text  # TODO include dtd language
        yield r'\]', DOCTYPE.End, -1

    @lexicon
    def entity(cls):
        yield r'\w+', Name.Entity
        yield r'"', String, cls.dqstring
        yield r'>', ENTITY.End, -1

    @lexicon
    def attrs(cls):
        yield r'\w+([:.-]\w+)*', Name.Attribute
        yield r'=', Operator
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r'/\s*>', Delimiter, -1
        yield r'>', Delimiter, -1, cls.tag
        yield r'\s+', skip
        yield default_action, Error

    @lexicon
    def dqstring(cls):
        yield r'&\S*?;', Escape.Entity
        yield default_action, String
        yield r'"', String, -1

    @lexicon
    def sqstring(cls):
        yield r'&\S*?;', Escape.Entity
        yield default_action, String
        yield r"'", String, -1

