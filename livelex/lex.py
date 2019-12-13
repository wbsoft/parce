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




class Lexer:
    
    
    
    
    def lex(self, text, state=None, pos=0):
        """Yield tokens for the text.
        
        state is a list of context instances or names(?), the last one is the current
        context.
        
        """
    
        if state is None:
            state = []
        lexicon = self.get_lexicon(state)
        state_change = False
        while True:
            for pos, text, match, action, *target in lexicon.parse(text, pos):
                if target:
                    state_change = True
                    lexicon = self.get_lexicon(state, target)
                if match:
                    yield from self.match(pos, text, action, match, state_change)
                    state_change = False
                elif text:
                    yield from self.unparsed(pos, text, action, state_change)
                    state_change = False
                if target:
                    break # continue with new lexicon
            else:
                break
        
    def get_lexicon(self, state, target):
        """Modify the state according to target and return the topmost lexicon."""

    def match(self, pos, text, action, match, state_change):
        """Yield one or more tokens from the match object."""
        yield (pos, text, action, state_change)

    def unparsed(self, pos, text, action, state_change):
        """Yield unparsed text."""
        yield (pos, text, action, state_change)


