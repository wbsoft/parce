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
Transform c.q. evaluate a tree or a stream of events.

The basic idea of transformation is simple: for every Context in a tree
structure, a method of a Transform instance is called. The method has the same
name as the context's lexicon, and is called with an :class:`Items` instance
containing the list of children of that context.

Sub-contexts in that list already have been replaced with the result of that
context's lexicon's transformation method, wrapped in an :class:`Item`, so the
Items list consists of instances of either :class:`~parce.tree.Token` or
:class:Item. To make it easier to distinguish between these, the Item class has
an :attr:`~Item.is_token` class attribute, set to False.

Thus, a Transform class can closely mimic a corresponding Language class. If
you want to ignore the output of a particular lexicon, don't define a method
with that name, but set its name to ``None`` in the Transform class definition.

The actual task of transformation (evaluation) is performed by a
:class:`Transformer`. The Transformer has infrastructure to choose the
Transform class based on the current Language

Using the :meth:`~Transformer.add_transform` method, you can assign a Transform
instance to a Language class.

For example::

    from parce import root, Language, lexicon, default_action
    from parce.action import Delimiter, Number, String
    from parce.transform import Transform, transform_text

    class MyLang(Language):
        @lexicon
        def root(cls):
            yield r'\[', Delimiter, cls.list
            yield r'\d+', Number
            yield r'"', String, cls.string

        @lexicon
        def list(cls):
            yield r'\]', Delimiter, -1
            yield from cls.root

        @lexicon
        def string(cls):
            yield r'"', String, -1
            yield default_action, String


    class MyLangTransform(Transform):
        def root(self, items):
            result = []
            for i in items:
                if i.is_token:
                    if i.action is Number:
                        result.append(int(i.text))  # a Number
                else:
                    result.append(i.obj)            # a list or string
            return result

        def list(self, items):
            return self.root(items)

        def string(self, items):
            return items[0].text     # not the closing quote

    >>> transform_text(MyLang.root, '1 2 3 [4 "Q" 6] x 7 8 9')
    [1, 2, 3, [4, 'Q', 6], 7, 8, 9]

You can also transform a tree structure::

    >>> from parce.transform import transform_tree
    >>> tree = root(MyLang.root, '1 2 3 [4 "Q" 6] x 7 8 9')
    >>> tree.dump()
    <Context MyLang.root at 0-23 (8 children)>
     ├╴<Token '1' at 0:1 (Literal.Number)>
     ├╴<Token '2' at 2:3 (Literal.Number)>
     ├╴<Token '3' at 4:5 (Literal.Number)>
     ├╴<Token '[' at 6:7 (Delimiter)>
     ├╴<Context MyLang.list at 7-15 (5 children)>
     │  ├╴<Token '4' at 7:8 (Literal.Number)>
     │  ├╴<Token '"' at 9:10 (Literal.String)>
     │  ├╴<Context MyLang.string at 10-12 (2 children)>
     │  │  ├╴<Token 'Q' at 10:11 (Literal.String)>
     │  │  ╰╴<Token '"' at 11:12 (Literal.String)>
     │  ├╴<Token '6' at 13:14 (Literal.Number)>
     │  ╰╴<Token ']' at 14:15 (Delimiter)>
     ├╴<Token '7' at 18:19 (Literal.Number)>
     ├╴<Token '8' at 20:21 (Literal.Number)>
     ╰╴<Token '9' at 22:23 (Literal.Number)>
    >>> transform_tree(tree)
    [1, 2, 3, [4, 'Q', 6], 7, 8, 9]

Note that the :func:`transform_tree` gets the root lexicon from the root
element, and then automatically finds the corresponding Transform class, if you
didn't specify one yourself.

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

    @property
    def name(self):
        """The lexicon's name."""
        return self.lexicon.name

    def __repr__(self):
        return "<Item '{}' {}>".format(self.name, repr(self.obj))


