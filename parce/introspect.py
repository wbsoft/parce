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
Helper functions to inspect and document objects.
"""


from .rule import variations



def rules(lexicon):
    """Yield all rules of the lexicon, including variations.

    Every rule is a two-tuple (pattern, variations), where variations is a list
    of variations. Every variation is a two-tuple (actions, target).
    The actions is a tuple of actions and targets is a Target.

    """
    # merge items that are the only child with their parents
    def merge(node):
        for key, node in node.items():
            if key is not None:
                key = [key]
                while len(node) == 1:
                    k, n = next(iter(node.items()))
                    if k is not None:
                        key.append(k)
                        node = n
                    else:
                        break
                else:
                    node = dict(merge(node))
                key = tuple(key)
            yield key, node

    for rule in lexicon.lexicon.rules_func(lexicon.language):
        tree = {}
        for variation in variations(rule):
            d = tree
            for item in variation:
                d = d.setdefault(item, {})
            d[None] = True
        yield dict(merge(tree))
