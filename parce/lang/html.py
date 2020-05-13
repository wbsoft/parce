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

__all__ = ('Html', 'XHtml')

import re

from parce import Language, lexicon, default_target
from parce.action import Delimiter, Name, Operator, String
from parce.rule import ARG, MATCH, bygroup, dselect, using, words

from parce.lang.xml import Xml
from parce.lang.css import Css
from parce.lang.javascript import JavaScript


# elements that do not start a new tag context
HTML_VOID_ELEMENTS = (
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr", "command", "keygen", "menuitem",
)


class XHtml(Xml):
    """XHtml, is also valid Xml."""
    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        yield r'(<)(style|script)\b(>|/\s*>)?', bygroup(Delimiter, Name.Tag, Delimiter), \
            dselect(MATCH(2), {
                "style": dselect(MATCH(3), {'>': cls.css_style_tag, None: cls.attrs("css")}),
                "script": dselect(MATCH(3), {'>': cls.script_tag, None: cls.attrs("js")}),
            })  # by default a close tag, stay in the context.
        yield from super().root

    @lexicon
    def attrs(cls):
        """Reimplemented to recognize style attributes and switch to style tag."""
        yield r'(style)\s*(=)\s*(")', bygroup(Name.Attribute, Operator, String), \
            cls.css_style_attribute
        yield r'>', Delimiter, -1, dselect(ARG, {
            "js": cls.script_tag,
            "css": cls.css_style_tag,
            None: cls.tag})
        yield from super().attrs

    @lexicon
    def script_tag(cls):
        """Stuff between <script> and </script>."""
        yield r'(<\s*/)\s*(script)\s*(>)', bygroup(Delimiter, Name.Tag, Delimiter), -1
        yield from JavaScript.root

    @lexicon
    def css_style_tag(cls):
        """Stuff between <style> and </style>."""
        yield r'(<\s*/)\s*(style)\s*(>)', bygroup(Delimiter, Name.Tag, Delimiter), -1
        yield from Css.root

    @lexicon
    def css_style_attribute(cls):
        """Stuff inside style=" ... " attrbute."""
        yield r'([^"]*)(")', bygroup(using(Css.inline), String), -1
        yield default_target, -1


class Html(XHtml):
    """Html, allows certain tags (void elements) not to be closed."""
    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        yield words(HTML_VOID_ELEMENTS, prefix=r'(<\s*?/)\s*((?:\w+:)?', suffix=r')\s*(>)'), \
            bygroup(Delimiter, Name.Tag, Delimiter) # don't leave no-closing tags
        yield words(HTML_VOID_ELEMENTS, prefix=r'(<)\s*(', suffix=r')(?:\s*((?:/\s*)?>))?'), \
            bygroup(Delimiter, Name.Tag, Delimiter), dselect(MATCH(3), {
                None: cls.attrs("noclose"), # no ">" or "/>": go to attrs/noclose
            })                          # by default ("/>"): stay in context
        yield from super().root

