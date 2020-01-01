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


"""
The action module defines Action and its subclasses.

If an instance of Action is encountered in a rule, its filter_actions() method
is called to yield a (pos, text action) tuple. Normally the filter_actions()
method simply calls back the filter_actions() method of the lexer with the new
action, which could again be an Action instance.

Nesting is possible in most cases, only some actions require the match object
to be present; and such actions can't be used as default action, or inside
subgroup_actions.

An Action object always holds all actions it is able to return in the actions
attribute. This is done so that it is possible to know all actions a Language
can generate beforehand, and e.g. translate all the actions in a Language to
other objects, which could even be methods or functions.

"""


class Action:
    """Base class for Action objects.

    All actions an Action object could yield are in the actions attribute.

    """
    def __init__(self, *actions):
        self.actions = actions

    def filter_actions(self, lexer, pos, text, match):
        raise NotImplementedError


class Subgroup(Action):
    """Yield actions from subgroups in a match.

    There should be the same number of subgroups in the regular expression as
    there are action attributes given to __init__().

    """
    def filter_actions(self, lexer, pos, text, match):
        for i, action in enumerate(self.actions, match.lastindex + 1):
            yield from lexer.filter_actions(action, match.start(i), match.group(i), None)


class Match(Action):
    """Expects a function as argument that is called with the match object.

    The function should return the index indicating the action to return.
    The function may also return True or False, which are regarded as 1 or 0,
    respectively.

    """
    def __init__(self, predicate, *actions):
        self.predicate = predicate
        super().__init__(*actions)

    def filter_actions(self, lexer, pos, text, match):
        index = self.predicate(match)
        action = self.actions[index]
        yield from lexer.filter_actions(action, pos, text, match)


class Text(Action):
    """Expects a function as argument that is called with the matched text.

    The function should return the index indicating the action to return.
    The function may also return True or False, which are regarded as 1 or 0,
    respectively.

    """
    def __init__(self, predicate, *actions):
        self.predicate = predicate
        super().__init__(*actions)

    def filter_actions(self, lexer, pos, text, match):
        index = self.predicate(text)
        action = self.actions[index]
        yield from lexer.filter_actions(action, pos, text, None)


class _SkipAction(Action):
    """An Action that yields nothing."""
    def filter_actions(self, lexer, pos, text, match):
        yield from ()


# used to suppress a token
skip = _SkipAction()
