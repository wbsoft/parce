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
This module provides Indenter to indent a Document.

To use the :class:`Indenter`: instantiate one and call its
:meth:`~AbstractIndenter.indent` method with a :class:`~parce.Cursor`
describing the text range to indent. For example::

    >>> from parce import Document, Cursor
    >>> from parce.indent import Indenter
    >>> from parce.lang.css import Css
    >>> i = Indenter()
    >>> i.indent_string = "    " # use four spaces by default
    >>> d = Document(Css.root, "h1 {\ncolor: red;\n     }\n")
    >>> c = Cursor(d, 0, None)  # select all
    >>> i.indent(c)
    >>> d.text()
    'h1 {\n    color: red;\n}\n'

Indenter uses per-language Indent classes which define the indenting behaviour.
You can add them manually to Indenter, but it can also find Indent classes
automatically by looking in the language's module and finding there an Indent
subclass with the same name, with "Indent" appended.

To further adapt the indenting behaviour, you can implement the
:meth:`~AbstractIndenter.indent_events` method of the Indenter. Or the
:meth:`Indent.indent_events` method of the language-specific indenter.

The following events can be yielded (simply module constants):

    ``BLANK``:
        this is a blank line, the current indent level is not changed

    ``CURRENT_INDENT, string``:
        the current indent string this line has.

    ``INDENT`` [``, string``]:
        next line should be indented a level. If string is given, that indent
        is used instead of the default indent (relatively to the start of the
        text in the current line excluding the current indent).

    ``NO_INDENT``:
        the indent of this line may not be changed at all, e.g. because it is
        part of a multiline string.

    ``DEDENT``:
        next line should be dedented a level. (If this event occurs before
        ``INDENT`` or ``NO_DEDENT``, the current line can be dedented.)

    ``NO_DEDENT``:
        further ``DEDENT`` events will not dedent the current line anymore, but
        rather affect the indentation of the next line.

    ``PREFER_INDENT``, ``string``:
        use this indent for the current line, but do not change the indent
        level or the current indent for the next line.


"""

import collections
import sys
import threading


BLANK           = 1
CURRENT_INDENT  = 2
INDENT          = 3
NO_INDENT       = 4
DEDENT          = 5
NO_DEDENT       = 6
PREFER_INDENT   = 7


Dedenters = collections.namedtuple("Dedenters", "start end")
"""Dedenters at the ``start`` and the ``end`` of the line."""


IndentInfo = collections.namedtuple("IndentInfo",
    "block is_blank indent allow_indent indenters dedenters prefer_indent")
"""Contains information about how to indent a block.

Created by :meth:`AbstractIndenter.indent_info` and used within
:meth:`AbstractIndenter.indent`.

