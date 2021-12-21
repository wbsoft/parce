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
Document and Cursor form the basis of handling of documents in the parce
package.

A Document contains a text string that is mutable via item and slice methods.

If you make modifications while inside a context (using the Python context
manager protocol), the modifications are only applied when the context
exits for the last time.

For tokenized documents (see :class:`parce.Document`), parce inherits from this
base class (see the :mod:`~parce.work` module).

You can use a Cursor to keep track of positions in a document. The position
(and selection) of a Cursor is adjusted when the text in the document is
changed.

You can use the various ``find_block()`` and ``blocks()`` methods to iterate
over a Document on a line-by-line basis.

"""


import contextlib
import itertools
import re
import reprlib
import weakref

from . import mutablestring
from . import util


class AbstractDocument(mutablestring.AbstractMutableString):
    """Base class for a Document.

    A Document is like a mutable string, but understands :class:`Cursor` and
    :class:`Block`.

    """

    block_separator = '\n'  #: separator to use for block boundaries (newline)

    def __init__(self):
        mutablestring.AbstractMutableString.__init__(self)
        self._cursors = weakref.WeakSet()
        self._revision = 0

    def _parse_key(self, key):
        """Get start and end values from key. Called by __[gs]etitem__."""
        if isinstance(key, AbstractTextRange):
            key = slice(key.pos, key.end)
        return super()._parse_key(key)

    def _update_cursors(self, changes):
        """Update the positions of the cursors."""
        i = 0
        cursors = sorted(self._cursors, key = lambda c: c.pos)
        for start, end, text in changes:
            for c in cursors[i:]:
                ahead = c.pos > start
                if ahead:
                    if end >= c.pos:
                        c.pos = start
                    else:
                        c.pos += start + len(text) - end
                if c.end is not None and c.end >= start:
                    if end >= c.end:
                        c.end = start + len(text)
                    else:
                        c.end += start + len(text) - end
                elif not ahead:
                    i += 1  # don't consider this cursor any more

    def _update_text(self, changes):
        """Apply the changes to the text, reimplemented here to also update the Cursor positions."""
        self._update_cursors(changes)
        self._revision += 1

    def revision(self):
        """Return the revision number.

        This number is incremented by one on every document change.

        """
        return self._revision

    def find_start_of_block(self, position):
        """Find the start of the block the position is in."""
        sep = self.block_separator
        pos = self.text().rfind(sep, 0, position)
        return 0 if pos == -1 else pos + len(sep)

    def find_end_of_block(self, position):
        """Find the end of the block the position is in."""
        pos = self.text().find(self.block_separator, position)
        return len(self) if pos == -1 else pos

    def find_block(self, position):
        """Return a Block representing the text line (block) at position."""
        pos = self.find_start_of_block(position)
        end = self.find_end_of_block(pos)
        return Block(self, pos, end)

    def blocks(self, start=0, end=None):
        """Yield Blocks, starting at position start, ending at end.

        Start defaults to 0, end to None, which means iterate to the last block.

        """
        block = self.find_block(start)
        if end is None:
            while block:
                yield block
                block = block.next_block()
        else:
            while True:
                yield block
                block = block.next_block()
                if not block or block.pos >= end:
                    break

    def replace(self, old, new, start=0, end=None, count=0):
        """Replace occurrences of old with new in region start->end.

        If count > 0, specifies the maximum number of occurrences to be
        replaced.

        """
        if old == new:
            return
        text = self[start:end]
        length = len(old)
        with self:
            pos = text.find(old)
            while pos >= 0:
                self[start+pos:start+pos+length] = new
                pos = text.find(old, pos + length)
                count -= 1
                if count == 0:
                    break

    def re_sub(self, pattern, replacement, start=0, end=None, count=0, re_flags=0):
        """Replace regular expression matches of pattern with replacement.

        The pattern may be a string or a compiled regexp pattern object.
        Backreferences are allowed. The region can be set with start and end.
        If count > 0, specifies the maximum number of occurrences to be
        replaced.

        The replacement argument can also be a funtion, which is then called
        with the match object and should return the replacement string.

        With start and end the range can be specified, and, if the pattern was
        a string it is compiled to a regular expression object using the
        speficied re_flags.

        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern, re_flags)
        if not callable(replacement):
            replacement = (lambda repl: lambda m: m.expand(repl))(replacement)
        text = self[start:end]
        with self:
            for i, m in enumerate(pattern.finditer(text), 1):
                self[start+m.start():start+m.end()] = replacement(m)
                if i == count:
                    break

    def trim(self, start=0, end=None):
        """Remove trialing whitespace in the specified region."""
        self.re_sub(r'[ \t]+$', '', start, end, re_flags=re.MULTILINE)

    def translate(self, mapping, start=0, end=None, count=0, whole_words=False):
        """Replace every occurrence of a key in mapping with its value.

        If whole_words is True, only match the keys at word boundaries.

        """
        from . import regex
        expr = regex.words2regexp(mapping.keys())
        if whole_words:
            expr = r"\b({})\b".format(expr)
        repl = lambda m: mapping[m.group()]
        self.re_sub(expr, repl, start, end, count)

    def text_changed(self, position, removed, added):
        """Called after ``_update_text()``.

        The default implementation does nothing.

        """
        pass


