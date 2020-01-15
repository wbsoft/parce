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
This module implements a Document encapsulating a QTextDocument.
"""

import sys
import weakref

from PyQt5.QtCore import pyqtSignal,QEventLoop, QObject, Qt, QThread
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QTextDocument, QTextLayout

import livelex
from livelex import util
from livelex.treebuilder import BackgroundTreeBuilder
from livelex.treedocument import TreeDocumentMixin
from livelex.document import AbstractDocument


class Job(QThread):
    def __init__(self, builder):
        super().__init__()
        self.builder = builder

    def run(self):
        self.builder.process_changes()


class QTreeBuilder(QObject, BackgroundTreeBuilder):
    """A TreeBuilder that uses Qt signals instead of callbacks."""
    updated = pyqtSignal(int, int)  # emitted when one full run finished
    finished = pyqtSignal()         # emitted when no more changes left

    def __init__(self, root_lexicon=None):
        QObject.__init__(self)
        BackgroundTreeBuilder.__init__(self, root_lexicon)

    def start_processing(self):
        """Start a background job if needed."""
        if not self.job:
            j = self.job = Job(self)
            j.finished.connect(self.finish_processing)
            j.start()

    def finish_processing(self):
        """Called when the background thread ends."""
        super().finish_processing()
        self.finished.emit()

    def build_updated(self):
        """Reimplemented to emit the updated() signal."""
        super().build_updated()
        self.updated.emit(self.start, self.end)

    def wait(self):
        """Wait for completion if a background job is running."""
        job = self.job
        if job and job.isRunning():
            # we can't simply job.wait() because signals that are executed
            # in the main thread would then deadlock.
            loop = QEventLoop()
            job.finished.connect(loop.quit)
            loop.exec_()


class QtDocument(TreeDocumentMixin, AbstractDocument):
    """QtDocument implements a Document encapsulating a QTextDocument.

    Use either QtDocument(doc) or QtDocument.instance(doc), where doc is a
    QTextDocument instance.

    In the latter form, the same instance is returned, if there already was
    a Document created.

    """
    @classmethod
    def instance(cls, document, default_root_lexicon=None):
        """Get the same instance back, creating it if necessary."""
        try:
            return cls._instances[document]
        except AttributeError:
            cls._instances = weakref.WeakKeyDictionary()
        except KeyError:
            pass
        new = cls._instances[document] = cls(document, default_root_lexicon)
        return new

    def __init__(self, document=None, root_lexicon=None):
        """Initialize with QTextDocument.

        If document is None, a new QTextDocument is created.

        """
        AbstractDocument.__init__(self)
        builder = QTreeBuilder(root_lexicon)
        TreeDocumentMixin.__init__(self, builder)
        self._document = document or QTextDocument()
        self._applying_changes = False
        # make sure we get notified when the user changes the document
        document.contentsChange.connect(self.contents_changed)
        # make sure update() is called in the GUI thread
        builder.remove_build_updated_callback(self.updated)
        builder.updated.connect(self.updated)

    def document(self):
        """Return our QTextDocument."""
        return self._document

    def text(self):
        """Reimplemented to get the text from the QTextDocument."""
        return self.document().toPlainText()

    def __len__(self):
        """Reimplemented to return the length of the text in the QTextDocument."""
        # see https://bugreports.qt.io/browse/QTBUG-4841
        return self.document().characterCount() - 1

    def _update_contents(self):
        """Apply the changes to our QTextDocument."""
        doc = self.document()
        c = QTextCursor(self.document())
        c.beginEditBlock()
        self._applying_changes = True
        for start, end, text in reversed(self._changes):
            c.setPosition(end)
            if start != end:
                c.setPosition(start, QTextCursor.KeepAnchor)
            c.insertText(text)
        c.endEditBlock()
        self._applying_changes = False

    def _get_contents(self, start, end):
        """Reimplemented to get a fragment of our text.

        This is faster than getting the whole text and using Python to slice it.

        """
        doc = self.document()
        c = QTextCursor(self.document())
        c.setPosition(end)
        c.setPosition(start, QTextCursor.KeepAnchor)
        return c.selection().toPlainText()

    def contents_changed(self, position, removed, added):
        """Overridden to prevent double call to contents_changed when changing ourselves."""
        if not self._applying_changes:
            super().contents_changed(position, removed, added)


class QtSyntaxHighlighter(QtDocument):
    """Provides syntax highlighting using livelex parsers.

    Implement get_format() and instantiate with:

        MyHighlighter.instance(qTextDocument, root_lexicon)

    """
    def updated(self, start, end):
        doc = self.document()
        block = doc.findBlock(start)
        start = pos = block.position()
        last_block = self.document().findBlock(end)
        end = last_block.position() + last_block.length() - 1
        formats = []
        for t_pos, t_end, action in util.merge_adjacent_actions(
                self._builder.root.tokens_range(start, end)):
            while t_pos >= pos + block.length():
                block.layout().setFormats(formats)
                block = block.next()
                pos = block.position()
                formats = []
            r = QTextLayout.FormatRange()
            r.format = f = self.get_format(action)
            r.start = t_pos - pos
            t_end = min(end, t_end)
            while t_end > pos + block.length():
                r.length = block.length() - r.start - 1
                formats.append(r)
                block.layout().setFormats(formats)
                block = block.next()
                pos = block.position()
                formats = []
                r = QTextLayout.FormatRange()
                r.format = f
                r.start = 0
            r.length = t_end - pos - r.start
            formats.append(r)
        block.layout().setFormats(formats)
        while block < last_block:
            block = block.next()
            block.layout().clearFormats()
        doc.markContentsDirty(start, end - start)

    def get_format(self, action):
        """Implement this method to return a QTextCharFormat for the action."""
        ### TEMP!
        from PyQt5.QtGui import QFont
        f = QTextCharFormat()
        if action in livelex.String:
            f.setForeground(Qt.red)
        elif action in livelex.Name:
            f.setForeground(Qt.blue)
        if action in livelex.Comment:
            f.setForeground(Qt.darkGray)
            f.setFontItalic(True)
        if action in livelex.Delimiter:
            f.setFontWeight(QFont.Bold)
        if action in livelex.Escape:
            f.setForeground(Qt.darkGreen)
        return f

