# -*- coding: utf-8 -*-
#
# This file is part of the livelex Python package.
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


"""
Parser for LilyPond syntax.
"""


import re


from livelex import *


class LilyPond(Language):

    @lexicon
    def root(cls):
        yield from cls.common()


    @classmethod
    def common(cls):
        yield r'%\{', Comment, cls.multiline_comment
        yield r'%', Comment, cls.singleline_comment
        yield r'"', String, cls.string
        yield r'#', Delimiter.SchemeStart, cls.scheme

    
    # -------------- Scheme ---------------------
    @lexicon
    def scheme(cls):
        from .scheme import Scheme
        yield from Scheme.one_arg()
        yield default_target, -1
        
    # -------------- String ---------------------
    @lexicon
    def string(cls):
        yield r'"', String, -1
        yield from cls.string_common()

    @classmethod
    def string_common(cls):
        yield r'\\[\\"]', String.Escape
        yield default_action, String

    # -------------- Comment ---------------------
    @lexicon
    def multiline_comment(cls):
        yield r'%}', Comment, -1
        yield from cls.comment_common()

    @lexicon(re_flags=re.MULTILINE)
    def singleline_comment(cls):
        yield from cls.comment_common()
        yield r'$', Comment, -1

    @classmethod
    def comment_common(cls):
        yield default_action, Comment