class Document(AbstractDocument, mutablestring.MutableString, util.Observable):
    """A basic Document with undo and modified status.

    This Document implements :class:`AbstractDocument` by holding the text in a
    hidden _text attribute. It adds support for undo/redo and has a
    :meth:`modified` state.

    It also inherits from :class:`~parce.util.Observable` and emits the
    following events:

    ``"text_change" (position, removed, added)``:
        emitted with ``position``, ``removed``, ``added`` arguments whenever the
        text changes

    ``"text_changed"``:
        emitted directly afther the previous event, but without arguments

    ``"modification_changed" (bool)``:
        emitted when the :meth:`modified` state changes; True means the document
        was modified

    ``"undo_available" (bool)``:
        emitted when the availability of :meth:`undo` changes

    ``"redo_available" (bool)``:
        emitted when the availability of :meth:`redo` changes.

    """
    _in_undo = util.Switch()
    _in_redo = util.Switch()

    undo_redo_enabled = True

    def __init__(self, text=""):
        AbstractDocument.__init__(self)
        mutablestring.MutableString.__init__(self, text)
        util.Observable.__init__(self)
        self._modified = False
        self._undo_stack = []
        self._redo_stack = []

    def modified(self):
        """Return whether the text was modified."""
        return self._modified

    def set_modified(self, modified):
        """Sets whether the text is modified, happens automatically normally."""
        changed = modified != self._modified
        self._modified = modified
        if not modified and not (self._in_undo or self._in_redo):
            self._set_all_undo_redo_modified()
        if changed:
            self.emit("modification_changed", modified)

    def _update_text(self, changes):
        """Apply the changes to the text."""
        with self._check_undo_state():
            if self.undo_redo_enabled:
                self._store_undo(self._reverse_changes(changes))
            AbstractDocument._update_text(self, changes)
            mutablestring.MutableString._update_text(self, changes)
        if not (self._in_undo or self._in_redo):
            self.set_modified(True) # othw this is handled by undo/redo

    def _reverse_changes(self, changes):
        """Return the changes that would be needed to undo the given list of changes."""
        def reverse_changes():
            head = 0
            current_text = self.text()
            for start, end, text in changes:
                head += start
                yield (head, head + len(text), current_text[start:end])
                head += len(text) - end
        return list(reverse_changes())

    def _store_undo(self, changes):
        """Store changes needed to reconstruct the previous state."""
        state = [changes, self.modified()]
        if self._in_undo:
            self._redo_stack.append(state)
        else:
            self._undo_stack.append(state)
            if not self._in_redo:
                self._redo_stack.clear()

    def _apply_undo_redo(self, stack):
        """Apply changes from the specified stack (undo or redo)."""
        if self._edit_context > 0:
            raise RuntimeError("can't undo or redo while in edit context")
        if stack:
            changes, modified = stack.pop()
            with self:
                for start, end, text in changes:
                    self[start:end] = text
            self.set_modified(modified)

    @contextlib.contextmanager
    def _check_undo_state(self):
        """Context manager to perform operations that alter the undo / redo stack.

        Emits "undo_available" and "redo_available" when they change.

        """
        can_undo = self.can_undo()
        can_redo = self.can_redo()
        try:
            yield
        finally:
            new_can_undo = self.can_undo()
            new_can_redo = self.can_redo()
            if new_can_undo != can_undo:
                self.emit("undo_available", new_can_undo)
            if new_can_redo != can_redo:
                self.emit("redo_available", new_can_redo)

    def _set_all_undo_redo_modified(self):
        """Called on set_modified(False). Set all undo/redo state to modified."""
        for undo in itertools.chain(self._undo_stack, self._redo_stack):
            undo[1] = True

    def undo(self):
        """Undo the last modification."""
        with self._in_undo:
            self._apply_undo_redo(self._undo_stack)

    def redo(self):
        """Redo the last undone modification."""
        with self._in_redo:
            self._apply_undo_redo(self._redo_stack)

    def clear_undo_redo(self):
        """Clear the undo/redo stack."""
        with self._check_undo_state():
            self._undo_stack.clear()
            self._redo_stack.clear()

    def can_undo(self):
        """Return True if undo is possible."""
        return bool(self._undo_stack)

    def can_redo(self):
        """Return True if redo is possible."""
        return bool(self._redo_stack)

    def text_changed(self, position, removed, added):
        """Called after ``_update_text()`` has been called.

        The default implementation emits the ``"text_change"`` and
        ``"text_changed"`` events.

        """
        self.emit("text_change", position, removed, added)
        self.emit("text_changed")


