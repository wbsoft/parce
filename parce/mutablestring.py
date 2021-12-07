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
The AbstractMutableString is the base of a parce Document.

It is a text string that is mutable via item and slice methods, the += operator
and some methods like ``insert()`` and ``append()``.

If you make modifications while inside a context (using the Python context
manager protocol), the modifications (that may not overlap then) are only
applied when the context exits for the last time.

"""


import collections
import reprlib


class AbstractMutableString:
    """Abstract base class of a MutableString.

    Defines the interface for interacting with the mutable string.

    The only thing to implement is where the contents are actually stored,
    which is an implementation detail. To make a mutable string object work,
    you should at least implement:

    * ``text()`` which should return the full text as a string.

    * ``_update_text(changes)`` to update the text according to the changes.
      Those changes are a sorted iterable of (start, end, text) tuples, and
      will never overlap. All start/end positions refer to the original state
      of the text.

    For efficiency reasons, you might want to reimplement:

    * ``set_text()`` to replace all text in one go

    * ``__len__()`` to get the length of the text

    * ``_get_text()`` called by ``__getitem__`` to get a slice or single
      character

    """
    def __init__(self):
        self._edit_context = 0
        self._changes = collections.defaultdict(list)

    def text(self):
        """Should return the text contents."""
        raise NotImplementedError

    def set_text(self, text):
        """Set the text contents."""
        if self._edit_context != 0:
            raise RuntimeError("can't use set_text() in edit context.")
        self[:] = text

    def __repr__(self):
        text = reprlib.repr(self.text())
        return "<{} {}>".format(type(self).__name__, text)

    def __str__(self):
        """Return the text contents."""
        return self.text()

    def __format__(self, formatstr):
        """Format our text."""
        return format(self.text(), formatstr)

    def __len__(self):
        """Return the length of the text."""
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

    def __iadd__(self, text):
        """Implement the += operator."""
        self.append(text)
        return self

    def __add__(self, text):
        """Implement the + operator. Returns a new, plain str instance."""
        return self.text() + text

    def __radd__(self, text):
        """Implement the + operator. Returns a new, plain str instance."""
        return text + self.text()

    def __setitem__(self, key, text):
        """Replace the position or slice with text."""
        start, end = self._parse_key(key)
        if ((text or start != end) and
            (end - start != len(text) or self[start:end] != text)):
            self._changes[start].append((end, text))
            if not self._edit_context:
                self._apply_changes()

    def __delitem__(self, key):
        """Delete the chracter or slice of text."""
        self[key] = ""

    def __getitem__(self, key):
        """Get a character or a slice of text."""
        start, end = self._parse_key(key)
        if start == end:
            return ""
        elif start == 0 and end == len(self):
            return self.text()
        return self._get_text(start, end)

    def _parse_key(self, key):
        """Get start and end values from key. Called by __[gs]etitem__."""
        total = len(self)
        if isinstance(key, slice):
            start, end, _ = key.indices(total)
        else:
            # single integer
            if key < 0:
                key += total
            if 0 <= key < total:
                return key, key + 1
            raise IndexError("index out of range")
        if end < start:
            end = start
        return start, end

    def _get_text(self, start, end):
        """Return the selected range of the text.

        Called by __getitem__(), only if a fragment was requested.

        """
        return self.text()[start:end]

    def _apply_changes(self):
        """(Internal.) Check, sort and apply the changes."""
        if self._changes:
            changes = list(self._get_changes())
            head = old = changes[0][0]
            added = 0
            for start, end, text in changes:
                added += start - old + len(text)
                old = end
            self._update_text(changes)
            self._changes.clear()
            self.text_changed(head, end - head, added)

    def _get_changes(self):
        """(Internal.) Yield the changes.

        Every change is a three-tuple(start, end, text).
        Overlapping changes are signalled and raise a RuntimeError.

        """
        positions = sorted(self._changes)
        end = positions[0]
        for start in positions:
            c = self._changes[start]
            text = ''.join(text for end, text in c)
            if start < end:
                raise RuntimeError("overlapping changes: {} before {}; text={}".format(start, end, reprlib.repr(text)))
            end = max(end for end, text in c)
            yield start, end, text

    def _update_text(self, changes):
        """Called to apply the changes to the text.

        The changes is a sorted list of (start, end, text) tuples.

        """
        raise NotImplementedError

    def append(self, text):
        """Append text at the end of the document."""
        self.insert(len(self), text)

    def insert(self, pos, text):
        """Insert text at pos."""
        self[pos:pos] = text

    def text_changed(self, position, removed, added):
        """Called after ``_update_text()``. The default implementation does nothing."""
        pass


class MutableString(AbstractMutableString):
    """A Mutable string, storing the string contents in an internal attribute."""
    def __init__(self, text):
        super().__init__()
        self._text = text

    def text(self):
        """Return the text."""
        return self._text

    def _update_text(self, changes):
        """Apply the changes to the text."""
        def generate_text():
            tail = 0
            for start, end, text in changes:
                if start > tail:
                    yield self._text[tail:start]
                if text:
                    yield text
                tail = end
            yield self._text[tail:]
        self._text = "".join(generate_text())


