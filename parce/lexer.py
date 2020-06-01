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


r"""
The Lexer is responsible for parsing text using Lexicons.

The lexer generates Event objects, which contain a target (or None) and one or
more tokens. The target, if not None, specifies a state change (i.e. leave the
current lexicon(s) or descend into specified lexicons. (See the
:mod:`~parce.target` module.)

The tokens is a tuple of one or more token tuples. A token is a ``(pos, text,
action)`` tuple. Note that an Event always contains at least one token tuple,
and that a tokens's text is always non-empty. (A rule's pattern might match the
empty string, but no token is generated in that case, although the target is
followed.)

The Lexer is capable of handling circular default targets: if a target is
pushed again in the same context at the same text position (and another
target pops back), it is detected and the text position pointer is advanced
by one. (Run-away pushed targets are not detected, those are detected by
the :mod:`~parce.validate` module.)

The TreeBuilder (:mod:`~parce.treebuilder`) uses a Lexer internally to parse
text and create the tree structure.

Example::

    >>> import parce.lexer
    >>> import parce.lang.css
    >>> for e in parce.lexer.Lexer([parce.lang.css.Css.root]).events("h1 { color: red; }"):
    ...     print(e)
    ...
    Event(target=Target(pop=0, push=[Css.prelude, Css.selector, Css.element_selector]), tokens=((0, 'h1', Name.Tag),))
    Event(target=Target(pop=-2, push=[]), tokens=((3, '{', Delimiter),))
    Event(target=Target(pop=-1, push=[Css.rule, Css.declaration, Css.property]), tokens=((5, 'color', Name.Property),))
    Event(target=Target(pop=-1, push=[]), tokens=((10, ':', Delimiter),))
    Event(target=Target(pop=0, push=[Css.identifier]), tokens=((12, 'red', Literal.Color),))
    Event(target=Target(pop=-1, push=[]), tokens=((15, ';', Delimiter),))
    Event(target=Target(pop=-1, push=[]), tokens=((17, '}', Delimiter),))

There is a convenience function in the *parce* module namespace that calls
Lexer for you::

    >>> import parce
    >>> from parce.lang.css import Css
    >>> for e in parce.events(Css.root, "h1 { color: red; }"):
    ...     print(e)

And here's how the same text would translate to a tree structure::

    >>> parce.root(parce.lang.css.Css.root, "h1 { color: red; }").dump()
    <Context Css.root at 0-18 (2 children)>
     ├╴<Context Css.prelude at 0-4 (2 children)>
     │  ├╴<Context Css.selector at 0-2 (1 children)>
     │  │  ╰╴<Context Css.element_selector at 0-2 (1 children)>
     │  │     ╰╴<Token 'h1' at 0:2 (Name.Tag)>
     │  ╰╴<Token '{' at 3:4 (Delimiter)>
     ╰╴<Context Css.rule at 5-18 (2 children)>
        ├╴<Context Css.declaration at 5-16 (4 children)>
        │  ├╴<Context Css.property at 5-10 (1 children)>
        │  │  ╰╴<Token 'color' at 5:10 (Name.Property)>
        │  ├╴<Token ':' at 10:11 (Delimiter)>
        │  ├╴<Context Css.identifier at 12-15 (1 children)>
        │  │  ╰╴<Token 'red' at 12:15 (Literal.Color)>
        │  ╰╴<Token ';' at 15:16 (Delimiter)>
        ╰╴<Token '}' at 17:18 (Delimiter)>


"""


import collections

from .ruleitem import ActionItem, Item, unroll
from .target import TargetFactory, Target


Event = collections.namedtuple("Event", "target tokens")


class Lexer:
    """A Lexer is responsible for parsing text using Lexicons.

    ``lexicons`` is a list of one or more lexicon instances, the first one
    being the root lexicon. Lexicons can add lexicons to this list and pop
    lexicons off while parsing text. The first lexicon is never popped off.

    While parsing text using the ``events()`` method, the ``lexicons``
    attribute reflects the current state: the current lexicon is at the end.

    """
    def __init__(self, lexicons):
        """Lexicons should be an iterable of one or more lexicons."""
        self.lexicons = list(lexicons)

    def events(self, text, pos=0):
        """Get the events from parsing text from the specified position."""
        lexicons = self.lexicons
        target_factory = TargetFactory()
        get_target = target_factory.get # access methods directly (faster)
        add_target = target_factory.add
        circular = set()

        def event():
            # yield Event, all vars are nonlocal :-)
            if isinstance(action, ActionItem):
                tokens = tuple(action.replace(self, pos, txt, match))
                if tokens:
                    yield Event(get_target(), tokens)
            else:
                yield Event(get_target(), ((pos, txt, action),))

        while True:
            for pos, txt, match, action, target in lexicons[-1].parse(text, pos):
                if target:
                    # never pop off root
                    if target.pop and -target.pop >= len(lexicons):
                        target = Target(1 - len(lexicons), target.push)
                    if txt:
                        if target.push and target.push[-1].consume:
                            # lexicon wants the starting tokens; handle target now
                            if target.pop:
                                del lexicons[target.pop:]
                            lexicons.extend(target.push)
                            add_target(target)
                            yield from event()
                        else:
                            yield from event()
                            if target.pop:
                                del lexicons[target.pop:]
                            lexicons.extend(target.push)
                            add_target(target)
                        circular.clear()
                        pos += len(txt)
                    else:
                        if target.pop:
                            del lexicons[target.pop:]
                        state = (pos, len(lexicons), len(target.push))
                        if state in circular:
                            if pos < len(text):
                                pos += 1
                            circular.clear()
                        else:
                            circular.add(state)
                        lexicons.extend(target.push)
                        add_target(target)
                    break   # continue with new lexicon
                elif txt:
                    yield from event()
            else:
                break   # done

    def filter_actions(self, action, pos, text, match):
        """Handle filtering via DynamicAction instances."""
        if isinstance(action, Item):
            if isinstance(action, ActionItem):
                yield from action.replace(self, pos, text, match)
            else:
                for action in unroll(action.evaluate({'text': text, 'match': match})):
                    yield from self.filter_actions(action, pos, text, match)
        elif text:
            yield pos, text, action
