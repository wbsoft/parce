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
This module defines classes and functions to build a tree structure by parsing
a text string.

To get the tree of tokens using a particular root lexicon from a string
of text, use :func:`build_tree`.

A more advanced approach is using the :class:`TreeBuilder`, which can build a
tree in one go as well, but is also capable of updating an existing tree when
the text changes on a particular position, e.g. while typing in a text editor.
In this case, tokens in front of the modified region are reused (carefully
checking whether changes affect earlier regions), and also tokens at the end of
the modified region are reused, if they have the same context ancestry.

TreeBuilder also reports the start and end position of the updated region, and
the lexicons that were left open at the end, which in some languages can mean
that a document or a certain structure is incomplete.

The TreeBuilder is designed so that it is possible to perform tokenizing in a
background thread, and even interrupt tokenizing when changes are to be applied
while processing previous changes.

The :class:`BackgroundTreeBuilder` provides an implementation using Python
threads.

"""

import operator
import threading

from parce.lexer import Lexer
from parce.util import Observable, tokens
from parce.target import TargetFactory
from parce.tree import Context, make_tokens
from parce.treebuilderutil import (
    BuildResult, ReplaceResult, Changes, get_prepared_lexer, new_tree)


def build_tree(root_lexicon, text, pos=0):
    """Build and return a tree in one go."""
    from parce.tree import Context, make_tokens # local is faster
    root = context = Context(root_lexicon, None)
    lexer = Lexer([root_lexicon])
    for e in lexer.events(text, pos):
        if e.target:
            for _ in range(e.target.pop, 0):
                context = context.parent
            for lexicon in e.target.push:
                context = Context(lexicon, context)
                context.parent.append(context)
        context.extend(make_tokens(e, context))
    return root


class TreeBuilder(Observable):
    """Build a tree from parsing the text.

    The root node of the tree is in the ``root`` instance attribute.
    This root context is never replaced, although its lexicon may change and
    of course its children.

    Call :meth:`rebuild` to build or rebuild the tree. This method stores the
    desired changes to the tree and calls :meth:`start_processing`, which can
    be re-implemented to support asynchronous tree building.

    The actual building of a tree happens in :meth:`build_new_tree` which
    builds a (replacement) tree without making any changes yet to the current
    tree.

    The result of :meth:`build_new_tree` is a tuple of arguments that is used
    used when calling :meth:`replace_tree`, which integrates the updated
    subtree in the main tree structure. This method sets three instance
    attributes:

    ``start``, ``end``:
        indicate the region the tokens were changed. After build(), start is
        always 0 and end = len(text), but after rebuild(), these values
        indicate the range that was actually re-tokenized.

    ``lexicons``:
        the list of open lexicons (excluding the root lexicon) at the end of
        the document. This way you can see in which lexicon parsing ended.

        If a tree was rebuilt, and old tail tokens were reused, the lexicons
        variable is not set, meaning that the old value is still valid. If the
        TreeBuilder was not used before, lexicons is an empty tuple.

    No other variables or state are kept, so if you don't need the above
    information anymore, you can throw away the TreeBuilder after use.

    During the building process, the TreeBuilder emits certain events you can
    subscribe to, using the :meth:`~parce.util.Observable.connect` method
    provided by the :class:`~parce.util.Observable` class that's mixed into
    this TreeBuilder class.

    The following events are emitted, with following arguments:

    ``"started"``:
        emitted when a (re)build starts; the handler is called without
        arguments

    ``"replace"``:
        emitted just before the tree actually changes (while the new tree is
        being built, the tree is still unchanged and accessible, but between
        the ``"replace"`` and ``"finished"`` events the tree is in an
        inconsistent state)

    ``"finished"``:
        emitted when a (re)build has finished; the handler is called without
        arguments

    ``"updated"``:
        emitted when a (re)build has finished; the handler is called with two
        arguments: ``start``, ``end``, that denote the updated range

    ``"peek"``:
        emitted by the default implementation of the :meth:`peek` method,
        the handler is called with two arguments: ``start``, ``tree``

    ``"invalidate"``:
        emitted by the default implementation of the :meth:`invalidate_context`
        method, the handler is called with the Context that needs to be
        invalidated

    For example, to get notified when a build process starts::

        >>> b = TreeBuilder(MyLang.root)
        >>> def hi_there():
        ...     print("started")
        ...
        >>> b.connect("started", hi_there)
        >>> b.rebuild("some boring text")
        started
        >>>

    """
    start = 0
    end = 0
    lexicons = ()

    peek_threshold = 0  #: set to a value > 0 to get :meth:`peek` called during building

    def __init__(self, root_lexicon=None):
        super().__init__()
        self.root = Context(root_lexicon, None)
        self.busy = False
        self.changes = []

    def tree(self, text):
        """Convenience method to build a tree and return the root node."""
        self.rebuild(text)
        return self.get_root(True)

    def rebuild(self, text, root_lexicon=False, start=0, removed=0, added=None):
        """Tokenize the modified part of the text again and update the tree.

        The arguments:

        ``text``
            The text to parse. Always give the entire text, also when you only
            actually changed a small part. The tree builder needs to check text
            before and after the changed region, and possibly re-parse more
            text.

        ``root_lexicon``
            The root lexicon to use (default: False). False means no change;
            can be None or any Lexicon. If not False, the tree is always
            rebuilt completely.

        ``start``
            Position of the change (default: 0)

        ``removed``
            The number of removed characters (default: 0)

        ``added``
            The number of added characters (default: None, which means
            all characters from start to the end of the text)

        Calls :meth:`build_new_tree` and :meth:`replace_tree` to do the actual work.

        """
        if added is None:
            added = len(text) - start
        self.lock(True)
        self.changes.append((text, root_lexicon, start, removed, added))
        self.lock(False)
        if not self.busy:
            self.busy = True
            self.start_processing()

    def build_new_tree(self, text, root_lexicon, start, removed, added):
        """Build a new tree without yet modifying the current tree.

        Tokens from the current tree are reused as much as possible. From
        tokens at the tail (after the end of the modified region) the pos
        attribute is updated if necessary.

        The arguments:

        ``text``
            The text to parse. Always the entire text, also when only a small
            portion was changed.

        ``root_lexicon``
            The root lexicon to use. False means no change; can be None or any
            Lexicon. If not False, the tree is always rebuilt completely.

        ``start``
            Position of the change.

        ``removed``
            The number of removed characters.

        ``added``
            The number of added characters.

        Returns a ``Result`` five-tuple with ``tree``, ``start``, ``end``,
        ``offset`` and ``lexicons`` values. The ``start`` and ``end`` are the
        insert positions in the old tree.

        The new ``tree`` is intended to replace a part of, or the whole old
        tree. If ``start`` == 0 and ``lexicons`` is not None; the whole tree
        can be replaced. (In this case; the root lexicon might have changed!)
        Use :meth:`replace_tree` to insert the result tree in the old tree.

        If ``start`` > 0, tokens in the old tree before start are to be
        preserved.

        If ``lexicons`` is None, old tail tokens after ``end`` must be reused,
        and the old list of open lexicons is still relevant. The ``offset`` then
        gives the position change for the tokens that are reused.

        """
        from parce.tree import Context, make_tokens # local is faster

        if root_lexicon is not False:
            start, removed, added = 0, 0, len(text)
        else:
            root_lexicon = self.root.lexicon

        # manage end, and record if there is text after the modified part (tail)
        end = start + removed

        # record the position change for tail tokens that may be reused
        offset = added - removed

        if not root_lexicon:
            return BuildResult(Context(root_lexicon, None), start, start + added, 0, [])

        # If there remains text after the modified part,
        # we try to reuse the old tokens
        tail = False
        if start + added < len(text):
            # find the first token after the modified part
            tail_token = self.root.find_token_after(end)
            if tail_token:
                tail_gen = ((t, t.pos) for t in tail_token.forward_including()
                        if not t.group and not (t.is_first() and t.parent.lexicon.consume))
                for tail_token, tail_pos in tail_gen:
                    tail = True
                    break

        lowest_start = start
        changes = self.changes
        tree = None
        while True:
            # when restarting, see if we can reuse (part of) the new tree
            if tree:
                result = get_prepared_lexer(tree, text, start)
                if result:
                    lexer, events, tokens = result
                    t = tokens[0]
                    context = t.parent
                    for p, i in t.ancestors_with_index():
                        del p[i+1:]
                    del context[-1]
                else:
                    tree = None
            # find insertion spot in old tree
            if not tree:
                start = min(lowest_start, start)
                result = get_prepared_lexer(self.root, text, start)
                if result:
                    lexer, events, tokens = result
                    t = tokens[0]
                    context, tree = new_tree(t)
                    start = tokens[-1].end
                    lowest_start = min(lowest_start, start)
                else:
                    tree = context = Context(root_lexicon, None)
                    lexer = Lexer([root_lexicon])
                    events = lexer.events(text)
                    lowest_start = 0
                peek = self.peek_threshold + lowest_start if self.peek_threshold else 0
            # start parsing
            for e in events:
                if e.target:
                    for _ in range(e.target.pop, 0):
                        context = context.parent
                    for lexicon in e.target.push:
                        context = Context(lexicon, context)
                        context.parent.append(context)
                tokens = make_tokens(e, context)
                if tail:
                    # handle tail
                    pos = tokens[0].pos - offset
                    if pos > tail_pos:
                        for tail_token, tail_pos in tail_gen:
                            if tail_pos >= pos:
                                break
                        else:
                            tail = False
                    if pos == tail_pos and tokens[0].equals(tail_token) and \
                            (context or not context.lexicon.consume) :
                        # we can reuse the tail from tail_pos
                        return BuildResult(tree, lowest_start, tail_pos, offset, None)
                context.extend(tokens)
                if changes:
                    # handle changes
                    c = self.get_changes()
                    if c:
                        # break out and adjust the current tokenizing process
                        text = c.text
                        start = c.start
                        if c.root_lexicon != False:
                            root_lexicon = c.root_lexicon
                            if not root_lexicon:
                                return BuildResult(Context(root_lexicon, None), 0, len(text), 0, [])
                            start = 0
                            tail = False
                            tree = None

                        elif tail:
                            # reuse old tail?
                            new_tail_pos = start + c.added
                            if new_tail_pos >= len(text):
                                tail = False
                            else:
                                offset += c.added - c.removed
                                new_tail_pos -= offset
                                if new_tail_pos > tail_pos:
                                    for tail_token, tail_pos in tail_gen:
                                        if tail_pos >= new_tail_pos:
                                            break
                                    else:
                                        tail = False
                        break # break the for loop to restart at new start pos
                if peek:
                    if tokens[-1].pos > peek:
                        # call peek with a copy of the current tree.
                        copied_tree = tree.copy()
                        # remove the first empty context
                        t = copied_tree[0]
                        while t and t.is_context:
                            t = t[0]
                        while t.is_context and not t:
                            t = t.parent
                            del t[0]
                        self.peek(lowest_start, copied_tree)
                        peek = 0
            else:
                # we ran till the end, also return the open lexicons
                return BuildResult(tree, lowest_start, len(text), 0, lexer.lexicons[1:])
        raise RuntimeError("shouldn't come here")

    def replace_tree(self, result):
        """Modify the tree using the result from :meth:`build_new_tree`.

        In most types of GUI applications, this method should be called in the
        main (GUI) thread.

        The changes are delegated to the various ``replace_`` methods, which
        can be reimplemented to get fine-grained monitoring of and control over
        the tree-replacing process.

        Additionally, this method calls :meth:`invalidate_context` with the
        youngest Context that had children removed or added.

        """
        tree, start, end, offset, lexicons = result

        if not tree.lexicon or tree.lexicon != self.root.lexicon:
            # whole tree update
            root = self.root
            for n in tree:
                n.parent = root
            self.replace_nodes(self.root, slice(None), tree)
            self.replace_root_lexicon(tree.lexicon)
            self.invalidate_context(self.root)

        else:

            context = self.root
            start_trail = self.root.find_token_left_with_trail(start)[1] if start else []
            end_trail = self.root.find_token_with_trail(end)[1] if lexicons is None else []

            # find the context that really changes, adjust trails
            i = 0
            for i, (s, e) in enumerate(zip(start_trail, end_trail)):
                if s == e and tree.is_context and len(tree) == 1:
                    context = context[s]
                    tree = tree[0]
                else:
                    break
            del start_trail[:i], end_trail[:i]

            for n in tree:
                n.parent = context

            slice_end = None
            if end_trail:
                # join stuff after end_trail with tree
                c = context
                t = tree
                end_trail[-1] -= 1
                for i in end_trail:
                    l = len(t) - 1
                    if slice_end is None:
                        slice_end = i + 1
                    else:
                        s = c[i+1:]
                        t.extend(s)
                        for n in s:
                            n.parent = t
                        if offset:
                            for n in tokens(s):
                                n.pos += offset
                    if t:
                        t = t[l]    # t can be empty if len(end_trail) == 1, is last iteration anyway
                    c = c[i]

            if offset:
                # if there remain nodes in the current context after tree
                # insertion, store the index now, later we'll adjust the pos
                if slice_end is not None:
                    replace_pos_index = slice_end - len(context)
                else:
                    replace_pos_index = 0

            if start_trail:
                # replace stuff after start_trail with tree
                c = context
                t = tree
                for i in start_trail[:-1]:
                    for n in t[1:]:
                        n.parent = c
                    self.replace_nodes(c, slice(i + 1, slice_end), t[1:])
                    slice_end = None
                    t = t[0]
                    c = c[i]
                i = start_trail[-1]
                for n in t:
                    n.parent = c
                self.replace_nodes(c, slice(i + 1, slice_end), t)
                self.invalidate_context(c)
            else:
                self.replace_nodes(context, slice(slice_end), tree)
                self.invalidate_context(context)

            if offset:
                if replace_pos_index < 0:
                    self.replace_pos(context, len(context) + replace_pos_index, offset)
                for p, i in context.ancestors_with_index():
                    self.replace_pos(p, i + 1, offset)

        return ReplaceResult(start, end + offset, lexicons)

    def replace_nodes(self, context, slice_, nodes):
        """Replace the context's slice with new nodes.

        This method is called by :meth:`replace_tree`.
        You can reimplement this method to notify others of the change.

        """
        context[slice_] = nodes

    def replace_root_lexicon(self, lexicon):
        """Set the root lexicon.

        This method is called by :meth:`replace_tree`.
        You can reimplement this method to notify others of the change.

        """
        self.root.lexicon = lexicon

    def replace_pos(self, context, index, offset):
        """Adjust the pos attribute of all tokens in ``context[index:]``.

        This method is called by :meth:`replace_tree`.
        You can reimplement this method to notify others of the change.

        """
        for t in tokens(context[index:]):
            t.pos += offset

    def invalidate_context(self, context):
        """Called with the younghest Context that had children are removed or
        added.

        This means that the meaning of this context probably has changed, for
        example when you want to transform the context to some other data
        structure, and that the ancestors also need to be invalidated.

        The default implementation of this method emits the ``invalidate``
        event, see :meth:`~parce.util.Observable.connect`.

        """
        self.emit("invalidate", context)

    def get_root(self, wait=False, callback=None, args=(), kwargs={}):
        """Return the root element of the completed tree.

        This is simply the ``root`` instance attribute, but this method only
        returns the tree when the ``busy`` attribute is False.

        If wait is True, this call blocks until tokenizing is done, and the
        full tree is returned. If wait is False, None is returned if the tree
        is still busy being built.

        If a callback is given and tokenizing is still busy, that callback is
        called once when tokenizing is ready. If given, args and kwargs are the
        arguments the callback is called with, defaulting to () and {},
        respectively.

        Note that, for the lifetime of a TreeBuilder, the root element is always
        the same. The root element is also accessible in the `root` attribute.
        But using this method you can be sure that you are dealing with a
        complete and fully intact tree.

        """
        if self.busy:
            if callback:
                if args or kwargs:
                    callback = lambda: callback(*args, **kwargs)
                self.connect("finished", callback, True)
            if not wait:
                return
            self.wait()
        return self.root

    def get_changes(self):
        """Get and combine the stored change requests in a Changes object.

        This may only be called from the same thread that also performs the
        :meth:`rebuild()`.

        """
        c = Changes()
        while self.changes:
            c.add(*self.changes.pop(0))
        return c

    def start_processing(self):
        """Called when there are recorded changes to process.

        The default implementation read all build stages from the
        :meth:`process` generator until exhausted. You can inherit from this
        method to call it e.g. in a background thread.

        """
        for stage in self.process():
            pass

    def process(self):
        """Process all changes and update the tree.

        This method behaves as a generator coroutine, instead of simply calling
        this method, you should iterate over its output, which reports which
        stage the process is at.

        Yields "build" when about to build a new tree; "replace" when about to
        replace a new tree; (which can be repeated); "finish" when finished
        looping, and "done" at the very end.

        When re-implementing :meth:`start_processing`, you can choose to decide
        which stages are to be run in a background thread and which in a main
        (GUI) thread.

        You should exhaust the generator fully.

        """
        self.process_started()
        start = end = -1
        lexicons = False    # no change
        self.lock(True)
        c = self.get_changes()
        while c and c.has_changes():
            self.lock(False)
            yield "build"
            result = self.build_new_tree(c.text, c.root_lexicon, c.start, c.removed, c.added)
            yield "replace"
            self.emit("replace")
            r = self.replace_tree(result)
            start = r.start if start == -1 else min (start, r.start)
            end = r.end if end == -1 else max(c.new_position(end), r.end)
            if r.lexicons is not None:
                lexicons = r.lexicons
            self.lock(True)
            c = self.get_changes()
        yield "finish"
        if start != -1:
            self.start = start
        if end != -1:
            self.end = end
        if lexicons is not False:
            self.lexicons = lexicons
        self.busy = False
        self.lock(False)
        self.process_finished()
        yield "done"

    def wait(self):
        """Implement to wait for completion if a background job is running.

        The default implementation does nothing, and immediately returns.

        """
        pass

    def peek(self, start, tree):
        """This is called from :meth:`build_new_tree` with a sneak preview tree.

        This can be used to get a small tree before the new tree is built
        completely, which is useful to update e.g. highlighting of a small
        portion of a document that is edited by a user, instead of waiting on
        the whole tree to update (which may cause slow highlighting updates).

        When build_new_tree (the build stage) is called from a background
        thread, this method will also be called from that same thread.

        Enable the ``peek()`` feature by setting the ``peek_threshold``
        attribute to a value > 0. E.g. the value 1000 will cause the
        :meth:`peek` method to be called with a tree that encompasses at least
        1000 characters (starting with the start position).

        The tree that is given, is a copy of the current tree. It is safe to
        use it in another thread, although its contents are not valid anymore
        when the build has finished, or when a build is restarted, causing
        peek() to be called a second time. (A build is restarted when there are
        new changes close to the position the build originally started.)

        The default implementation of this method emits the ``peek`` event, see
        :meth:`~parce.util.Observable.connect`.

        """
        self.emit("peek", start, tree)

    def lock(self, acquire):
        """Acquire lock (True) or release lock (False). Does nothing by default.

        If you want to run the full update and replace jobs in a background
        thread, you may need locking, to prevent changes from going unnoticed.

        """
        pass

    def process_started(self):
        """Called at the start ot the tree building process.

        The default implementation of this method emits the ``started`` event,
        see :meth:`~parce.util.Observable.connect`.

        """
        self.emit("started")

    def process_finished(self):
        """Called when tree building is done.

        The default implementation of this method emits the ``updated(start,
        end)`` and ``finished`` events, see
        :meth:`~parce.util.Observable.connect`.

        """
        self.emit("updated", self.start, self.end)
        self.emit("finished")


class BackgroundTreeBuilder(TreeBuilder):
    """A TreeBuilder that can tokenize a text in a Python thread.

    In BackgroundTreeBuilder, :meth:`rebuild()` returns immediately, because
    :meth:`start_processing()` has been reimplemented to call itself in a
    background thread.

    You can continue adding changes while previous changes are processed;
    the tree builder will immediately adapt to the new changes.

    To be sure you get a completed tree, call ``get_root(True)``.

    """
    def __init__(self, root_lexicon=None):
        super().__init__(root_lexicon)
        self.job = None
        self._lock = threading.Lock()

    def lock(self, acquire):
        """Reimplemented to actually lock/unlock."""
        self._lock.acquire() if acquire else self._lock.release()

    def start_processing(self):
        """Reimplemented to call start_processing in a background thread."""
        self.job = threading.Thread(target=super().start_processing)
        self.job.start()

    def wait(self):
        """Reimplemented to await our background thread if active."""
        job = self.job
        if job:
            job.join()

    def process_finished(self):
        """Reimplemented to clear the job attribute."""
        self.job = None
        super().process_finished()


