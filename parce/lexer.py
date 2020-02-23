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
The Lexer is responsible for parsing text using Lexicons.
"""


import collections

from .action import DynamicAction
from .lexicon import DynamicItem


Event = collections.namedtuple("Event", "target tokens")


class Lexer:
    """A Lexer is responsible for parsing text using Lexicons.

    ``lexicons`` is a list of one or more lexicon instances, the first one
    being the root lexicon. Lexicons can add lexicons to this list and pop
    lexicons off while parsing text. The first lexicon is never popped off.

    """
    def __init__(self, lexicons):
        """Lexicons should be an iterable of one or more lexicons."""
        self.lexicons = list(lexicons)

    def events(self, text, pos=0):
        """Get the events from parsing text from the specified position."""
        lexicons = self.lexicons
        temp_target = None
        circular = set()
        circular_pos = -1
        old_tokens = None
        while True:
            for pos, txt, match, action, target in lexicons[-1].parse(text, pos):
                if txt:
                    if isinstance(action, DynamicAction):
                        tokens = tuple(action.filter_actions(self, pos, txt, match))
                    else:
                        tokens = (pos, txt, action),
                    if tokens:
                        yield Event(temp_target or None, tokens)
                        temp_target = None
                    pos += len(txt)
                if target:
                    if target.pop:
                        # never pop off root
                        if -target.pop >= len(lexicons):
                            target.pop = 1 - len(lexicons)
                        del lexicons[target.pop:]
                    if target.push:
                        for i, t in enumerate(target.push):
                            if t is None:
                                target.push[i] = lexicons[-1]
                            else:
                                break
                        if not txt:
                            move = (len(lexicons), len(push))
                            if pos == circular_pos and move in circular:
                                if pos < len(text):
                                    pos += 1
                                circular.clear()
                            else:
                                circular.add(move)
                        else:
                            circular.clear()
                        lexicons.extend(target.push)
                    if temp_target:
                        temp_target += target
                    else:
                        temp_target = target
                    break   # continue with new lexicon
            else:
                break   # done

    def filter_actions(self, action, pos, text, match):
        """Handle filtering via DynamicAction instances."""
        if isinstance(action, DynamicItem):
            if isinstance(action, DynamicAction):
                yield from action.filter_actions(self, pos, text, match)
            else:
                for action in action.replace(text, match):
                    yield from self.filter_actions(action, pos, text, match)
        elif text:
            yield pos, text, action
