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


"""
The action module defines Action and its subclasses.

If an instance of Action is encountered in a rule, it is called to return the 
desired action. Nesting is possible in most cases, only some actions require 
the match object to be present; and such actions can't be used as default
action, or inside subgroup_actions.

"""


# used to suppress a token
skip = object()


class Action:
    def __init__(self, *args):
        self.args = args
    
    def match(self, lexer, pos, text, match, state_change):
        raise NotImplementedError

    def text(self, lexer, pos, text, state_change):
        raise NotImplementedError


class MatchAction(Action):
    """An Action that can't be used for text, but requires a match object."""
    def text(self, lexer, pos, text, state_change):
        raise RuntimeError("Can't use this action without match object.")


class Subgroup(MatchAction):
    """Yield actions from subgroups in a match.

    When there are multiple tokens yielded from one match object, it is not
    possible to resume parsing after a token that is not the last one.
    To signal that, the stage_change field is set to None for all except
    the last token.

    """
    def match(self, lexer, pos, text, match, state_change):
        acts = enumerate(self.args, match.lastindex + 1)
        acts = [item for item in acts if item[1] is not skip]
        for i, action in acts[:-1]:
            yield from lexer.text(match.start(i), match.group(i), action, None)
        for i, action in acts[-1:]:
            yield from lexer.text(match.start(i), match.group(i), action, state_change)
        

class Match(MatchAction):
    """Expects a function as argument that is called with the match object.
    
    The function should return the desired action.
    
    """
    def __init__(self, func):
        self.func = func

    def match(self, lexer, pos, text, match, state_change):
        action = self.func(match)
        yield from lexer.match(pos, text, action, match, state_change)


class Text(Action):
    """Expects a function as argument that is called with the matched text.
    
    The function should return the desired action.
    
    """
    def __init__(self, func):
        self.func = func

    def match(self, lexer, pos, text, match, state_change):
        action = self.func(text)
        yield from lexer.match(pos, text, action, match, state_change)

    def text(self, lexer, pos, text, state_change):
        action = self.func(text)
        yield from lexer.text(pos, text, action, state_change)


