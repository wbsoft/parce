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
A Document mixin that keeps all text tokenized.

When the text is modified, retokenizes only the modified part.
"""


import parce.treebuilder


class TreeDocumentMixin:
    """Encapsulates a full tokenized text string.

    Combine this class with a subclass of AbstractDocument (see the
    :py:mod:`document <parce.document>` module).

    Everytime the text is modified, only the modified part is retokenized. If
    that changes the lexicon in which the last part (after the modified part)
    starts, that part is also retokenized, until the state (the list of active
    lexicons) matches the state of existing tokens.

    """

    def __init__(self, builder):
        """Initialize with a TreeBuilder instance, which is doing the work."""
        self._builder = builder

    def builder(self):
        """Return the TreeBuilder we were instantiated with."""
        return self._builder

    def get_root(self, wait=False, callback=None, args=(), kwargs={}):
        """Get the root element of the completed tree.

        If wait is True, this call blocks until tokenizing is done, and the
        full tree is returned. If wait is False, None is returned if the tree
        is still busy being built.

        If a callback is given and a BackgroundTreeBuilder was used and
        tokenizing is still busy, that callback is called once when tokenizing
        is ready. If given, args and kwargs are the arguments the callback is
        called with, defaulting to () and {}, respectively.

        Note that, for the lifetime of a Document, the root element is always
        the same. But using this method you can be sure that you are dealing
        with a complete and fully intact tree.

        """
        return self.builder().get_root(wait, callback, args, kwargs)

    def root_lexicon(self):
        """Return the currently set root lexicon."""
        return self.builder().root.lexicon

    def set_root_lexicon(self, root_lexicon):
        """Set the root lexicon to use to tokenize the text."""
        self.builder().rebuild(self.text(), root_lexicon)

    def open_lexicons(self):
        """Return the list of lexicons that were left open at the end of the text.

        The root lexicon is not included; if parsing ended in the root lexicon,
        this list is empty, and the text can be considered "complete."

        """
        return self.builder().lexicons

    def modified_range(self):
        """Return a two-tuple(start, end) describing the range that was re-tokenized."""
        b = self.builder()
        return b.start, b.end

    def contents_changed(self, start, removed, added):
        """Called after modification of the text, retokenizes the modified part."""
        self.builder().rebuild(self.text(), False, start, removed, added)
        super().contents_changed(start, removed, added)