"""

class AbstractIndenter:
    """Indents (part of) a Document.

    """

    indent_string = "  "

    def indent(self, cursor):
        """Indent all the lines in the cursor's range."""
        prev_line_info = None
        indents = ['']

        with cursor.document() as d:
            for block in d.blocks():
                line_info = self.indent_info(block, indents)

                # handle indents in previous line
                if prev_line_info and prev_line_info.indenters:
                    current_indent = indents[-1]
                    for indent in prev_line_info.indenters:
                        indents.append(current_indent + (indent or self.indent_string))

                # dedents at start of current line
                del indents[max(1, len(indents) - line_info.dedenters.start):]

                # if we may not change the indent just remember the current
                if line_info.allow_indent and not line_info.is_blank:
                    if block.pos < cursor.pos:
                        # we're outside the cursor's range
                        # obey the existing indent if not a special case
                        if line_info.prefer_indent is None:
                            indents[-1] = line_info.indent
                    else:
                        # we're inside the cursor's range; may replace the indent
                        if line_info.prefer_indent is not None:
                            new_indent = line_info.prefer_indent
                        else:
                            new_indent = indents[-1]
                        if new_indent != line_info.indent:
                            d[block.pos:block.pos + len(line_info.indent)] = new_indent

                # dedents at end of current line
                del indents[max(1, len(indents) - line_info.dedenters.end):]

                # done?
                if cursor.end is not None and block.end >= cursor.end:
                    break

                prev_line_info = line_info

    def indent_info(self, block, prev_indents=()):
        """Return an IndentInfo object for the specified block."""

        blank = False           # False or True
        allow_indent = True     # False or True
        indent = None           # string (is set later)
        indenters = []          # list of string/None elements
        dedenters_start = 0     # # of dedenters at the beginning of the line
        dedenters_end = 0       # # of dedenters later in the line
        prefer_indent = None    # prefer a special case indent (None or string)

        find_dedenters = True

        for event, *args in self.indent_events(block, prev_indents):
            if event is BLANK:
                blank = True
            elif event is CURRENT_INDENT:
                indent = args.pop()
            elif event is INDENT:
                indenters.append(args.pop() if args else None)
                find_dedenters = False
            elif event is NO_INDENT:
                allow_indent = False
            elif event is DEDENT:
                if find_dedenters:
                    dedenters_start += 1
                elif indenters:
                    indenters.pop()
                else:
                    dedenters_end += 1
            elif event is NO_DEDENT:
                find_dedenters = False
            elif event is PREFER_INDENT:
                prefer_indent = args.pop()

        # if no CURRENT_INDENT was yielded, just pick the first whitespace if allowed
        if indent is None:
            text = block.text()
            indent = text[:-len(text.lstrip())] if allow_indent else ""

        dedenters = Dedenters(dedenters_start, dedenters_end)
        return IndentInfo(block, blank, indent, allow_indent, indenters, dedenters, prefer_indent)

    def indent_events(self, block, prev_indents=()):
        """Implement this method to yield indenting events for the block."""
        return
        yield


class Indenter(AbstractIndenter):
    """Indenter that uses Language-specific indenters if available.

    This can only be used on documents that have TreeDocument mixed in, i.e.
    have a tree available.

    """
    def __init__(self):
        self._lock = threading.Lock()   # for instantiating Indents
        self._indents = {}

    def indent_events(self, block, prev_indents=()):
        """Reimplemented to use Indent subclasses for the specified language."""
        tokens = block.tokens()
        if tokens:
            curlang = tokens[0].parent.lexicon.language
            i = 0
            for j in range(1, len(tokens)):
                newlang = tokens[j].parent.lexicon.language
                if newlang is not curlang:
                    indenter = self.get_indent(curlang)
                    if indenter:
                        yield from indenter.indent_events(
                            block, tokens[i:j], i == 0, prev_indents)
                    i = j
                    curlang = newlang
            indenter = self.get_indent(curlang)
            if indenter:
                yield from indenter.indent_events(
                    block, tokens[i:], i == 0, prev_indents)

    def get_indent(self, language):
        """Return a Indent class instance for the specified language."""
        try:
            return self._indents[language]
        except KeyError:
            with self._lock:
                try:
                    i = self._indents[language]
                except KeyError:
                    i = self._indents[language] = self.find_indent(language)
                return i

    def add_indent(self, language, transform):
        """Add a Indent instance for the specified language."""
        self._indents[language] = indent

    def find_indent(self, language):
        """If no Indent was added, try to find a predefined one.

        This is done by looking for a Indent subclass in the language's
        module, with the same name as the language with "Indent" appended.
        So for a language class named "Css", this method tries to find a
        Indent in the same module with the name "CssIndent".

        If no Indent is found, for the language, the language's base classes
        are also tried.

        """
        for lang in language.mro():
            module = sys.modules[lang.__module__]
            name = lang.__name__ + "Indent"
            indent = getattr(module, name, None)
            if isinstance(indent, type) and issubclass(indent, Indent):
                return indent()


class Indent:
    """The base class for language-specific indenters."""
    def indent_events(self, block, tokens, is_first, prev_indents):
        """Implement this to yield indent events for the tokens.


        """
        return
        yield


