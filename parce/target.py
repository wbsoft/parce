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
A Target describes where to go.

In a lexicon rule, you can specify destinations using integers or lexicons.
A Target generalizes this in two values/attributes: ``pop`` and ``push``.

``pop`` is zero or a negative integer, determining how many lexicons to
pop off the current state/context.

``push`` is a list of zero or more lexicons, determining which lexicons to
add to the current state.

You can sort of "add" targets using a TargetFactory, which can create single
Target objects combining multiple targets in once.

"""

import collections
import itertools


Target = collections.namedtuple("Target", "pop push")


class TargetFactory:
    """Maintains a current target and allows you to store changes.

    Call get() to get the final Target, and to reset the factory's internal
    state.

    """
    __slots__ = '_pop', '_push'

    def __init__(self):
        self._pop = 0
        self._push = []

    def add(self, target):
        """Add a Target to this factory."""
        if target:
            if target.pop == 0:
                self._push.extend(target.push)
            elif -target.pop <= len(self._push):
                self._push[target.pop:] = target.push
            else:
                self._pop += len(self._push) + target.pop
                self._push[:] = target.push

    def get(self):
        """Get the current target, may be None if no pop and push.

        After this the current target is reset.

        """
        if self._pop or self._push:
            t = Target(self._pop, self._push)
            self.__init__()
            return t

    def push(self, *lexicons):
        """Enter one or more lexicons."""
        self._push.extend(lexicons)

    def pop(self, pop=-1):
        """Pop off one (or more) lexicon."""
        if pop:
            if -pop <= len(self._push):
                del self._push[pop:]
            else:
                self._pop += len(self._push) + pop
                self._push.clear()

    @classmethod
    def make(cls, lexicon, rule):
        """Create a Target of a rule."""
        if rule:
            f = cls()
            for t in rule:
                if isinstance(t, int):
                    if t < 0:
                        f.pop(t)
                    elif t:
                        f.push(*itertools.repeat(lexicon, t))
                else:
                    f.push(t)
            return f.get()


