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
Transform/evaluate a tree or a stream of events.

XXX This module is in the planning phase!!

The basic idea of transformation is simple: for every Context in a tree
structure, a method of a Transform instance is called. The method has the same
name as the context's lexicon, and is called with the list of children of that
context, where sub-contexts already have been replaced with the result of
that context's lexicon's transformation method.
So a Transform class can closely mimic a corresponding Language class.

The actual task of transformation (evaluation) is performed by a Transformer.
The Transformer has infrastructure to choose the Transform class based on the
current Language.

Using the :meth:`~Transformer.add_transform` method, you can assign a Transform
instance to a Language class.

TODO: it would be nice to be able to specify the Transform for another Language
inside a Transform, just like a lexicon can target a lexicon from a different
language. But I'm not yet sure how it would be specified.




"""

import collections
import functools
import sys

import parce.lexer


class Item:
    """An Item wraps any object returned by a transform method.

    It has two readonly attributes, ``lexicon`` and ``obj``. The ``lexicon``
    is the lexicon that created the items a transform method is called with. To
    be able to easily distinguish an Item from a Token, a fixed readonly class
    attribute ``is_token`` exists, set to False.

    """
    __slots__ = ('lexicon', 'obj')
    is_token = False

    def __init__(self, lexicon, obj):
        self.lexicon = lexicon
        self.obj = obj


class Transform:
    """This is the base class for a transform class.

    Currently it has no special behaviour, but that might change in the future.

    A Transform class must have a method for every Lexicon the corresponding
    Language class has.

    """



class Transformer:
    """Evaluate a tree.

    For every context, the transformer calls the corresponding method of the
    transformer with the contents of that context, where sub-contexts are
    already replaced with the transformed result.

    """
    def __init__(self):
        self._transforms = {}

    def transform_text(self, root_lexicon, text, pos=0):
        """Directly create an evaluated object from text using root_lexicon.

        The transform methods get intermediate tokens, but *no* tree is built
        and the tokens don't have a parent.

        """
        from parce.tree import make_tokens  # local lookup is faster

        curlang = root_lexicon.language
        transform = self.get_transform(curlang)

        items = []
        stack = [(root_lexicon, items)]
        events = parce.lexer.Lexer([root_lexicon]).events(text, pos)
        lexicon = root_lexicon

        def get_object_item(items):
            """Get the object item, may update curlang and transform variables."""
            nonlocal curlang, transform
            if curlang is not lexicon.language:
                curlang = lexicon.language
                transform = self.get_transform(curlang)
            name = lexicon.name
            try:
                meth = getattr(transform, name)
            except AttributeError:
                return Item(lexicon, None)
            else:
                return Item(lexicon, meth(items))

        for e in events:
            if e.target:
                for _ in range(e.target.pop, 0):
                    item = get_object_item(items)
                    lexicon, items = stack.pop()
                    items.append(item)
                for l in e.target.push:
                    stack.append((lexicon, items))
                    items = []
                    lexicon = l
            items.extend(make_tokens(e))

        # unwind
        while True:
            item = get_object_item(items)
            if not stack:
                return item.obj
            lexicon, items = stack.pop()
            items.append(item)

    def transform_tree(self, tree):
        """Evaluate a tree structure."""
        try:
            return tree.cached
        except AttributeError:
            pass

        curlang = tree.lexicon.language
        transform = self.get_transform(curlang)

        stack = []
        node, items, i = tree, [], 0
        while True:
            for i in range(i, len(node)):
                n = node[i]
                if n.is_token:
                    items.append(n)
                else:
                    # a context; do we have a method for it?
                    if curlang is not n.lexicon.language:
                        curlang = n.lexicon.language
                        transform = self.get_transform(curlang)
                    name = n.lexicon.name
                    meth = getattr(transform, name, None)
                    # don't bother going in this context is there is no method
                    if meth:
                        try:
                            items.append(Item(n.lexicon, n.cached))
                        except AttributeError:
                            stack.append((items, i + 1))
                            node, items, i = n, [], 0
                            break
            else:
                if curlang is not node.lexicon.language:
                    curlang = node.lexicon.language
                    transform = self.get_transform(curlang)
                name = node.lexicon.name
                meth = getattr(transform, name, None)
                obj = meth(items) if meth else None
                print(obj, bool(meth))
                # caching the obj on the node can be enabled as soon as tree.Node
                # (or tree.Context) supports it
                #node.cached = obj
                if stack:
                    items, i = stack.pop()
                    items.append(Item(node.lexicon, obj))
                    node = node.parent
                else:
                    break
        return obj

    def get_transform(self, language):
        """Return a Transform class instance for the specified language."""
        try:
            tf = self._transforms[language]
        except KeyError:
            tf = self._transforms[language] = self.find_transform(language)
        return tf

    def add_transform(self, language, transform):
        """Add a Transform instance for the specified language."""
        self._transforms[language] = transform

    def find_transform(self, language):
        """If no Transform was added, try to find a predefined one.

        This is done by looking for a Transform subclass in the language's
        module, with the same name as the language with "Transform" appended.
        So for a language class named "Css", this method tries to find a Transform
        in the same module with the name "CssTransform".

        """
        module = sys.modules[language.__module__]
        tfname = language.__name__ + "Transform"
        tf = getattr(module, tfname, None)
        return tf() if issubclass(tf, Transform) else None





def transform_tree(tree, transform=None):
    """TEMP Convenience function that transforms tree using Transform."""
    t = Transformer()
    if transform:
        t.add_transform(tree.lexicon.language, transform)
    return t.transform_tree(tree)


def transform_text(root_lexicon, text, transform=None, pos=0):
    """TEMP Convenience function that transforms text directly using Transform."""
    t = Transformer()
    if transform:
        t.add_transform(root_lexicon.language, transform)
    return t.transform_text(root_lexicon, text, pos)


def validate_transform(transform, language):
    """Check whether the Transform has a method for every lexicon.

    Prints the missing names to the screen.

    """
    from parce import introspect
    for lexicon in introspect.lexicons(language):
        if not getattr(transform, lexicon.name, None):
            print("Missing transform method for lexicon:", lexicon.name)


