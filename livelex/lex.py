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


from .action import Action


class Lexer:
    """A Lexer is used to parse a text.

    A root lexicon is needed to start parsing; rules in the root lexicon
    can move to other lexicons or leave the current lexicon.

    You can specify the root lexicon on instantiation, but you may also just
    call tokens() with a state. A state is simply a Python list of lexicons,
    the last list item being the current lexicon, and the first item is
    regarded as the root lexicon, i.e. the first lexicon will never be removed.

    If you don't specify a root lexicon, you must specify a state when calling
    tokens().

    """

    def __init__(self, root_lexicon=None):
        self.root_lexicon = root_lexicon

    def tokens(self, text, state=None, pos=0):
        """Yield tokens for the text.

        state is a list of lexicons, the last one is the current
        lexicon.

        A token is a four-tuple(pos, text, action, state_change):

        * pos: the position in the source string
        * text: the text of the token (always a string with length > 0)
        * action: the action that is associated with the token
        * state_change: whether this token caused a state change.

        If state_change is False, the matched text did not change the current
        lexicon. If state_change is None, the token is part of a series of
        tokens that originates from one single rule match. (This series ends
        with a token that has either a state_change or True or False.)

        If state_change is True, the state (i.e. the current lexicon) has
        changed.

        """

        if state is None:
            state = self.initial_state()
        lexicon = self.get_lexicon(state)
        state_change = False
        while True:
            for pos, txt, match, action, *target in lexicon.parse(text, pos):
                if target:
                    self.update_state(state, target)
                    state_change = True
                    lexicon = self.get_lexicon(state)
                if txt:
                    tokens = list(self.filter_actions(action, pos, txt, match))
                    if tokens:
                        for token in tokens[:-1]:
                            yield (*token, None)
                        for token in tokens[-1:]:
                            yield (*token, state_change)
                        state_change = False
                if target:
                    pos += len(txt)
                    break # continue with new lexicon
            else:
                break

    def initial_state(self):
        """Return a state list with the root lexicon."""
        if self.root_lexicon:
            return [self.root_lexicon]
        raise RuntimeError("Lexer: no root lexicon specified and tokens() called without state")

    def update_state(self, state, target):
        """Modify the state according to target."""
        for t in target:
            if type(t) is int:
                if t < 0:
                    t = max(1, len(state) + t)  # never delete the root lexicon
                    del state[t:]
                elif t > 0:
                    state.extend(itertools.repeat(state[-1], t))
            else:
                state.append(t)

    def get_lexicon(self, state):
        """Return the topmost lexicon."""
        return state[-1]

    def filter_actions(self, action, pos, txt, match):
        """Handle filtering via Action instances."""
        if isinstance(action, Action):
            yield from action.filter_actions(self, pos, txt, match)
        else:
            yield pos, txt, action


