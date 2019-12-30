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


"""
Document and Cursor form the basis of handling of documents in the livelex
package.

A Document contains a text string that is mutable via item and slice methods.

If you make modifications while inside a context (using the Python context
manager protocol), the modifications are only applied when the context
exits for the last time.

You can use a Cursor to keep track of positions in a document. The position
(and selection) of a Cursor is adjusted when the text in the document is
changed.

For tokenized documents, livelex inherits from this base class.

"""



import weakref


class Document:
    """A Document is like a mutable string. E.g.:

    .. code-block:: python

        d = Document('some string')
        with d:
            d[5:5] = 'different '
        d.text()  --> 'some different string'

    You can also make modifications outside the a context, they will then
    be applied immediately, which is slower.

    You can enter a context multiple times, and changes will be applied when the
    last exits.

    """
    undoRedoEnabled = True

    def __init__(self, text=""):
        self._cursors = weakref.WeakSet()
        self._edit_context = 0
        self._changes = []
        self._text = text
        self._modified_range = None
        self._undo_stack = []
        self._redo_stack = []
        self._in_undo = None

    def __repr__(self):
        text = self._text
        if len(text) > 30:
            text = text[:28] + "..."
        return "<{} {}>".format(type(self).__name__, repr(text))

    def __str__(self):
        return self._text

    def __format__(self, formatstr):
        return self._text.__format__(formatstr)

    def __len__(self):
        return len(self._text)

    def text(self):
        """Return all text."""
        return self._text

    def set_text(self, text):
        """Replace all text."""
        self._text = text
        self._modified_range = None

    def __enter__(self):
        """Start the context for modifying the document."""
        self._edit_context += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context for modifying."""
        if exc_type is not None:
            # cancel all edits when an exception occurred
            self._edit_context = 0
            self._changes.clear()
        elif self._edit_context > 1:
            self._edit_context -= 1
        else:
            self._edit_context = 0
            self._apply()

    def __setitem__(self, key, value):
        if isinstance(key, Cursor):
            start = key.start
            end = key.end
        elif isinstance(key, slice):
            start = key.start or 0
            end = key.stop
        else:
            start = key
            end = key + 1
        if self._text[start:end] != value:
            self._changes.append((start, end, value))
            if not self._edit_context:
                self._apply()

    def __delitem__(self, key):
        self[key] = ""

    def __getitem__(self, key):
        if isinstance(key, Cursor):
            return self._text[key.start:key.end]
        return self._text[key]

    def _apply(self):
        """Apply the changes and update the positions of the cursors."""
        if self._changes:
            self._changes.sort()
            head = tail = self._changes[0][0]
            result = []
            cursors = sorted(self._cursors, key = lambda c: c.start)
            i = 0   # cursor index
            for start, end, text in self._changes:
                if tail is not None:
                    if start > tail:
                        result.append(self._text[tail:start])
                    if text:
                        result.append(text)
                    tail = end
                for c in cursors[i:]:
                    ahead = c.start > start
                    if ahead:
                        if end is None or end >= c.start:
                            c.start = start
                        else:
                            c.start += start + len(text) - end
                    if c.end is not None and c.end >= start:
                        if end is None or end >= c.end:
                            c.end = start + len(text)
                        else:
                            c.end += start + len(text) - end
                    elif not ahead:
                        i += 1  # don't consider this cursor any more
            self._changes.clear()
            text = "".join(result)
            if self.undoRedoEnabled:
                self._handle_undo(head, head + len(text), self._text[head:tail])
            self._modify(head, tail, text)

    def _modify(self, start, end, text):
        """Called by _apply(), replace document[start:end] with text."""
        notail = end is None or end >= len(self._text)
        self._text = self._text[:start] + text + self._text[end:]
        if start == 0 and notail:
            self._modified_range = True
        else:
            self._modified_range = start, start + len(text)

    def modified_range(self):
        """Return a two-tuple(start, end) describing the range that was modified.

        If the last modification did not change anything, (0, 0) is returned.

        """
        if self._modified_range is True:
            return 0, len(self._text)
        elif self._modified_range is None:
            return 0, 0
        else:
            return self._modified_range

    def _handle_undo(self, start, end, text):
        if self._in_undo == "undo":
            self._redo_stack.append((start, end, text))
        else:
            self._undo_stack.append((start, end, text))
            if self._in_undo is None:
                self._redo_stack.clear()

    def undo(self):
        """Undo the last modification."""
        if self._undo_stack:
            self._in_undo = "undo"
            start, end, text = self._undo_stack.pop()
            self[start:end] = text
            self._in_undo = None

    def redo(self):
        """Redo the last undone modification."""
        if self._redo_stack:
            self._in_undo = "redo"
            start, end, text = self._redo_stack.pop()
            self[start:end] = text
            self._in_undo = None

    def clear_undo_redo(self):
        """Clear the undo/redo stack."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def can_undo(self):
        """Return True whether undo is possible."""
        return bool(self._undo_stack)

    def can_redo(self):
        """Return True whether redo is possible."""
        return bool(self._redo_stack)


class Cursor:
    """Describes a certain range (selection) in a Document.

    You may change the start and end attributes yourself. Both must be an
    integer, end may also be None, denoting the end of the document.

    As long as you keep a reference to the Cursor, its positions are updated
    when the document changes. When text is inserted at the start position, the
    position remains the same. But when text is inserted at the end of a
    cursor, the end position moves along with the new text. E.g.:

    .. code-block:: python

        d = Document('hi there, folks!')
        c = Cursor(d, 8, 8)
        with d:
            d[8:8] = 'new text'
        c.start, c.end --> (8, 16)

    You can also use a Cursor as key while editing a document:

    .. code-block:: python

        c = Cursor(d, 8, 8)
        with d:
            d[c] = 'new text'

    You cannot alter the document via the Cursor.

    """
    __slots__ = "_document", "end", "start", "__weakref__"

    def __init__(self, document, start=0, end=-1):
        """Init with document. Start default to 0 and end defaults to start."""
        self._document = document
        self.start = start
        self.end = end if end != -1 else start
        document._cursors.add(self)

    def __repr__(self):
        key = [self.start]
        if self.start != self.end:
            key.append(self.end or "")
        key = ":".join(map(format, key))
        text = self.text()
        if len(text) > 30:
            text = text[:28] + "..."
        return "<{} [{}] {}>".format(type(self).__name__, key, repr(text))

    def document(self):
        return self._document

    def text(self):
        """Return the selected text, if any."""
        return self._document[self]

    def select(self, start, end=-1):
        """Change start and end in one go. End defaults to start."""
        self.start = start
        self.end = start if end == -1 else end

    def lstrip(self, chars=None):
        """Move start to the right, like Python's lstrip() string method."""
        text = self.text()
        if text:
            offset = len(text) - len(text.lstrip(chars))
            self.start += offset

    def rstrip(self, chars=None):
        """Move end to the left, like Python's lstrip() string method."""
        text = self.text()
        if text:
            offset = len(text) - len(text.rstrip(chars))
            if offset:
                if self.end is None or self.end > len(self._document):
                    self.end = len(self._document)
                self.end -= offset

    def strip(self, chars=None):
        """Strip chars from the selection, like Python's strip() method."""
        self.rstrip(chars)
        self.lstrip(chars)

