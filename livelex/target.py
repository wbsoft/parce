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
The Target module defines Targets that depend on the text or match objects
from the lexer.

Instead of zero or more targets (which may be lexicons or integers), one
Target instance can be given as Target in a rule. Its target() method is then
called to return the desired tuple of targets.

"""


from livelex.lexicon import BoundLexicon


class Target:
    """Base class for Target objects.

    The possible targets are in the targets attribute.
    An index() function returns the index of the target to choose.

    If you specify a single integer or lexicon as a target, it is automatically
    converted to a single-item list.

    """
    def __init__(self, predicate, *targets):
        self.predicate = predicate
        self.targets = tuple([t] if isinstance(t, (int, BoundLexicon)) else t
            for t in targets)

    def index(self, text, match):
        raise NotImplementedError

    def target(self, text, match):
        return self.targets[self.index(text, match)]


class MatchTarget(Target):
    """A Target that calls the predicate with the match object.

    The predicate should return the index of the target to choose.

    """
    def index(self, text, match):
        return self.predicate(match)


class TextTarget(Target):
    """A Target that calls the predicate with the matched text.

    The predicate should return the index of the target to choose.

    """
    def index(self, text, match):
        return self.predicate(text)


