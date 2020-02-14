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
Iterate over a tree using events.

Makes it possible to detect context or language changes without
having multiple tests or comparisons on every node.

"""


class EventHandler:
    """Iterate over a tree using events.

    You can reimplement ``context_start()``, ``context_end()``, ``tokens()``
    and possibly ``events()`` to do something useful.

    """
    def events_range(self, tree, start=0, end=None):
        """Yield events from range."""
        for context, slice_ in tree.context_slices(start, end):
            yield from self.events(context, slice_)

    def events(self, context, slice_=None):
        """Yield events for the tokens from the iterable of nodes.

        Calls ``context_start()`` and ``context_end()`` when a Context
        starts resp. ends. Yields the result from ``token()`` for every Token.

        """
        nodes = context[slice_] if slice_ is not None else context
        pos = nodes[0].pos
        end = nodes[-1].end
        self.context_start(pos, context)
        for n in nodes:
            yield from self.token(n) if n.is_token else self.events(n)
        self.context_end(end, context)

    def context_start(self, pos, context):
        """Called when a new context starts."""

    def context_end(self, end, context):
        """Called when a new context ends."""

    def token(self, token):
        """Called for a token, is expected to yield something."""
        yield token


