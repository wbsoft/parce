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
"""

import itertools


class Target:
    """Abstracts a target.

    A Target has two attributes:

        ``pop``
            zero or negative integer, indicating how may contexts to pop
            off the current context.

        ``push``
            a list of lexicons that need to be created. A lexicon may be None,
            indicating that the same lexicon needs to be pushed.

    Targets can be added and be applied in once if desired.
    A Target evaluates to None if pop == 0 and push is the empty list.

    A Target is instantiated with the list of targets in a rule.

    """
    __slots__ = 'pop', 'push'

    def __new__(cls, lexicon=None, args=()):
        pop = 0
        push = []
        for i in args:
            if isinstance(i, int):
                if i < 0:
                    if -i < len(push):
                        del push[i:]
                    else:
                        pop += len(push) + i
                        push.clear()
                elif i:
                    push.extend(itertools.repeat(lexicon, i))
            else:
                push.append(i)
        return cls._make(pop, push)

    @classmethod
    def _make(cls, pop, push):
        if pop or push:
            target = object.__new__(cls)
            target.pop = pop
            target.push = push
            return target

    def __repr__(self):
        return '<Target {} [{}]>'.format(self.pop, ' '.join(map(format, self.push)))

    def __bool__(self):
        return bool(self.pop or self.push)

    def __eq__(self, other):
        if isinstance(other, Target):
            return self.pop == other.pop and self.push == other.push
        elif other is None:
            return self.pop == 0 and not self.push
        else:
            return super().__eq__(other)

    def __ne__(self, other):
        if isinstance(other, Target):
            return self.pop != other.pop or self.push != other.push
        elif other is None:
            return bool(self.pop or self.push)
        else:
            return super().__ne__(other)

    def __add__(self, other):
        if other is None:
            pop = self.pop
            push = self.push
        elif other.pop == 0:
            pop = self.pop
            push = self.push + other.push
        elif -other.pop <= len(self.push):
            pop = self.pop
            push = self.push[:other.pop] + other.push
        else:
            pop = self.pop + len(self.push) + other.pop
            push = other.push
        return self._make(pop, push)

    __radd__ = __add__

    @classmethod
    def enter(cls, lexicon):
        """Return a new Target with lexicon pushed."""
        target = object.__new__(cls)
        target.pop = 0
        target.push = [lexicon]
        return target

    @classmethod
    def leave(cls):
        """Return a new Target that pops one lexicon off."""
        target = object.__new__(cls)
        target.pop = -1
        target.push = []
        return target

