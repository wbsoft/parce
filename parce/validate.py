# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
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

import parce
from parce.lexicon import Lexicon, BoundLexicon
from parce.pattern import Pattern
from parce.target import DynamicTarget


def validate_language(lang):
    """Perform checks to the specified language class.

    Detects circular default targets, invalid regular expressions, etc.

    """
    lexicons = []
    for key, value in lang.__dict__.items():
        if isinstance(value, Lexicon):
            lexicons.append(getattr(lang, key))

    for lexicon in lexicons:
        validate_lexicon(lexicon)


def validate_lexicon(lexicon):
    default_act, default_tg = None, None
    msg = message(lexicon)
    for pattern, action, *target in lexicon():
        if pattern is parce.default_action:
            if default_act:
                msg("conflicting default actions")
            else:
                default_act = action
        elif pattern is parce.default_target:
            if default_tg:
                msg("conflicting default targets")
            else:
                default_tg = action, *target
                check_default_target(lexicon, default_tg)
        else:
            validate_pattern(msg, pattern)
            validate_target(msg, target)

    if default_act and default_tg:
        msg("can't have both default_action and default_target")


def validate_pattern(msg, pattern):
    """Validate a regular expression pattern."""
    if isinstance(pattern, Pattern):
        pattern = pattern.build()
    try:
        rx = re.compile(pattern)
    except re.error as e:
        msg("regular expression {} error:\n  {}".format(repr(pattern), e))
    else:
        if rx.match(''):
            msg("warning: pattern {} matches the empty string".format(repr(pattern)))


def validate_target(msg, target):
    """Validate a target."""
    def targets():
        if len(target) == 1 and isinstance(target[0], DynamicTarget):
            for t in target[0].targets:
                yield from t
        else:
            yield from target
    for t in targets():
        if isinstance(t, DynamicTarget):
            msg("a DynamicTarget must be the only one: {}".format(target))
        elif not isinstance(t, (int, BoundLexicon)):
            msg("invalid target {} in targets {}".format(t, target))
            break


def check_default_target(lexicon, target):
    """Check whether this default target could lead to circular references.

    This could hang the parser, and we wouldn't like to have that :-)

    """
    state = [lexicon]
    circular = set()
    while True:
        msg = message(lexicon)
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
            elif not isinstance(t, BoundLexicon):
                msg("in default target only integer or lexicon allowed")
                return
            else:
                state.append(t)
        if len(state) == depth:
            msg("invalid default target")
            return
        lexicon = state[-1]
        if lexicon in circular:
            state.extend(l for l in circular if l not in state)
            msg("circular default target: {}".format(" -> ".join(map(str, state))))
            return
        for pattern, *target in lexicon():
            if pattern is parce.default_target:
                break
        else:
            break


def message(lexicon):
    """Return a callable that prints a message with the lexicon name prepended."""
    return lambda s: print("{}: ".format(lexicon) + s)

