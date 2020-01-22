# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
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


import parce.treebuilder


class TreeDocumentMixin:
    """Encapsulates a full tokenized text string.

    Combine this class with a subclass of AbstractDocument (see document.py).

    Everytime the text is modified, only the modified part is retokenized. If
    that changes the lexicon in which the last part (after the modified part)
    starts, that part is also retokenized, until the state (the list of active
    lexicons) matches the state of existing tokens.

    """

    def __init__(self, builder):
        """Initialize with a BackgroundTreeBuilder instance, which is doing the work."""
        self._builder = builder
        builder.add_build_updated_callback(self.updated)

    def get_root(self, wait=False, callback=None, args=None, kwargs=None):
        """Get the root element of the completed tree.

        If wait is True, this call blocks until tokenizing is done, and the
        full tree is returned. If wait is False, None is returned if the tree
        is still busy being built.

        If a callback is given and tokenizing is still busy, that callback is
        called once when tokenizing is ready. If given, args and kwargs are the
        arguments the callback is called with, defaulting to () and {},
        respectively.

        Note that, for the lifetime of a Document, the root element is always
        the same. But using this method you can be sure that you are dealing
        with a complete and fully intact tree.

        """
        return self._builder.get_root(wait, callback, args, kwargs)

    def root_lexicon(self):
        """Return the currently set root lexicon."""
        c = self._builder.changes
        if c and c.root_lexicon != False:
            return c.root_lexicon
        return self._builder.root.lexicon

    def set_root_lexicon(self, root_lexicon):
        """Set the root lexicon to use to tokenize the text."""
        if root_lexicon != self.root_lexicon():
            with self._builder.change() as c:
                c.change_root_lexicon(self.text(), root_lexicon)

    def open_lexicons(self):
        """Return the list of lexicons that were left open at the end of the text.

        The root lexicon is not included; if parsing ended in the root lexicon,
        this list is empty, and the text can be considered "complete."

        """
        return self._builder.lexicons

    def modified_range(self):
        """Return a two-tuple(start, end) describing the range that was re-tokenized."""
        b = self._builder
        return b.start, b.end

    def contents_changed(self, start, removed, added):
        """Called after modification of the text, retokenizes the modified part."""
        with self._builder.change() as c:
            c.change_contents(self.text(), start, removed, added)

    def updated(self, start, end):
        """Called when the document is fully tokenized.

        The `start` and `end` arguments denote the region that was tokenized.
        The same values can be found using the modified_range() method.

        """
        pass

