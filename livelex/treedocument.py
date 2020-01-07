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
A Document mixin that keeps all text tokenized.

When the text is modified, retokenizes only the modified part.
"""


from livelex.tree import Context, TreeBuilder


class TreeDocumentMixin:
    """Encapsulates a full tokenized text string.

    Combine this class with a subclass of AbstractDocument (see document.py).

    Everytime the text is modified, only the modified part is retokenized. If
    that changes the lexicon in which the last part (after the modified part)
    starts, that part is also retokenized, until the state (the list of active
    lexicons) matches the state of existing tokens.

    """
    def __init__(self, root_lexicon=None):
        self._modified_range = 0, 0
        self._tree = Context(root_lexicon, None)
        self._builder = TreeBuilder()

    def root(self):
        """Return the root Context of the tree."""
        return self._tree

    def root_lexicon(self):
        """Return the currently set root lexicon."""
        return self._tree.lexicon

    def set_root_lexicon(self, root_lexicon):
        """Set the root lexicon to use to tokenize the text."""
        if root_lexicon is not self._tree.lexicon:
            self._tree.lexicon = root_lexicon
            self._tokenize_full()
        else:
            self.set_modified_range(0, 0)

    def tree_builder(self):
        """Return the tree builder. By default an instance of TreeBuilder."""
        return self._builder

    def set_tree_builder(self, builder):
        """Set a different tree builder. Normally not needed. Does not reparse."""
        self._builder = builder

    def open_lexicons(self):
        """Return the list of lexicons that were left open at the end of the text.

        The root lexicon is not included; if parsing ended in the root lexicon,
        this list is empty, and the text can be considered "complete."

        """
        return self._builder.lexicons

    def _tokenize_full(self):
        """Re-tokenize the whole document. Called if the root lexicon is changed."""
        self._tree.clear()
        if self._tree.lexicon:
            self._builder.build(self._tree, self.text())
            self.set_modified_range(0, len(self))
        else:
            self.set_modified_range(0, 0)

    def modified_range(self):
        """Return a two-tuple(start, end) describing the range that was re-tokenized."""
        return self._modified_range

    def set_modified_range(self, start, end):
        """Set the modified range.

        Called by _tokenize_full() and contents_changed().
        You can override this method if you want additional handling of the
        modified range.

        """
        self._modified_range = start, end

    def modified_tokens(self):
        """Yield all the tokens that were changed in the last update."""
        start, end = self.modified_range()
        if start < end:
            return self.tokens(start, end)

    def tokens(self, start=0, end=None):
        """Yield all tokens from start to end if given."""
        t = self._tree.find_token(start) if start else None
        gen = t.forward_including() if t else self._tree.tokens()
        if end is None or end >= len(self):
            yield from gen
        else:
            for t in gen:
                if t.pos >= end:
                    break
                yield t

    def contents_changed(self, start, removed, added):
        """Called after modification of the text, retokenizes the modified part."""
        if self._tree.lexicon:
            self._builder.rebuild(self._tree, self.text(), start, removed, added)
            self.set_modified_range(self._builder.start, self._builder.end)
        else:
            self.set_modified_range(start, start + added)