class Items(list):
    """A list of Item and Token instances.

    The Transform methods are called with an instance of this class. Besides
    being a Python list, this class also has some methods that filter out items
    or tokens, etc.

    Slicing from Items returns a new Items instance, so you can slice and
    the methods still work.

    """
    __slots__ = ()

    def __getitem__(self, n):
        """Reimplemented to return an Items instance when slicing."""
        result = super().__getitem__(n)
        if isinstance(n, slice):
            return type(self)(result)
        return result

    def tokens(self, *texts):
        """Yield only the tokens.

        If one or more texts are given, only yield tokens with one of the
        texts.

        """
        if texts:
            for i in self:
                if i.is_token and i.text in texts:
                    yield i
        else:
            for i in self:
                if i.is_token:
                    yield i

    def items(self, *names):
        """Yield only the sub-items.

        If one or more names are given, only yield items that have one of the
        names.

        """
        if names:
            for i in self:
                if not i.is_token and i.name in names:
                    yield i
        else:
            for i in self:
                if not i.is_token:
                    yield i

    def action(self, *actions):
        """Yield only the tokens with one of the specified actions."""
        for i in self:
            if i.is_token and i.action in actions:
                yield i

    def in_action(self, *actions):
        """Yield only the tokens with an action that's in one of the specified
        actions.

        """
        for i in self:
            if i.is_token and any(i.action in a for a in actions):
                yield i


class Transform:
    """This is the base class for a transform class.

    Currently it has no special behaviour, but that might change in the future.

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
        if not root_lexicon:
            return  # a root lexicon can be None, but then there are no children

        from parce.tree import make_tokens  # local lookup is faster

        curlang = root_lexicon.language
        transform = self.get_transform(curlang)

        items = Items()
        stack = []
        events = parce.lexer.Lexer([root_lexicon]).events(text, pos)
        lexicon = root_lexicon

        no_object = object()                # sentinel for missing method

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
                return no_object
            else:
                return Item(lexicon, meth(items))

        for e in events:
            if e.target:
                for _ in range(e.target.pop, 0):
                    item = get_object_item(items)
                    lexicon, items = stack.pop()
                    if item is not no_object:
                        items.append(item)
                for l in e.target.push:
                    stack.append((lexicon, items))
                    items = Items()
                    lexicon = l
            items.extend(make_tokens(e))

        # unwind
        while stack:
            item = get_object_item(items)
            lexicon, items = stack.pop()
            if item is not no_object:
                items.append(item)
        item = get_object_item(items)
        return None if item is no_object else item.obj

    def transform_tree(self, tree):
        """Evaluate a tree structure."""
        if not tree.lexicon:
            return  # a root lexicon can be None, but then there are no children

        try:
            return tree.cached
        except AttributeError:
            pass

        curlang = tree.lexicon.language
        transform = self.get_transform(curlang)

        stack = []
        node, items, i = tree, Items(), 0
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
                            node, items, i = n, Items(), 0
                            break
            else:
                if curlang is not node.lexicon.language:
                    curlang = node.lexicon.language
                    transform = self.get_transform(curlang)
                name = node.lexicon.name
                meth = getattr(transform, name, None)
                obj = meth(items) if meth else None
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
        So for a language class named "Css", this method tries to find a
        Transform in the same module with the name "CssTransform".

        """
        module = sys.modules[language.__module__]
        tfname = language.__name__ + "Transform"
        tf = getattr(module, tfname, None)
        return tf() if issubclass(tf, Transform) else None


def transform_tree(tree, transform=None):
    """Convenience function that transforms tree using Transform.

    If you don't specify a Transform to use, *parce* tries to find one using
    the :meth:`Transformer.find_transform` method.

    If you want to specify multiple Transforms for different Language you
    expect in the tree you want to transform, instantiate a
    :class:`Transformer`, add the Transforms you want and call its
    :meth:`Transformer.transform_tree` method directly.

    """
    t = Transformer()
    if transform:
        t.add_transform(tree.lexicon.language, transform)
    return t.transform_tree(tree)


def transform_text(root_lexicon, text, transform=None, pos=0):
    """Convenience function that transforms text directly using Transform.

    If you don't specify a Transform to use, *parce* tries to find one using
    the :meth:`Transformer.find_transform` method.

    If you want to specify multiple Transforms for different Language you
    expect in the text you want to transform, instantiate a
    :class:`Transformer`, add the Transforms you want and call its
    :meth:`Transformer.transform_text` method directly.

    """
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


