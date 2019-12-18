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


import itertools


from livelex.action import Action


class Lexer:
        
    def __init__(self, root_lexicon):
        self.root_lexicon = root_lexicon
    
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
            for pos, txt, match, action, *target in lexicon.parse(text, pos):
                if target:
                    state_change = True
                    lexicon = self.get_lexicon(state, target)
                if txt:
                    tokens = list(self.filter_actions(action, pos, txt, match))
                    if tokens:
                        for token in tokens[:-1]:
                            yield (*token, None)
                        for token in tokens[-1:]:
                            yield (*token, state_change)
                        state_change = False
                    pos += len(txt)
                if target:
                    break # continue with new lexicon
            else:
                break
        
    def get_lexicon(self, state, target=()):
        """Modify the state according to target and return the topmost lexicon."""
        for t in target:
            if type(t) is int:
                if t < 0:
                    del state[t:]
                elif t > 0:
                    state.extend(itertools.repeat(state[-1], t))
            else:
                state.append(t)
        if not state:
            state.append(self.root_lexicon)
        return state[-1]

    def filter_actions(self, action, pos, txt, match):
        """Handle filtering via Action instances."""
        if isinstance(action, Action):
            yield from action.filter_actions(self, pos, txt, match)
        else:
            yield pos, txt, action


