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

RE_CSS_ESCAPE = r"\\(?:[0-9A-Fa-f]{1,6} ?|\n|.)"
RE_CSS_NUMBER = (
    r"[+-]?"            # sign
    r"(?:\d*\.)?\d+"     # mantisse
    r"([Ee][+-]\d+)?")  # exponent


class Css(Language):
    
    @classmethod
    def common(cls):
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
    
    @lexicon
    def dqstring(cls):
        yield r'"', String, -1
        yield from cls.string()
    
    @lexicon
    def sqstring(cls):
        yield r"'", String, -1
        yield from cls.string()
    
    @classmethod
    def string(cls):
        yield default_action, String
        yield RE_CSS_ESCAPE, String.Escape
        yield r"\n", Error, -1

    @lexicon
    def comment(cls):
        yield r"\*/", Comment, -1
        yield default_action, Comment