class AbstractTextRange:
    """Base class for :class:`Cursor` and :class:`Block`.

    The text range is denoted by the ``pos`` and ``end`` attributes.

    Provides the comparison operators ``==``, ``!=``, ``>``, ``<``, ``>=``,
    ``<=``, based on the ``pos`` attribute. The ranges must refer to the same
    Document.

    """
    __slots__ = ("_document", "pos", "end")
    __hash__ = object.__hash__

    def __init__(self, document, pos, end):
        self._document = document
        self.pos = pos  #: the (start) position.
        self.end = end  #: the end position (for Cursor, this may be None).

    def __repr__(self):
        key = [self.pos]
        if self.pos != self.end:
            key.append(self.end or "")
        key = ":".join(map(format, key))
        text = reprlib.repr(self.text())
        return "<{} [{}] {}>".format(type(self).__name__, key, text)

    def document(self):
        """Return our document."""
        return self._document

    def text(self):
        """Return text in this range."""
        return self.document()[self]

    def __bool__(self):
        return True

    def __eq__(self, other):
        """Return ``self.pos == other.pos and self.end == other.end``."""
        return other.document() is self.document() \
            and other.pos == self.pos \
            and other.end == self.end

    def __ne__(self, other):
        """Return ``self.pos != other.pos or self.end != other.end``."""
        return other.document() is not self.document() \
            or other.pos != self.pos \
            or other.end != self.end

    def __gt__(self, other):
        """Return ``self.pos > other.pos``."""
        return self.pos > other.pos

    def __lt__(self, other):
        """Return ``self.pos < other.pos``."""
        return self.pos < other.pos

    def __ge__(self, other):
        """Return ``self.pos >= other.pos``."""
        return self.pos >= other.pos

    def __le__(self, other):
        """Return ``self.pos <= other.pos``."""
        return self.pos <= other.pos

    def token(self):
        """Convenience method returning the :class:`~parce.tree.Token` at our pos.

        The Document must have the :class:`~.work.WorkerDocumentMixin` class
        mixed in (i.e. have the :meth:`~.work.WorkerDocumentMixin.token`
        method.

        """
        return self.document().token(self.pos)

    def tokens(self):
        """Convenience method yielding all Tokens that are in or overlap this
        text range.

        The Document must have the :class:`~.work.WorkerDocumentMixin` class
        mixed in (i.e. have the :meth:`~.work.WorkerDocumentMixin.get_root`
        method.

        """
        return self.document().get_root(True).tokens_range(self.pos, self.end)


