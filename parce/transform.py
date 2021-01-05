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

This module provides the Transformer that does the work, the Transform base
class for all your transforming classes, the Item that wraps the output of
sub-contexts, the Items list type to ease iterating over the contents of a
context, and some toplevel convenience functions.

See also the documentation: :doc:`transforming`.

TODO: it would be nice to be able to specify the Transform for another Language
inside a Transform, just like a lexicon can target a lexicon from a different
language. But I'm not yet sure how it would be specified.

"""

import collections
import sys
import threading
import weakref

import parce.lexer
import parce.util


class Item(collections.namedtuple("Item", "name obj")):
    """A named tuple(name, obj) wrapping the return value of a Tranform method.

    The `name` attribute is the name of the Lexicon and transform method that
    created the object `obj`. To make it easier to distinguish an Item from a
    Token, Item has as class attribute `is_token` set to False.

    """
    __slots__ = ()
    is_token = False


class Items(list):
    """A list of Item and Token instances.

    The Transformer populates this list with all the Tokens from a Context,
    replacing nested Contexts with an Item that wraps the return value of the
    Transform method for that Context's lexicon.

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
        """Yield only the tokens, ignoring Item objects that represent
        sub-contexts.

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
        """Yield only the sub-Items, ignoring any Token instances.

        If one or more names are given, only yield items that have one of the
        names.

        Because you know only Item instances and not Tokens will be yielded,
        you can unpack name and object in one go::

            for name, obj in items.items():
                ...

        """
        if names:
            for i in self:
                if not i.is_token and i.name in names:
                    yield i
        else:
            for i in self:
                if not i.is_token:
                    yield i

    def grouped_objects(self, *names):
        """Yield objects in groups, specified by the names.

        The order remains the same. For example, when you have a stream of `key`
        and `value` Item objects, calling `grouped_objects('key', 'value')`
        yields the objects in (key, value) pairs.

        For missing objects, None is yielded. Tokens are ignored.

        """
        # a mapping from name to position in the names list
        index = dict((name, i) for i, name in enumerate(names))

        result = [None] * len(names)
        lastindex = -1
        for name, obj in self.items(*names):
            if index[name] <= lastindex:
                yield result
                result = [None] * len(names)
            lastindex = index[name]
            result[lastindex] = obj
        if lastindex > -1:
            yield result


class Transform:
    """This is the base class for a transform class.

    Currently it has no special behaviour, but that might change in the future.

    """


class Transformer(parce.util.Observable):
    """Evaluate a tree.

    For every context, the transformer calls the corresponding method of the
    Transform instance with the contents of that context, where sub-contexts
    are already replaced with the transformed result.

    When a tree is transformed, Transformer emits the following events you
    can connect to:

    ``"started"``:
        emitted when transforming has started, with the tree as argument

    ``"updated"``:
        emitted when the transformation has fully completed, with the tree
        and the resulting transformation

    ``"finished"``:
        always emitted when transformation has quit, also when it was
        inrerrupted due to tree modification while transforming was busy;
        with the tree as argument

    """
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()   # for instantiating Transforms
        self._transforms = {}
        self._cache = weakref.WeakKeyDictionary()
        self._interrupt = weakref.WeakKeyDictionary()

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
            meth = getattr(transform, name, None)
            return Item(name, meth(items)) if meth else no_object

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
        self._interrupt[tree] = False

        if not tree.lexicon:
            return  # a root lexicon can be None, but then there are no children

        curlang = tree.lexicon.language
        transform = self.get_transform(curlang)

        stack = []
        node, items, i = tree, Items(), 0
        while not self._interrupt[tree]:
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
                            items.append(Item(name, self._cache[n]))
                        except KeyError:
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
                if stack:
                    self._cache[node] = obj
                    items, i = stack.pop()
                    items.append(Item(name, obj))
                    node = node.parent
                else:
                    break
        return obj

    def build(self, tree):
        """Called when a tree needs to be transformed.

        The default implementation iterates over :meth:`process` to perform
        the job. You can reimplement this method to perform the job
        in a background thread.

        """
        for stage in self.process(tree):
            pass

    def process(self, tree):
        """Transform the tree and emit events.

        Updates the cached result if the transformation was not interrupted.
        This method returns a generator; exhaust it fully to perform the
        transformation.

        """
        self.emit("started", tree)
        yield "build"
        result = self.transform_tree(tree)
        yield "replace"
        if not self._interrupt[tree]:
            self._cache[tree] = result
            self.emit("updated", tree, result)
        del self._interrupt[tree]
        self.emit("finished", tree)
        yield "done"

    def interrupt(self, tree):
        """Tell the Transformer to stop transforming the specified tree."""
        self._interrupt[tree] = True

    def result(self, tree):
        """Get the result of the transformed tree.

        Returns None if no result was yet created. Although this method
        is intended to return the transformed result for the root node,
        it can be used to get the intermediate result for any Context node.

        """
        return self._cache.get(tree)

    def invalidate_node(self, node):
        """Remove the transform results for this node and its ancestors
        from our cache.

        Does not throw away the result for the root context.

        """
        while node.parent:
            del self._cache[node]
            node = node.parent

    def connect_treebuilder(self, builder):
        """Connect to the events of the TreeBuilder.

        This causes the Transformer to automatically update the transformation
        when the tree builder updates the tree.

        """
        builder.connect("replace", self.slot_replace, prepend_self=True)
        builder.connect("finished", self.slot_update, prepend_self=True, priority=-1000)
        builder.connect("invalidate", self.invalidate_node)

    def disconnect_treebuilder(self, builder):
        """Disconnects from the events of the TreeBuilder."""
        builder.disconnect("replace", self.slot_replace)
        builder.disconnect("finished", self.slot_update)
        builder.disconnect("invalidate", self.invalidate_node)

    def slot_replace(self, builder):
        """Called when the tree builder starts altering the tree.

        Interrupts a process if busy for that tree.

        """
        self.interrupt(builder.root)

    def slot_update(self, builder):
        """Called when the tree builder has finished building the tree.

        Starts a new transformation job for the tree.

        """
        self.build(builder.root)

    def get_transform(self, language):
        """Return a Transform class instance for the specified language."""
        try:
            return self._transforms[language]
        except KeyError:
            with self._lock:
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
        if isinstance(tf, type) and issubclass(tf, Transform):
            return tf()


class BackgroundTransformer(Transformer):
    """A Transformer that does its job in a background thread."""
    def __init__(self):
        super().__init__()
        self._jobs = {}

    def build(self, tree):
        """Reimplemented to build the transformation in a background thread.

        This method starts a background thread performing the transformation
        and returns immediately.

        """
        def job():
            for stage in self.process(tree):
                pass
            del self._jobs[tree]
        job = self._jobs[tree] = threading.Thread(target=job)
        job.start()

    def wait(self, tree):
        """Wait for completion of the transformation of the tree if busy."""
        job = self._jobs.get(tree)
        if job:
            job.wait()

    def busy(self, tree):
        """Return True if a job transforming the tree is busy."""
        return tree in self._jobs


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

