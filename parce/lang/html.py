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
Parse HTML.

Recognizes CSS in style tags and attributes.

"""

import re


from parce import *
from parce.lang.xml import Xml
from parce.lang.css import Css


class Html(Xml):
    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        yield r'(<)(style)\b(>|/\s*>)?', bygroup(Delimiter, Name.Tag, Delimiter), \
            mapgroup(3, {
                '>': cls.css_style_tag,
                None: cls.attrs("css"),
            })  # by default a close tag, stay in the context.
        yield from super().root

    @lexicon
    def attrs(cls):
        """Reimplemented to recognize style attributes and switch to style tag."""
        yield r'(style)\s*(=)\s*(")', bygroup(Name.Attribute, Operator, String), \
            cls.css_style_attribute
        predicate = lambda arg: arg == "css"
        yield r'>', Delimiter, -1, byarg(predicate, cls.tag, cls.css_style_tag)
        yield from super().attrs

    @lexicon
    def css_style_tag(cls):
        """Stuff between <style> and </style>."""
        yield r'(<\s*/)\s*(style)\s*(>)', bygroup(Delimiter, Name.Tag, Delimiter), -1
        yield from Css.root

    @lexicon
    def css_style_attribute(cls):
        """Stuff inside style=" ... " attrbute."""
        yield r'"', String, -1
        yield from Css.inline


