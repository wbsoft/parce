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
Replacable rule item objects.

When the Lexicon builds its internal representation of the rules,
RuleItem instances are evaluated in two stages. First, the items
are pre-elevated: meaning that the items that depend on the lexicon
argument (the ARG variable) are evaluated.

When a rule matches during parsing, the rest of the items are evaluated
using the TEXT and the MATCH variables.

Only Items that inherit from RuleItem may directly appear in a rule,
and items that they expose (such as the items a :class:`select` Item selects
from) must also inherit from RuleItem.

This way, we can be sure that we are able to validate a Lexicon beforehand,
and know all actions or target lexicons that it might yield during parsing.

A third evaluation stage happens in the lexer, for Item objects that inherit
of ActionItem.

The following fixed Item instances are defined here:

``ARG``
    represents the lexicon argument
``MATCH``
    represents the match object of a regular expression match
``TEXT``
    represents the matched text

The match and text variables have some additional functionality:

``MATCH(n)``
    represents the text in a subgroup of the match (subgroups start with 1)
``MATCH(n)[s]``
    represents a slice of the text in a subgroup (fails if the group is None)
``TEXT[s]``
    represents a slice of the matched text

Very often you want to use a predicate function on one of the above
variables, then you need the ``call`` item type:

``call(callable, *arguments)``
    gets the result of calling callable with zero or more arguments

Callable and arguments may also be Item instances.
The ``call`` item type is not allowed directly in a rule, because is not clear
what value it will return. Use it in combination with ``select``, ``target``,
``pattern`` or dynamic actions (see below).

The following items are RuleItem types (allowed in toplevel in a rule):

``select(index, *items)``
    selects the item pointed to by the value in index. The item that ends up in
    a rule is unrolled when it is a list.
``target(value, *lexicons)``
    has a special handling: if the value is an integer, return it (pop or push
    value). If it is a two-tuple(index, arg): derive the lexicon at index with
    arg.

And the following items may also appear in a rule, they survive evaluating,
although the *pre*-evaluation process may alter their attributes:

``pattern(value)``
    only allowed as the first item in a rule; is expected to create a string
    or None. If None, the whole rule is skipped.

``ActionItem(*items)``
    base class for dynamic actions. Those are not evaluated by the Lexicon,
    although the items they contain may be. The lexer takes care of these
    items.

"""


from . import ruleitem


#: the lexicon argument
ARG = ruleitem.VariableItem('arg')

#: the regular expression match (or None)
MATCH = ruleitem.VariableItem('match', (lambda m, n: m.group(m.lastindex + n)))

#: the matched text
TEXT = ruleitem.VariableItem('text')


def call(predicate, *arguments):
    return ruleitem.call(predicate, *arguments)


def select(index, *items):
    return ruleitem.select(index, *items)


def pattern(value):
    return ruleitem.pattern(value)


def target(value, *lexicons):
    return ruleitem.target(value, *lexicons)


