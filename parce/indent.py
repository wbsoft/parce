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
    this is a blank line, the current indent level is not changed.

``CURRENT_INDENT, string``:
    the current indent string this line has.

``INDENT``
    next line should be indented a level.

``NO_INDENT``:
    the indent of this line may not be changed at all, e.g. because it is part
    of a multiline string.

``DEDENT``:
    next line should be dedented a level. (If this event occurs before
    ``INDENT`` or ``NO_DEDENT``, the current line can be dedented.)

``NO_DEDENT``:
    further ``DEDENT`` events will not dedent the current line anymore, but
    rather affect the indentation of the next line.

``PREFER_INDENT``, ``string``:
    use this indent for the current line, but do not change the indent level or
    the current indent for the next line.

``NO_STRIP``:
    trailing whitespace should not be stripped off this line.

``ALIGN``, ``string``:
    The last ``INDENT`` event should use the specified string for alignment
    instead of the default indent (relatively to the start of the text in the
    current line excluding the current indent).

"""

import collections
import sys
import threading

# events w/o args
INDENT          = 1
DEDENT          = 2
NO_DEDENT       = 3

# with string args
PREFER_INDENT   = 4
CURRENT_INDENT  = 5
ALIGN           = 6

# state for whole line
BLANK           = 64
NO_STRIP        = 128
NO_INDENT       = 256



class IndentInfo:
    """Contains information about how to indent a block.

    Created by :meth:`AbstractIndenter.indent_info` and used within
    :meth:`AbstractIndenter.indent`.

    """
    __slots__ = ("block", "indents", "dedents_start", "dedents_end", "indent",
                 "prefer_indent", "_state")

    def __init__(self, block):
        self.block = block          #: the Block
        self.indents = []           #: the indent events (None or string)
        self.dedents_start = 0      #: the number of dedents at the start of the line
        self.dedents_end = 0        #: the number of dedents later in the line
        self.indent = None          #: the current indent
        self.prefer_indent = None   #: a preferred, special case indent
        self._state = 0             #: mask of BLANK, NO_STRIP, NO_INDENT

    @property
    def allow_indent(self):
        """Whether the indent of this line may be changed."""
        return self._state & NO_INDENT == 0

    @property
    def allow_strip(self):
        """Whether trailing whitespace may be stripped of this line."""
        return self._state & NO_STRIP == 0

    @property
    def is_blank(self):
        return self._state & BLANK == BLANK


class AbstractIndenter:
    """Indents (part of) a Document.

    The indenting preferences can be set using some instance attributes.

    """

    #: the string to indent each level with, defaulting to two spaces.
    indent_string = "  "

    #: whether to also indent blank lines
    indent_blank_lines = True

    def indent(self, cursor):
        """Indent all the lines in the cursor's range.

        This method scans the document always from the beginning, although it
        doesn't change lines before the start of the cursor's range. To
        re-indent a full document, select all text in the cursor (i.e. ``pos``
        is 0, ``end`` is None).

        """
        prev_info = None
        indents = ['']

        with cursor.document() as d:
            for block in d.blocks():
                info = self.indent_info(block, indents)

                # handle indents in previous line
                if prev_info and prev_info.indents:
                    current_indent = indents[-1]
                    for indent in prev_info.indents:
                        indents.append(current_indent + (indent or self.indent_string))

                # dedents at start of current line
                del indents[max(1, len(indents) - info.dedents_start):]

                # if we may not change the indent just remember the current
                if info.allow_indent and (self.indent_blank_lines or not info.is_blank):
                    if block.pos < cursor.pos:
                        # we're outside the cursor's range
                        # obey the existing indent if not a special case
                        if info.prefer_indent is None:
                            indents[-1] = info.indent
                    else:
                        # we're inside the cursor's range; may replace the indent
                        if info.prefer_indent is not None:
                            new_indent = info.prefer_indent
                        else:
                            new_indent = indents[-1]
                        if new_indent != info.indent:
                            d[block.pos:block.pos + len(info.indent)] = new_indent

                # dedents at end of current line
                del indents[max(1, len(indents) - info.dedents_end):]

                # done?
                if cursor.end is not None and block.end >= cursor.end:
                    break

                prev_info = info

    def auto_indent(self, cursor):
        """Adjust the indent of the single block at the Cursor's pos."""
        block = b = cursor.block()
        info = self.indent_info(block)
        if info.allow_indent:
            new_indent = current_indent = info.indent
            if info.prefer_indent is not None:
                new_indent = info.prefer_indent
            else:
                # search backwards
                depth = info.dedents_start
                while not b.is_first():
                    b = b.previous_block()
                    info = self.indent_info(b)
                    if info.allow_indent:
                        if 0 <= depth < len(info.indents):
                            # we found the indent to use
                            index = len(info.indents) - depth - 1
                            new_indent = info.indent + (info.indents[index] or self.indent_string)
                            break
                        depth -= len(info.indents)
                        depth += info.dedents_end
                        if depth == 0:
                            # same indent as this line
                            new_indent = info.indent
                            break
                        depth += info.dedents_start
            if new_indent != current_indent:
                with cursor.document() as d:
                    d[block.pos:block.pos + len(current_indent)] = new_indent

    def increase_indent(self, cursor):
        """Increase the indent in the Cursor's lines."""
        with cursor.document() as d:
            for b in cursor.blocks():
                info = self.indent_info(b)
                if info.allow_indent:
                    d.insert(b.pos, self.indent_string)

    def decrease_indent(self, cursor):
        """Decrease the indent in the Cursor's lines."""
        # TODO: 'd be nice to make it smarter and search backwards for indents.
        with cursor.document() as d:
            for b in cursor.blocks():
                info = self.indent_info(b)
                if info.allow_indent and info.indent:
                    if info.indent.startswith(self.indent_string):
                        remove = self.indent_string
                    else:
                        remove = info.indent
                    del d[b.pos:b.pos + len(remove)]

    def strip_trailing_blanks(self, cursor, chars=None):
        """Strip trailing blanks off the selected lines.

        Lines that don't allow changing the indent are skipped. The ``chars``
        argument is passed on to the Python :py:meth:`~str.strip` method.

        """
        with cursor.document() as d:
            for b in cursor.blocks():
                info = self.indent_info(b)
                if info.allow_strip:
                    new_text = b.text().rstrip(chars)
                    if len(new_text) != len(b):
                        del d[b.pos+len(new_text):b.end]

    def indent_info(self, block, prev_indents=()):
        """Return an IndentInfo object for the specified block."""

        info = IndentInfo(block)

        find_dedents = True

        for event, *args in self.indent_events(block, prev_indents):
            if event is INDENT:
                info.indents.append(None)
                find_dedenters = False
            elif event is DEDENT:
                if find_dedents:
                    info.dedents_start += 1
                elif indenters:
                    info.indents.pop()
                else:
                    info.dedents_end += 1
            elif event is NO_DEDENT:
                find_dedents = False
            elif event is CURRENT_INDENT:
                info.indent = args[0]
            elif event is ALIGN and info.indents and args:
                info.indents[-1] = args[0]
            elif event is PREFER_INDENT:
                info.prefer_indent = args[0]
            else: # event in (BLANK, NO_INDENT, NO_STRIP):
                info._state |= event

        # if no CURRENT_INDENT was yielded, just pick the first whitespace if allowed
        if info.indent is None:
            if info.allow_indent:
                text = block.text()
                info.indent = text[:-len(text.lstrip())]
            else:
                info.indent == ""
        return info

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

    def add_indent(self, language, indent):
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


