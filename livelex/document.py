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


import itertools
import re
import weakref


from . import util


class AbstractDocument:
    """Base class for a Document.

    To make a Document work, you should at least implement:

        text()
        _update_contents()

    The method text() should simply return the entire text string.

    The method _update_contents() should read the (start, end, text) tuples
    from the list in self._changes, which is already sorted. These changes
    will never overlap. All start/end positions refer to the original state
    of the text.

    For efficiency reasons, you might want to reimplement:

        set_text()
        __len__()
        _get_contents() (called by __getitem__)

    """
    def __init__(self):
        self._cursors = weakref.WeakSet()
        self._edit_context = 0
        self._changes = []

    def text(self):
        """Should return the text."""
        raise NotImplementedError

    def set_text(self, text):
        """Set the text."""
        assert self._edit_context == 0, "can't use set_text() in edit context."
        self[:] = text

    def __repr__(self):
        text = util.abbreviate_repr(self[:31])
        return "<{} {}>".format(type(self).__name__, text)

    def __str__(self):
        return self.text()

    def __format__(self, formatstr):
        return format(self.text(), formatstr)

    def __len__(self):
        return len(self.text())

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
            self._apply_changes()

    def __setitem__(self, key, text):
        start, end = self._parse_key(key)
        if ((text or start != end) and
            (end - start != len(text) or self[start:end] != text)):
            self._changes.append((start, end, text))
            if not self._edit_context:
                self._apply_changes()

    def __delitem__(self, key):
        self[key] = ""

    def __getitem__(self, key):
        start, end = self._parse_key(key)
        if start == end:
            return ""
        elif start == 0 and end == len(self):
            return self.text()
        return self._get_contents(start, end)

    def _parse_key(self, key):
        """Get start and end values from key. Called by __[gs]etitem__."""
        total = len(self)
        if isinstance(key, slice):
            start = key.start or 0
            end = key.stop
        elif isinstance(key, Cursor):
            start = key.start
            end = key.end
        else:
            # single integer
            if key < 0:
                key += total
            if 0 <= key < total:
                return key, key + 1
            raise IndexError("index out of range")
        if start is None or start < -total:
            start = 0
        elif start < 0:
            start += total
        elif start > total:
            start = total
        if end is None or end > total:
            end = total
        elif end < -total:
            end = 0
        elif end < 0:
            end += total
        if end < start:
            end = start
        return start, end

    def _get_contents(self, start, end):
        """Return the selected range of the text.

        Called by __getitem__(), only if a fragment was requested.

        """
        return self.text()[start:end]

    def _apply_changes(self):
        """Apply the changes and update the positions of the cursors."""
        if self._changes:
            self._changes.sort()
            # check for overlaps, find the region
            head = old = self._changes[0][0]
            added = 0
            for start, end, text in self._changes:
                if start < old:
                    raise RuntimeError("overlapping changes: {}".format(self._changes))
                added += start - old + len(text)
                old = end
            self._update_cursors()
            self._update_contents()
            self._changes.clear()
            self.contents_changed(head, end - head, added)

    def _update_cursors(self):
        """Update the positions of the cursors."""
        i = 0
        cursors = sorted(self._cursors, key = lambda c: c.start)
        for start, end, text in self._changes:
            for c in cursors[i:]:
                ahead = c.start > start
                if ahead:
                    if end >= c.start:
                        c.start = start
                    else:
                        c.start += start + len(text) - end
                if c.end is not None and c.end >= start:
                    if end >= c.end:
                        c.end = start + len(text)
                    else:
                        c.end += start + len(text) - end
                elif not ahead:
                    i += 1  # don't consider this cursor any more

    def _update_contents(self):
        """Should apply the changes (in self._changes) to the text."""
        raise NotImplementedError

    def insert(self, pos, text):
        """Insert text at pos."""
        if text:
            self[pos:pos] = text

    def replace(self, old, new, start=0, end=None):
        """Replace occurrences of old with new in region start->end."""
        if old == new:
            return
        text = self[start:end]
        length = len(old)
        with self:
            pos = text.find(old)
            while pos >= 0:
                self[start+pos:start+pos+length] = new
                pos = text.find(old, pos + 1)

    def re_sub(self, pattern, replacement, start=0, end=None, count=0, flags=0):
        """Replaces regular expression matches of pattern with replacement.

        Backreferences are allowed. The region can be set with start and end.
        If count > 0, specifies the maximum number of occurrences to be
        replaced.

        """
        text = self[start:end]
        with self:
            for i, m in enumerate(re.finditer(pattern, text, flags), 1):
                self[m.start():m.end()] = m.expand(replacement)
                if i == count:
                    break

    def contents_changed(self, position, removed, added):
        """Called by _apply(). The default implementation does nothing."""
        pass


class Document(AbstractDocument):
    """A basic Document with undo and modified status.

    This Document implements AbstractDocument by holding the text in a hidden
    _text attribute. It also adds support for undo/redo and has a modified()
    state.

    A Document is like a mutable string. E.g.:

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
    undo_redo_enabled = True

    def __init__(self, text=""):
        super().__init__()
        self._text = text
        self._modified = False
        self._undo_stack = []
        self._redo_stack = []
        self._in_undo = None

    def modified(self):
        """Return whether the text was modified."""
        return self._modified

    def set_modified(self, modified):
        """Sets whether the text is modified, happens automatically normally."""
        self._modified = modified
        if not modified and not self._in_undo:
            self._set_all_undo_redo_modified()

    def text(self):
        """Return all text."""
        return self._text

    def _update_contents(self):
        """Apply the changes to the text."""
        result = []
        head = tail = self._changes[0][0]
        for start, end, text in self._changes:
            if start > tail:
                result.append(self._text[tail:start])
            if text:
                result.append(text)
            tail = end
        text = "".join(result)
        if self.undo_redo_enabled:
            # store start, end, and text needed to undo this change
            self._handle_undo(head, head + len(text), self._text[head:tail])
        self._text = self._text[:head] + text + self._text[tail:]
        if not self._in_undo:
            self.set_modified(True) # othw this is handled by undo/redo

    def _handle_undo(self, start, end, text):
        """Store start, end, and text needed to reconstruct the previous state."""
        if self._in_undo == "undo":
            self._redo_stack.append([start, end, text, self.modified()])
        else:
            self._undo_stack.append([start, end, text, self.modified()])
            if self._in_undo != "redo":
                self._redo_stack.clear()

    def _set_all_undo_redo_modified(self):
        """Called on set_modified(False). Set all undo/redo state to modified."""
        for undo in itertools.chain(self._undo_stack, self._redo_stack):
            undo[3] = True

    def undo(self):
        """Undo the last modification."""
        assert self._edit_context == 0, "can't undo while in edit context"
        if self._undo_stack:
            self._in_undo = "undo"
            start, end, text, modified = self._undo_stack.pop()
            self[start:end] = text
            self.set_modified(modified)
            self._in_undo = None

    def redo(self):
        """Redo the last undone modification."""
        assert self._edit_context == 0, "can't redo while in edit context"
        if self._redo_stack:
            self._in_undo = "redo"
            start, end, text, modified = self._redo_stack.pop()
            self[start:end] = text
            self.set_modified(modified)
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

    def select_all(self):
        """Set start to 0 and end to None; selecting all text."""
        self.start = 0
        self.end = None

    def select_none(self):
        """Set end to start."""
        self.end = self.start

    def has_selection(self):
        """Return True if text is selected."""
        end = len(self._document) if self.end is None else self.end
        return self.start < end

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

