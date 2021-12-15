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

"""

import collections
import sys
import threading
import weakref

import parce.lexer
import parce.util


class Item(collections.namedtuple("Item", "name obj")):
    """A named tuple(name, obj) wrapping the return value of a Transform method.

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
    __slots__ = ('_arg',)

    def __init__(self, arg, iterable=()):
        """Items is initialized with the lexicon's argument."""
        self._arg = arg
        super().__init__(iterable)

    def __getitem__(self, n):
        """Reimplemented to return an Items instance when slicing."""
        result = super().__getitem__(n)
        if isinstance(n, slice):
            return type(self)(self.arg, result)
        return result

    @property
    def arg(self):
        """The lexicon's argument (if any)."""
        return self._arg

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

    def peek(self, index, *values):
        """Return True if the items from ``index`` compare equal with the
        ``values``.

        For tokens, the value is their action; for :class:`Item` instances
        their name. Negative indices are allowed.

        .. versionadded:: 0.27.0
        """
        if index < 0:
            index += len(self)
            if index < 0:
                return False
        if index + len(values) > len(self):
            return False
        for i, v in enumerate(values, index):
            t = self[i]
            if (t.action if t.is_token else t.name) != v:
                return False
        return True


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

    transform_name_template = "{}Transform"
    """This format string creates the name to look for when searching a
    suitable Transform class in a Language module space (see
    :meth:`find_transform`).

    .. versionadded:: 0.27.0

    """

    def __init__(self):
        super().__init__()
        self._transforms = parce.util.caching_dict(self.find_transform)
        self._cache = weakref.WeakKeyDictionary()
        self._interrupt = weakref.WeakKeyDictionary()

    def transform_text(self, root_lexicon, text, pos=0):
        """Directly create an evaluated object from text using root_lexicon.

        The transform methods get intermediate tokens, but *no* tree is built
        and the tokens don't have a parent.

        """
        if not root_lexicon:
            return  # a root lexicon can be None, but then there are no children

        from parce.tree import Context, make_tokens  # local lookup is faster
        from parce.lexer import Event
        from parce.target import Target

        def make_target(pop, push):
            """Return a Target if pop < 0 or push is not empty."""
            if pop or push:
                return Target(pop, push)

        def build_tree(lexicons, events):
            """Build a tree in case missing lexicons need to be handled.

            Returns the tree and the next event (if any), with adapted pop
            value.

            """
            tree = context = Context(lexicons[0], None)
            for lexicon in lexicons[1:]:
                context = Context(lexicon, context)
                context.parent.append(context)
            for target, lexemes in events:
                if target:
                    for pop in range(target.pop, 0):
                        if context is tree:
                            return tree, Event(make_target(pop, target.push), lexemes)
                        context = context.parent
                    for lexicon in target.push:
                        context = Context(lexicon, context)
                        context.parent.append(context)
                context.extend(make_tokens(lexemes, context))
            return tree, None

        def consume_events(lexicons, events):
            """Simply consume events until the first of the specified lexicons ends.

            Returns the next event, if any, with adapted pop value.

            """
            pop = len(lexicons)
            for target, lexemes in events:
                if target:
                    pop += target.pop
                    if pop <= 0:
                        return Event(make_target(pop, target.push), lexemes)
                    pop += len(target.push)

        curlang = root_lexicon.language
        transform = self.get_transform(curlang)

        events = parce.lexer.Lexer([root_lexicon]).events(text, pos)
        root_meth = getattr(transform, root_lexicon.name, None)
        if root_meth:
            add_untransformed = _allow_untransformed(root_meth)
            items = Items(root_lexicon.arg)
            stack = []
            lexicon = root_lexicon

            for target, lexemes in events:
                while target:
                    for _ in range(target.pop, 0):
                        lexicon, olditems, meth, name, add_untransformed = stack.pop()
                        olditems.append(Item(name, meth(items)))
                        items = olditems
                    for i, l in enumerate(target.push):
                        if l.language is not curlang:
                            curlang = l.language
                            transform = self.get_transform(curlang)
                        meth = getattr(transform, l.name, None)
                        if meth:
                            stack.append((lexicon, items, meth, l.name, add_untransformed))
                            add_untransformed = _allow_untransformed(meth)
                            items = Items(l.arg)
                            lexicon = l
                        else:
                            if add_untransformed:
                                context, event = build_tree(target.push[i:], events)
                                items.append(Item("<untransformed>", context))
                            else:
                                event = consume_events(target.push[i:], events)
                            target, lexemes = event if event else (None, ())
                            break
                    else:
                        break
                items.extend(make_tokens(lexemes))

            # unwind
            while stack:
                lexicon, olditems, meth, name, add_untransformed = stack.pop()
                olditems.append(Item(name, meth(items)))
                items = olditems
            return root_meth(items)

    def transform_tree(self, tree):
        """Evaluate a tree structure."""
        self._interrupt[tree] = False

        if not tree.lexicon:
            return  # a root lexicon can be None, but then there are no children

        curlang = tree.lexicon.language
        transform = self.get_transform(curlang)
        root_meth = getattr(transform, tree.lexicon.name, None)
        if root_meth:
            add_untransformed = _allow_untransformed(root_meth)
            stack = []
            node, items, i = tree, Items(tree.lexicon.arg), 0
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
                        # don't bother going in this context if there is no method
                        if meth:
                            try:
                                items.append(Item(name, self._cache[n]))
                            except KeyError:
                                stack.append((items, i + 1, meth, add_untransformed))
                                node, items, i = n, Items(n.lexicon.arg), 0
                                add_untransformed = _allow_untransformed(meth)
                                break
                        elif add_untransformed:
                            items.append(Item("<untransformed>", n))
                else:
                    if stack:
                        name = node.lexicon.name
                        olditems, i, meth, add_untransformed = stack.pop()
                        obj = self._cache[node] = meth(items)
                        items = olditems
                        items.append(Item(name, obj))
                        node = node.parent
                    else:
                        return root_meth(items)

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
        yield "done"
        self.emit("finished", tree)

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
        """Return a Transform class instance for the specified language.

        May return None, if no Transform was added and none could be found.

        """
        return self._transforms[language]

    def add_transform(self, language, transform):
        """Add a Transform instance for the specified language.

        You may also specify None, to disable transformation for that language
        even if a transform could automatically be found.

        """
        self._transforms[language] = transform

    def find_transform(self, language):
        """Try to find a Transform for the specified language definition.

        This is done by looking for a Transform subclass in the language's
        module, with the same name as the language with "Transform" appended.
        So for a language class named "Css", this method tries to find a
        Transform in the same module with the name "CssTransform".

        This naming scheme can be modified by setting the
        :attr:`transform_name_template` attribute.

        This method is called by :meth:`get_transform` if no Transform was
        added for the language.

        """
        module = sys.modules[language.__module__]
        tfname = self.transform_name_template.format(language.__name__)
        tf = getattr(module, tfname, None)
        if isinstance(tf, type) and issubclass(tf, Transform):
            return tf()


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


def add_untransformed(func):
    """Decorator to mark a Transform method with the 'add_untransformed' flag.

    When a :class:`Transform` method has this flag, child contexts of this
    method's context that have no transform method are not silently ignored,
    but added in an :class:`Item` with ``name`` ``<untransformed>`` (including
    the angle brackets).

    For example::

        class MyLangTransform(Transform):
            @add_untransformed
            def root(self, items):
                "This method also gets the untransformed Contexts"
                for item in items:
                    if not item.is_token and item.name == "<untransformed>":
                        context = item.obj
                        # do something with the parce context....

    """
    func.add_untransformed = True
    return func


def _allow_untransformed(meth):
    """Return True when the method wants the untransformed stuff."""
    return getattr(meth.__func__, "add_untransformed", False)


