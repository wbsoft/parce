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
            for match, target in lexicon.parse(text, pos):
                if lexicon.default_action and match.start() > pos:
                    yield (pos, lexicon.default_action, text[pos:m.start()], state_change)
                    state_change = False
                pos = match.end()
                if target:
                    lexicon = self.get_lexicon(state, target)
                    yield from self.match(match, True)
                    state_change = False
                    break
                else:
                    yield from self.match(match, state_change)
                    state_change = False
            else:
                # run out, has the lexicon a default lexicon target?
                if lexicon.default_target:
                    lexicon = self.get_lexicon(state, lexicon.default_target)
                    state_change = True
                else:
                    break
        if lexicon.default_action and pos < len(text):
            yield (pos, lexicon.default_action, text[pos:], state_change)
        
    def get_lexicon(self, state, target):
        """Modify the state according to target and return the topmost lexicon."""

    def match(self, match, state_change=False):
        """Yield one or more tokens from the match object."""
        pos = match.start()
        action = match.lastgroup
        value = match.group()
        yield (pos, action, value, state_change)

