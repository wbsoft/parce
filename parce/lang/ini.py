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
INI file format parsers.

"""

import re


from parce import *


class Ini(Language):
    @lexicon
    def root(cls):
        yield r'\[', Delimiter.Section, cls.section
        yield r';', Comment, cls.comment
        yield r'=', Operator.Assignment, cls.value
        yield default_target, cls.key

    @lexicon
    def section(cls):
        yield r'\]', Delimiter.Section, -1
        yield default_action, Name.Namespace.Section

    @lexicon
    def key(cls):
        yield from cls.values()

    @lexicon
    def value(cls):
        yield from cls.values()

    @lexicon
    def values(cls):
        yield r"""\\[\n\\'"0abtrn;#=:]""", Escape
        yield r"\\x[0-9a-fA-F]{4}", Escape
        yield r"[^\[\\\n;=#:]+", Name
        yield default_target, -1

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield r'$', Comment, -1
        yield from cls.comment_common()
        yield default_action, Comment


