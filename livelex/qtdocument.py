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

from livelex.treedocument import TreeDocumentMixin
from livelex.document import AbstractDocument


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

    def __init__(self, document, root_lexicon=None):
        """Initialize with QTextDocument."""
        AbstractDocument.__init__(self)
        TreeDocumentMixin.__init__(self, root_lexicon)
        self._document = document
        self._applying_changes = False
        # make sure we get notified when the user changes the document
        document.contentsChange.connect(self.contents_changed)

    def document(self):
        """Return our QTextDocument."""
        return self._document

    def text(self):
        return self.document().toPlainText()

    def __len__(self):
        # see https://bugreports.qt.io/browse/QTBUG-4841
        return self.document().characterCount() - 1

    def _update_contents(self):
        """Apply the changes to our QTextDocument."""
        doc = self.document()
        QTextCursor = sys.modules[doc.__module__].QTextCursor
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
        """Get a fragment of our text."""
        doc = self.document()
        QTextCursor = sys.modules[doc.__module__].QTextCursor
        c = QTextCursor(self.document())
        c.setPosition(end)
        c.setPosition(start, QTextCursor.KeepAnchor)
        return c.selection().toPlainText()

    def contents_changed(self, position, removed, added):
        """Overridden to prevent double call to contents_changed when changing ourselves."""
        if not self._applying_changes:
            super().contents_changed(position, removed, added)


