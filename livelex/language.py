# -*- coding: utf-8 -*-
#
# This file is part of the livelex Python module.
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


from livelex.lexicon import lexicon, default_action, default_target
from livelex.action import Subgroup, Text


class Language:
    """A Language represents a set of Lexicons comprising a specific language.
    
    A Language is never instantiated. The class itself serves as a namespace
    and can be inherited from.
    
    
    
    """
    re_flags = 0

    @lexicon
    def root(cls):
        yield r'bla', 'bla action'
        yield r'ble', 'ble action'
        yield r'(bl)(ub)', Subgroup('bl act', 'ub act')
        yield r'blo', 'blo action', cls.blo
    
    @lexicon
    def blo(cls):
        yield r'1', '1 in blo'
        yield r'4', '4 in blo, end', -1
        yield r'[0-9]', Text(lambda t: "has 3" if '3' in t else 'no 3')
        yield default_action, "unparsed"


        
