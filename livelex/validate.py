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


import re

import livelex


def validate_language(lang):
    """Performs checks to the specified language class.

    Detects circular default targets, empty or invalid regular expressions, etc.

    """
    lexicons = []
    for key, value in lang.__dict__.items():
        if isinstance(value, livelex.Lexicon):
            lexicons.append(getattr(lang, key))

    for lexicon in lexicons:
        default_act, default_tg = None, None
        msg = lambda s: print("{}: ".format(lexicon) + s)
        for pattern, action, *target in lexicon():
            if pattern is livelex.default_action:
                if default_act:
                    msg("conflicting default actions")
                else:
                    default_act = action
            elif pattern is livelex.default_target:
                if default_tg:
                    msg("conflicting default targets")
                else:
                    default_tg = action, *target
                    _check_default_target(lexicon, default_tg)
            else:
                # validate pattern
                if isinstance(pattern, livelex.Pattern):
                    pattern = pattern.build()
                try:
                    rx = re.compile(pattern)
                except re.error as e:
                    msg("regular expression {} error:".format(repr(pattern)))
                    print("  {}".format(e))
                else:
                    if rx.match(''):
                        msg("warning: pattern {} matches the empty string".format(repr(pattern)))
                # validate target
                def targets():
                    if len(target) == 1 and isinstance(target[0], livelex.Target):
                        for t in target[0].targets:
                            yield from t
                    else:
                        yield from target
                for t in targets():
                    if not isinstance(t, (int, livelex.BoundLexicon)):
                        msg("invalid target {} in targets {}".format(t, target))
                        break

        if default_act and default_tg:
            msg("can't have both default_action and default_target")



def _check_default_target(lexicon, target):
    """Check whether this default target could lead to circular references.

    This could hang the parser, and we wouldn't like to have that :-)

    """
    state = [lexicon]
    circular = set()
    while True:
        circular.add(lexicon)
        depth = len(state)
        for t in target:
            if isinstance(t, int):
                if t < 0:
                    if len(state) + t < 1:
                        return
                    del state[t:]
                else:
                    state += [lexicon] * t
            else:
                state.append(t)
        if len(state) == depth:
            print("{}: invalid default target".format(lexicon))
            return
        lexicon = state[-1]
        if lexicon in circular:
            state.extend(l for l in circular if l not in state)
            print("{}: circular default target: {}".format(lexicon,
                " -> ".join(map(str, state))))
        for pattern, *target in lexicon():
            if pattern is livelex.default_target:
                break
        else:
            break


