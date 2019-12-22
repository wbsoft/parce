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


import collections
import itertools


from .action import Action


Token = collections.namedtuple("Token", "pos text action target")
Target = collections.namedtuple("Target", "pop push")


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

        A token is a named four-tuple Token(pos, text, action, target):

        * pos: the position in the source string
        * text: the text of the token
        * action: the action that is associated with the token
        * target: the state change this token caused.

        Target can be a named two-tuple Target(pop, push), indicating how the
        state was changed by this token. The pop attribute is zero or negative;
        if negative it indicates the number of lexicons that were popped off
        the state. The push attribute is a tuple of zero or more lexicons that
        are to be added on top of the state.

        The target can also be None or False. If target is None, the matched
        text did not change the current lexicon. If target is False, the token
        is part of a series of tokens that originates from one single rule
        match. (This series ends with a token that has either a real target or
        None.)

        """

        if state is None:
            state = self.initial_state()
        lexicon = self.get_lexicon(state)
        state_change = None
        circular = set()
        change_token = None
        while True:
            for pos, txt, match, action, *target in lexicon.parse(text, pos):
                if change_token and match:
                    if change_token.target:
                        yield change_token # no need to yield if it does not change state
                    state_change = None
                    change_token = None
                    circular.clear()
                if target:
                    state_change = self.update_state(state, target, state_change)
                    lexicon = self.get_lexicon(state)
                    if not match:
                        # we have a state change caused by a default target
                        if lexicon in circular:
                            raise RuntimeError(
                                "Circular default target(s) detected: {}".format(circular))
                        if not state_change or len(state_change.push) + state_change.pop > 0:
                            circular.add(lexicon)
                        change_token = Token(pos, "", None, state_change)
                        break # continue with new lexicon
                tokens = list(self.filter_actions(action, pos, txt, match))
                if tokens:
                    for token in tokens[:-1]:
                        yield Token(*token, False)
                    for token in tokens[-1:]:
                        yield Token(*token, state_change)
                    state_change = None
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

    def update_state(self, state, target, old=False):
        """Modify the state according to target.

        Returns a two-tuple(pop, push), where pop is 0 or a negative number
        indicating how many lexicons were removed, and push the tuple of zero
        or more lexicons that were added. If you also specify the old state
        change, it is taken into account, as if the state was updated from
        before the previous state change. This is useful when a lexicon has a
        skipped action, while the state was changed, or a default target, and
        generates no tokens before switching.

        """
        # create the state change tuple (pop, push)
        pop, push = 0, []
        i = 0
        while i < len(target) and isinstance(target[i], int) and target[i] < 0:
            pop += target[i]
            i += 1
        pop = max(1 - len(state), pop)  # never delete the root lexicon
        for t in target[i:]:
            if isinstance(t, int) and t >= 0:
                push.extend(itertools.repeat(state[pop-1], t))
            else:
                push.append(t)
        push = tuple(push)
        # apply it to the state
        if pop:
            del state[pop:]
        if push:
            state.extend(push)
        # take into account the old state change if given
        if old:
            if -pop <= len(old.push):
                pop, push = old.pop, old.push[:pop] + push
            else:
                pop += old.pop + len(old.push)
        if pop or push:
            return Target(pop, push)

    def get_lexicon(self, state):
        """Return the topmost lexicon."""
        return state[-1]

    def filter_actions(self, action, pos, txt, match):
        """Handle filtering via Action instances."""
        if isinstance(action, Action):
            yield from action.filter_actions(self, pos, txt, match)
        else:
            yield pos, txt, action


def tree(tokens):
    """Experimental function that puts the tokens in a tree structure.

    The structure consists of nested lists; the first item of each list is the
    lexicon. The other items are the tokens that were generated by rules of
    that lexicon, or child lists.

    """
    root = current = []
    stack = [root]
    for t in tokens:
        if t.text:
            current.append(t)
        if t.target:
            if t.target.pop:
                for i in range(-1, t.target.pop - 1, -1):
                    if len(stack[i]) > 1:
                        stack[i-1].append(stack[i])
                del stack[t.target.pop:]
            for lexicon in t.target.push:
                stack.append([lexicon])
            current = stack[-1]
    # unwind if we were not back in the root lexicon
    for i in range(len(stack) - 1, 0, -1):
        if len(stack[i]) > 1:
            stack[i-1].append(stack[i])
    return root


