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
from .lexicon import LexiconDescriptor, Lexicon
from .pattern import Pattern, PredicatePattern
from .rule import DynamicRuleItem
from . import util


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
        patterns = set()
        for rule in self.lexicon:
            if not isinstance(rule, (tuple, list)):
                self.error("invalid rule; should be tuple or list")
                continue
            elif len(rule) < 2:
                self.error("invalid rule; pattern and action should be there")
                continue
            pattern, *rule = rule
            if pattern is parce.default_action:
                if default_act:
                    self.error("conflicting default actions")
                else:
                    default_act = rule[0]
                    if isinstance(default_act, DynamicRuleItem):
                        self.warning("dynamic default_action; will not be replaced!")
            elif pattern is parce.default_target:
                if default_tg:
                    self.error("conflicting default targets")
                else:
                    default_tg = rule
                    self.check_default_target(default_tg)
            else:
                while isinstance(pattern, Pattern):
                    pattern = pattern.build()
                if pattern is None:
                    self.warning("pattern is None; rule will be skipped")
                else:
                    self.validate_pattern(pattern)
                    if pattern in patterns:
                        self.warning("repeated pattern {}; will be skipped".format(util.abbreviate_repr(pattern)))
                    patterns.add(pattern)
                self.validate_rule(rule)

        if default_act and default_tg:
            self.error("can't have both default_action and default_target")
        return not self.errors

    def validate_pattern(self, pattern):
        """Validate a regular expression pattern."""
        try:
            rx = re.compile(pattern, self.lexicon.re_flags)
        except (TypeError, re.error) as e:
            self.error("regular expression {} error:\n  {}".format(repr(pattern), e))
        else:
            if rx.match(''):
                self.warning("pattern {} matches the empty string".format(repr(pattern)))

    def validate_rule(self, rule):
        """Validate a rule, which should be action, target[, target, ...].

        Does not look at the action, but checks whether all the targets are
        valid (either an integer or a Lexicon).

        """
        # find all possible permutations of the rule when there are DynamicRuleItems
        def future(items):
            items = list(items)
            for i, item in enumerate(items):
                if isinstance(item, DynamicRuleItem):
                    prefix = items[:i]
                    for suffix in future(items[i+1:]):
                        for itemlist in item.itemlists:
                            for l in future(itemlist):
                                yield prefix + l + suffix
                    break
            else:
                yield items
        # all possible rule paths
        for path in future(rule):
            for target in path[1:]:     # the first item always is the action
                if not isinstance(target, (int, Lexicon)):
                    self.error("invalid target: {}".format(target))

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