class Cursor(AbstractTextRange):
    """Describes a certain range (selection) in a :class:`Document`.

    You may change the ``pos`` and ``end`` attributes yourself. Both must be an
    integer, end may also be None, denoting the end of the document.

    As long as you keep a reference to the Cursor, its positions are updated
    when the document changes. When text is inserted at ``pos``, the position
    remains the same. But when text is inserted at the end of a cursor, the
    ``end`` position (if not None) moves along with the new text. E.g.::

        >>> from parce.document import Document, Cursor
        >>> d = Document('hi there, folks!')
        >>> c = Cursor(d, 8, 8)
        >>> with d:
        ...     d[8:8] = 'new text'
        ...
        >>> c.pos, c.end
        (8, 16)

    You can also use a Cursor as key while editing a document::

        >>> c = Cursor(d, 8, 8)
        >>> with d:
        ...     d[c] = 'new text'

    You cannot alter the document via the Cursor. All move and select methods
    return the cursor again, so they can be chained::

        >>> c = Cursor(d).select_all()
        >>> c.pos, c.end
        (0, None)

    """
    __slots__ = ("__weakref__",)

    def __init__(self, document, pos=0, end=-1):
        """Init with document. ``pos`` defaults to 0 and ``end`` defaults to pos."""
        super().__init__(document, pos, end if end != -1 else pos)
        document._cursors.add(self)

    def block(self):
        """Return the :class:`Block` our ``pos`` is in."""
        return self.document().find_block(self.pos)

    def blocks(self):
        """Yield the Blocks from pos to end."""
        yield from self.document().blocks(self.pos, self.end)

    def move_start_of_block(self):
        """Move pos and end to the start of the current block. Returns self."""
        self.pos = self.end = self.document().find_start_of_block(self.pos)
        return self

    def move_end_of_block(self):
        """Move pos and end to the end of the current block. Returns self."""
        self.pos = self.end = self.document().find_end_of_block(self.pos)
        return self

    def select(self, pos, end=-1):
        """Change pos and end in one go. End defaults to pos. Returns self."""
        self.pos = pos
        self.end = pos if end == -1 else end
        return self

    def select_all(self):
        """Set pos to 0 and end to None; selecting all text. Returns self."""
        self.pos = 0
        self.end = None
        return self

    def select_none(self):
        """Set end to pos. Returns self."""
        self.end = self.pos
        return self

    def selection(self):
        """Return the two-tuple (pos, end) denoting the selected range.

        The ``end`` value is never None, it is set to the length of the
        document if the :attr:`end` attribute is None.

        """
        end = len(self.document()) if self.end is None else self.end
        return self.pos, end

    def has_selection(self):
        """Return True if text is selected."""
        pos, end = self.selection()
        return pos < end

    def select_start_of_block(self):
        """Moves the selection pos to the beginning of the current line.

        Returns self.

        """
        self.pos = self.document().find_start_of_block(self.pos)
        return self

    def select_end_of_block(self):
        """Moves the selection end (if not None) to the end of its line.

        Returns self.

        """
        if self.end is not None:
            self.end = self.document().find_end_of_block(self.end)
        return self

    def lstrip(self, chars=None):
        """Move pos to the right, if specified characters can be skipped.

        By default whitespace is skipped, like Python's lstrip() string method.
        Returns self.

        """
        text = self.text()
        if text:
            offset = len(text) - len(text.lstrip(chars))
            self.pos += offset
        return self

    def rstrip(self, chars=None):
        """Move end to the left, if specified characters can be skipped.

        By default whitespace is skipped, like Python's rstrip() string method.
        Returns self.

        """
        text = self.text()
        if text:
            offset = len(text) - len(text.rstrip(chars))
            if offset:
                doc_length = len(self.document())
                if self.end is None or self.end > doc_length:
                    self.end = doc_length
                self.end -= offset
        return self

    def strip(self, chars=None):
        """Adjust pos and end, like Python's strip() method. Returns self."""
        self.rstrip(chars)
        self.lstrip(chars)
        return self


class Block(AbstractTextRange):
    r"""Represents a single line (block) of text in the :class:`Document`.

    Block objects are separated by newlines in the Document, and are created
    by Document.find_block() or Cursor.block(), and the blocks() iterator of
    both Cursor and Document.

    Unlike :class:`Cursor`, Block objects do not update their position when the
    document is changed. You should use Blocks while iterating but throw them
    away after applying changes to a Document.

    Blocks can be compared: blocks originating from the same document compare
    equal when they point to the same position. You can also use the ``<``,
    ``<=``, ``>`` and ``>=`` operators.

    """
    __slots__ = ()

    def __len__(self):
        return self.end - self.pos

    def is_first(self):
        """True if this is the first block."""
        return self.pos == 0

    def is_last(self):
        """True if this is the last block."""
        return self.end >= len(self.document())

    def next_block(self):
        """The next block if available."""
        if not self.is_last():
            pos = self.end + len(self.document().block_separator)
            end = self.document().find_end_of_block(pos)
            return type(self)(self.document(), pos, end)

    def previous_block(self):
        """The previous block if available."""
        if self.pos > 0:
            end = self.pos - len(self.document().block_separator)
            pos = self.document().find_start_of_block(end)
            return type(self)(self.document(), pos, end)

    def tokens(self):
        """Convenience method returning a tuple with all Tokens that are in
        or overlap this block.

        The Document must have the :class:`~.work.WorkerDocumentMixin` class
        mixed in (i.e. have the :meth:`~.work.WorkerDocumentMixin.get_root`
        method.

        """
        return tuple(super().tokens())

