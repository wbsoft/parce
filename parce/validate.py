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


import re

import parce
from parce.lexicon import Lexicon, BoundLexicon
from parce.pattern import Pattern
from parce.target import DynamicTarget


def validate_language(lang):
    """Validate all lexicons in this language.

    Errors and warnings are printed to stdout. If there are errors,
    this function returns False, otherwise True.

    """

    lexicons = []
    for key, value in lang.__dict__.items():
        if isinstance(value, Lexicon):
            lexicons.append(getattr(lang, key))

    correct = True
    for lexicon in lexicons:
        correct &= LexiconValidator(lexicon).validate()
    return correct


class LexiconValidator:

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.errors = False

    def error(self, msg, lexicon=None):
        """Print message to stdout with lexicon name prepended. Sets error flag."""
        self.errors = True
        print("{}: error: {}".format(lexicon or self.lexicon, msg))

    def warning(self, msg, lexicon=None):
        """Print message to stdout with lexicon name prepended. Sets error flag."""
        print("{}: warning: {}".format(lexicon or self.lexicon, msg))

    def validate(self):
        """Validate a lexicon and return True if no errors, False otherwise."""
        self.errors = False
        print("Validating lexicon {}".format(self.lexicon))

        default_act, default_tg = None, None
        for pattern, action, *target in self.lexicon():
            if pattern is parce.default_action:
                if default_act:
                    self.error("conflicting default actions")
                else:
                    default_act = action
            elif pattern is parce.default_target:
                if default_tg:
                    self.error("conflicting default targets")
                else:
                    default_tg = action, *target
                    self.check_default_target(default_tg)
            else:
                self.validate_pattern(pattern)
                self.validate_target(target)

        if default_act and default_tg:
            self.error("can't have both default_action and default_target")
        return not self.errors

    def validate_pattern(self, pattern):
        """Validate a regular expression pattern."""
        if isinstance(pattern, Pattern):
            pattern = pattern.build()
        try:
            rx = re.compile(pattern, self.lexicon.re_flags)
        except re.error as e:
            self.error("regular expression {} error:\n  {}".format(repr(pattern), e))
        else:
            if rx.match(''):
                self.warning("pattern {} matches the empty string".format(repr(pattern)))

    def validate_target(self, target):
        """Validate a target."""
        def targets():
            if len(target) == 1 and isinstance(target[0], DynamicTarget):
                for t in target[0].targets:
                    yield from t
            else:
                yield from target
        for t in targets():
            if isinstance(t, DynamicTarget):
                self.error("a DynamicTarget must be the only one: {}".format(target))
            elif not isinstance(t, (int, BoundLexicon)):
                self.error("invalid target {} in targets {}".format(t, target))
                break

    def check_default_target(self, target):
        """Check whether this default target could lead to circular references.

        This could hang the parser, and we wouldn't like to have that :-)

        """
        lexicon = self.lexicon
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
                elif not isinstance(t, BoundLexicon):
                    self.error("in default target only integer or lexicon allowed", lexicon)
                    return
                else:
                    state.append(t)
            if len(state) == depth:
                self.error("invalid default target", lexicon)
                return
            lexicon = state[-1]
            if lexicon in circular:
                state.extend(l for l in circular if l not in state)
                self.error("circular default target: {}".format(" -> ".join(map(str, state))), lexicon)
                return
            for pattern, *target in lexicon():
                if pattern is parce.default_target:
                    break
            else:
                break

