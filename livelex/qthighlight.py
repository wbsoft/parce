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
This module provides QSyntaxHighlighterMixin.

This class can be combined with QSyntaxHighlighter to use livelex lexing
with QSyntaxHighlighter.

You should inherit from both Qt's QSyntaxHighlighter and this 
QSyntaxHighlighterMixin, and implement the get_format() method.

This method is called with the action of every token in the current line,
and should return a QTextCharFormat, a QColor or a QFont; anything that
QSyntaxHighlighter.setFormat() allows.

For example:

    class Highlighter(livelex.qthighlight.QSyntaxHighlighterMixin, QSyntaxHighlighter):
        def get_format(self, action):
            return self.our_text_formats[action]

    h = Highlighter(qtextdocument)

The Highlighter instance has all the features of livelex.Document, to access
the tokens, etc.

This module itself does not depend on Qt.
    
"""

import sys

from .document import AbstractDocument
from .tree import TreeDocumentMixin


class QSyntaxHighlighterMixin(TreeDocumentMixin, AbstractDocument):
    def __init__(self, qtextdocument, root_lexicon=None):
        AbstractDocument.__init__(self)
        TreeDocumentMixin.__init__(self, root_lexicon)
        # find Qt without making this module depend on it ;-)
        for base in self.__class__.__mro__:
            if base.__name__ == "QSyntaxHighlighter":
                base.__init__(self, qtextdocument)
                break
        else:
            raise TypeError("Must inherit from QSyntaxHighlighter")

    def text(self):
        return self.document().toPlainText()

    def _update_contents(self):
        d = self.document()
        # get a QTextCursor without having access to Qt
        QTextCursor = sys.modules[self.document().__module__].QTextCursor
        c = QTextCursor(d)
        c.beginEditBlock()
        for start, end, text in reversed(self._changes):
            c.setPosition(end)
            c.setPosition(start, QTextCursor.KeepAnchor)
            c.insertText(text)
        c.endEditBlock()

    def highlightBlock(self, text):
        pass


