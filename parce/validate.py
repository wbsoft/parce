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


import collections
import re

import parce
from parce.lexicon import LexiconDescriptor, Lexicon
from parce.pattern import Pattern
from parce.target import DynamicTarget


def validate_language(lang):
    """Validate all lexicons in this language.

    Errors and warnings are printed to stdout. If there are errors,
    this function returns False, otherwise True.

    """

    lexicons = []
    for key, value in lang.__dict__.items():
        if isinstance(value, LexiconDescriptor):
            lexicons.append(getattr(lang, key))

    errors = set()
    warnings = set()
    for lexicon in lexicons:
        v = LexiconValidator(lexicon)
        v.validate()
        errors.update(v.errors)
        warnings.update(v.warnings)
    for warning in warnings:
        print(warning)
    for error in errors:
        print(error)
    return not errors


class LexiconValidator:

    def __init__(self, lexicon):
        self.lexicon = lexicon
        self.errors = set()
        self.warnings = set()

    def error(self, msg, lexicon=None):
        """Add message to errors."""
        msg = "{}: error: {}".format(lexicon or self.lexicon, msg)
        self.errors.add(msg)

    def warning(self, msg, lexicon=None):
        """Add message to warnings."""
        msg = "{}: warning: {}".format(lexicon or self.lexicon, msg)
        self.warnings.add(msg)

    def validate(self):
        """Validate a lexicon.

        Errors and warnings are left in the ``errors`` and ``warnings``
        attributes, respectively.

        """
        self.errors.clear()
        self.warnings.clear()
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
            elif not isinstance(t, (int, Lexicon)):
                self.error("invalid target {} in targets {}".format(t, target))
                break

    def check_default_target(self, target):
        """Check whether this default target could lead to circular references.

        This could hang the parser, and we wouldn't like to have that :-)

        """
        # a unique object for every entered context, mimicking tree builder behaviour
        class Context:
            def __init__(self, lexicon):
                self.lexicon = lexicon

        lexicon = self.lexicon
        lexicons = collections.Counter()    # count them to find the circular culprits
        state = [Context(lexicon)]
        circular = set()                    # track circular (existing) contexts
        warn = False
        context = state[-1]
        while True:
            circular.add(context)
            lexicons.update((lexicon,))     # count
            depth = len(state)
            for t in target:
                if isinstance(t, int):
                    if t < 0:
                        if len(state) + t < 1:
                            return
                        del state[t:]
                    else:
                        for _ in range(t):
                            state.append(Context(lexicon))
                elif not isinstance(t, Lexicon):
                    self.error("in default target only integer or lexicon allowed", lexicon)
                    return
                else:
                    state.append(Context(t))
            newcontext = state[-1]
            lexicon = newcontext.lexicon
            if newcontext is context:
                self.error("invalid default target", lexicon)
                return
            context = newcontext
            if newcontext in circular:
                # a circular default state that lands in an existing context
                # is handled gracefully by the tree builder
                warn = True
            if len(circular) > 100:
                lexicons = " <-> ".join(str(l) for l, n in lexicons.items() if n > 1)
                if warn:
                    # this type of circular default state is handled
                    self.warning("handled circular default target: {}".format(lexicons), lexicon)
                else:
                    # run away default states creating new contexts all the time
                    self.error("circular default target: {}".format(lexicons), lexicon)
                return
            for pattern, *target in lexicon():
                if pattern is parce.default_target:
                    break
            else:
                break

