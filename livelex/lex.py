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


import itertools

import lexicon


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
                if match:
                    yield from self.match(pos, txt, action, match, state_change)
                    state_change = False
                    pos = match.end()
                elif txt:
                    yield from self.unparsed(pos, txt, action, state_change)
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

    def match(self, pos, text, action, match, state_change):
        """Yield one or more tokens from the match object.
        
        When there are multiple tokens yielded from one match object, it is not
        possible to resume parsing after a token that is not the last one.
        To signal that, the stage_change field is set to None for all except
        the last token.

        """
        if type(action) is lexicon.subgroup_actions:
            acts = enumerate(action, match.lastindex + 1)
            acts = [item for item in acts if item[1] is not None]
            for i, action in acts[:-1]:
                yield (match.start(i), match.group(i), action, None)
            for i, action in acts[-1:]:
                yield (match.start(i), match.group(i), action, state_change)
        else:
            yield (pos, text, action, state_change)

    def unparsed(self, pos, text, action, state_change):
        """Yield unparsed text."""
        yield (pos, text, action, state_change)


