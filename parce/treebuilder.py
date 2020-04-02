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


import threading

from parce.lexer import Lexer
from parce.tree import Context, Token, _GroupToken
from parce.util import tokens
from parce.target import TargetFactory
from parce.treebuilderutil import (
    Build, Result, Changes, find_insert_tokens, get_lexer, new_tree)


def build_tree(root_lexicon, text, pos=0):
    """Build and return a tree in one go."""
    root = context = Context(root_lexicon, None)
    lexer = Lexer([root_lexicon])
    for e in lexer.events(text, pos):
        if e.target:
            for _ in range(e.target.pop, 0):
                context = context.parent
            for lexicon in e.target.push:
                context = Context(lexicon, context)
                context.parent.append(context)
        if len(e.tokens) > 1:
            tokens = tuple(_GroupToken(context, *t) for t in e.tokens)
            for t in tokens:
                t.group = tokens
        else:
            tokens = Token(context, *e.tokens[0]),
        context.extend(tokens)
    return root


class BasicTreeBuilder:
    """Build a tree from parsing the text.

    The root node of the tree is in the ``root`` instance attribute.
    This root context is never replaced, although its lexicon may change and
    of course its children.

    Building a tree happens in :meth:`build_new` which builds a (replacement)
    tree without making any changes yet to the current tree.

    The result of :meth:`build_new` is a tuple of arguments that can be used
    to call :meth:`replace_tree`, which integrates the updated subtree in the
    main tree structure. This method sets three instance attributes:

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

    The :meth:`build` and :meth:`rebuild` methods are provided for convenience.

    """
    start = 0
    end = 0
    lexicons = ()

    def __init__(self, root_lexicon=None):
        self.root = Context(root_lexicon, None)
        self.changes = False # keep "if self.changes" in rebuild() from complaining

    def tree(self, text):
        """Convenience method building and returning the tree with all tokens."""
        self.build(text)
        return self.root

    def build(self, text):
        """Convenience method building the tree with all tokens.

        Calls :meth:`build_new` and :meth:`replace_tree` to do the work.

        """
        self.rebuild(text)

    def rebuild(self, text, root_lexicon=False, start=0, removed=0, added=None):
        """Tokenize the modified part of the text again and update the tree.

        Except for the ``text``, all arguments have default values:

        ``root_lexicon``
            False means no change; can be None or a Lexicon

        ``start``
            Position of the change (default: 0)

        ``removed``
            The number of removed characters (default: 0)

        ``added``
            The number of added characters (default: None, which means
            the length of the entire text)

        Calls :meth:`build_new` and :meth:`replace_tree` to do the actual work.

        """
        if added is None:
            added = len(text)
        result = self.build_new(Build(text, root_lexicon, start, removed, added))
        self.replace_tree(result)

    def build_new(self, build):
        """Build a new tree without yet modifying the current tree.

        Tokens from the current tree are reused as much as possible. From
        tokens at the tail (after the end of the modified region) the pos
        attribute is updated if necessary.

        The ``build`` argument is a five-tuple ``Build(root_lexicon, text,
        start, removed, added)``.

        Returns a ``Result`` tuple with ``tree``, ``start``, ``end``,
        ``offset`` and ``lexicons`` values ``start`` and ``end`` are the
        insert positions in the old tree.

        The new ``tree`` is intended to replace a part of, or the whole old
        tree. If ``start`` == 0 and ``lexicons`` is not None; the whole tree
        can be replaced. (In this case; check the root lexicon of the returned
        tree, it might have changed!) The :meth:`replace_tree` method can
        perform this action.

        If ``start`` > 0, tokens in the old tree before start are to be
        preserved.

        If ``lexicons`` is None, old tail tokens after ``end`` must be reused,
        and the old list of open lexicons is still relevant. The ``offset`` then
        gives the position change for the tokens that are reused.

        """
        text, root_lexicon, start, removed, added = build

        if root_lexicon is not False:
            start, removed, added = 0, 0, len(text)
        else:
            root_lexicon = self.root.lexicon

        # manage end, and record if there is text after the modified part (tail)
        end = start + removed

        # record the position change for tail tokens that may be reused
        offset = added - removed

        if not root_lexicon:
            return Result(Context(root_lexicon, None), start, start + added, 0, None)

        # If there remains text after the modified part,
        # we try to reuse the old tokens
        tail = False
        if start + added < len(text):
            # find the first token after the modified part
            tail_token = self.root.find_token_after(end)
            if tail_token:
                tail_gen = ((t, t.pos) for t in tail_token.forward()
                        if not t.group or (t.group and t is t.group[0]))
                tail_pos = tail_token.pos
                tail = True

        lowest_start = start
        changes = self.changes
        tree = None
        while True:
            # when restarting, see if we can reuse (part of) the new tree
            if tree:
                tokens = find_insert_tokens(tree, text, start)
                if tokens:
                    t = tokens[0]
                    context = t.parent
                    lexer = get_lexer(t)
                    events = lexer.events(text, t.pos)
                    for p, i in t.ancestors_with_index():
                        del p[i+1:]
                    del context[-1]
                else:
                    tree = None
            # find insertion spot in old tree
            if not tree:
                tokens = find_insert_tokens(self.root, text, start)
                if tokens:
                    t = tokens[0]
                    context = new_tree(t)
                    lexer = get_lexer(t)
                    events = lexer.events(text, t.pos)
                    next(events) # skip over the first token, we need its target
                    tree = context.root()
                    start = tokens[-1].end
                    lowest_start = min(lowest_start, start)
                else:
                    tree = context = Context(root_lexicon, None)
                    lexer = Lexer([root_lexicon])
                    events = lexer.events(text)
                    lowest_start = 0
            # start parsing
            for e in events:
                if e.target:
                    for _ in range(e.target.pop, 0):
                        context = context.parent
                    for lexicon in e.target.push:
                        context = Context(lexicon, context)
                        context.parent.append(context)
                if len(e.tokens) > 1:
                    tokens = tuple(_GroupToken(context, *t) for t in e.tokens)
                    for t in tokens:
                        t.group = tokens
                else:
                    tokens = Token(context, *e.tokens[0]),
                if tail:
                    # handle tail
                    pos = tokens[0].pos - offset
                    if pos > tail_pos:
                        for tail_token, tail_pos in tail_gen:
                            if tail_pos >= pos:
                                break
                        else:
                            tail = False
                    if pos == tail_pos and tokens[0].equals(tail_token):
                        # we can reuse the tail from tail_pos
                        return Result(tree, lowest_start, tail_pos, offset, None)
                context.extend(tokens)
                if changes:
                    # handle changes
                    c = self.get_changes()
                    if c:
                        # break out and adjust the current tokenizing process
                        text = c.text
                        start = c.position
                        if c.root_lexicon != False:
                            tree.lexicon = c.root_lexicon
                            start = 0
                            tail = False
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
            else:
                # we ran till the end, also return the open lexicons
                return Result(tree, lowest_start, len(text), 0, lexer.lexicons[1:])
        raise RuntimeError("shouldn't come here")

    def replace_tree(self, result):
        """Modify the tree using the result from build_new().

        In most types of GUI applications, this method should be called in the
        main (GUI) thread.

        """
        tree, start, end, offset, lexicons = result

        if not tree.lexicon or tree.lexicon != self.root.lexicon:
            # whole tree update
            root = self.root
            for n in tree:
                n.parent = root
            self.replace_nodes(self.root, slice(None), tree)
            self.replace_root_lexicon(tree.lexicon)

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

            # all tree nodes will end up in context, don't reparent twice :-)
            for n in tree:
                n.parent = context

            if end_trail:
                # join stuff after end_trail with tree
                c = context
                t = tree
                reparent = False
                end_trail[-1] -= 1
                for i in end_trail:
                    l = len(t) - 1
                    s = c[i+1:]
                    t.extend(s)
                    if reparent:
                        for n in s:
                            n.parent = t
                    else:
                        reparent = True
                    if offset:
                        for n in tokens(s):
                            n.pos += offset
                    t = t[l]
                    c = c[i]

            if start_trail:
                # replace stuff after start_trail with tree
                c = context
                t = tree
                reparent = False
                for i in start_trail[:-1]:
                    if reparent:
                        for n in t[1:]:
                            n.parent = c
                    else:
                        reparent = True
                    self.replace_nodes(c, slice(i + 1, None), t[1:])
                    t = t[0]
                    c = c[i]
                i = start_trail[-1]
                if reparent:
                    for n in t:
                        n.parent = c
                self.replace_nodes(c, slice(i + 1, None), t)
            else:
                self.replace_nodes(context, slice(None), tree)

            if offset:
                for p, i in context.ancestors_with_index():
                    self.replace_pos(p, slice(i + 1, None), offset)

        self.start = start
        self.end = end + offset
        if lexicons is not None:
            self.lexicons = lexicons

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

    def replace_pos(self, context, slice_, offset):
        """Adjust the pos attribute of all tokens in the context's slice.

        This method is called by :meth:`replace_tree`.
        You can reimplement this method to notify others of the change.

        """
        for t in tokens(context[slice_]):
            t.pos += offset


class TreeBuilder(BasicTreeBuilder):
    """TreeBuilder extends BasicTreeBuilder with change management functions.

    Instead of calling :meth:`build()` or :meth:`rebuild()`, you can call
    :meth:`change_text` and/or :meth:`change_root_lexicon`, which will trigger
    a rebuild. If you call these methods within a :keyword:`with` context,
    changes are stored and applied as soon as the context exits.

    You can inherit from this class and call :meth:`process_changes` from a
    background thread to move tokenizing to a background thread. See
    :class:`BackgroundTreeBuilder` for an example that uses Python threads.

    While tree building is in progress, the ``busy`` attribute is set to True,
    the tree can then be in an inconsistent state. During background
    tokenizing, new changes can be submitted and will immediately be acted
    upon; the ``rebuild()`` method can interrupt itself and adjust tokenizing
    to the new changes.

    """
    busy = False

    def __init__(self, root_lexicon=None):
        super().__init__(root_lexicon)
        self._incontext = 0
        self.busy = False
        self.changes = []

    def __enter__(self):
        self._incontext += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._incontext -= 1
        if self._incontext == 0 and not self.busy:
            self.start_processing()

    def change_root_lexicon(self, text, lexicon):
        """Record a request to change the root lexicon.

        Because TreeBuilder does not store the text, we should also give the
        text. If we are not in a :keyword:`with` context,
        :meth:`start_processing()` is called immediately.

        """
        self.changes.append(("lexicon", text, lexicon))
        if self._incontext == 0 and not self.busy:
            self.start_processing()

    def change_text(self, text, position=0, removed=None, added=None):
        """Record a request to change the text.

        If we are not in a :keyword:`with` context, :meth:`start_processing()`
        is called immediately.

        """
        self.changes.append(("text", text, position, removed, added))
        if self._incontext == 0 and not self.busy:
            self.start_processing()

    def get_changes(self):
        """Get and combine the stored change requests in a Changes object.

        This may only be called from the same thread that also performs the
        :meth:`rebuild()`.

        """
        c = Changes()
        while self.changes:
            request, *args = self.changes.pop(0)
            c.change_root_lexicon(*args) if request == "lexicon" else c.change_contents(*args)
        return c

    def start_processing(self):
        """Initialize and start processing if needed."""
        self.busy = True
        self.start = self.end = -1
        self.process_started()
        self.do_processing()

    def do_processing(self):
        """Called when there are recorded changes to process.

        Calls, :meth:`process_changes()` and after that
        :meth:`finish_processing()`; may be reimplemented to call
        :meth:`process_changes()` in a background thread.

        """
        self.process_changes()
        self.finish_processing()

    def process_changes(self):
        """Processes the recorded change requests."""
        c = self.get_changes()
        start = self.start
        end = self.end
        while c and c.has_changes():
            self.rebuild(c.text, c.root_lexicon, c.position, c.removed, c.added)
            start = self.start if start == -1 else min(start, self.start)
            end = self.end if end == -1 else max(c.new_position(end), self.end)
            c = self.get_changes()
        if start != -1:
            self.start = start
        if end != -1:
            self.end = end

    def finish_processing(self):
        """Called by :meth:`do_processing()` when :meth:`process_changes()` has finished."""
        if self.changes:
            self.do_processing()
            return
        self.busy = False
        self.process_finished()

    def process_started(self):
        """Called when ``start()`` has been called to update the tree.

        Does nothing by default.

        """
        pass

    def process_finished(self):
        """Called when tree building is done.

        Does nothing by default.

        """
        pass


class BackgroundTreeBuilder(TreeBuilder):
    """A TreeBuilder that can tokenize a text in a Python thread.

    In BackgroundTreeBuilder, :meth:`change_text()` and
    :meth:`change_root_lexicon()` return immediately, because
    :meth:`do_processing()` has been reimplemented to call
    :meth:`process_changes()` in a background thread.

    You can continue adding changes while previous changes are processed;
    the tree builder will immediately adapt to the new changes.

    You can add callbacks to the ``updated_callbacks`` attribute (using
    ``add_build_updated_callback()``) that are called everytime the whole
    document is tokenized.

    You can also add callbacks to the ``finished_callbacks`` attribute, using
    ``add_finished_callback()``; those are called once when all pending changes
    are processed and then forgotten again.

    To be sure you get a complete tree, call ``get_root()``.

    """
    def __init__(self, root_lexicon=None):
        super().__init__(root_lexicon)
        self.job = None
        self.lock = threading.Lock()
        self.updated_callbacks = []
        self.finished_callbacks = []

    def change_root_lexicon(self, text, lexicon):
        """Reimplemented to add locking."""
        with self.lock:
            self.changes.append(("lexicon", text, lexicon))
        if self._incontext == 0 and not self.busy:
            self.start_processing()

    def change_text(self, text, position=0, removed=None, added=None):
        """Reimplemented to add locking."""
        with self.lock:
            self.changes.append(("text", text, position, removed, added))
        if self._incontext == 0 and not self.busy:
            self.start_processing()

    def do_processing(self):
        """Start a background job if needed."""
        self.job = threading.Thread(target=super().do_processing)
        self.job.start()

    def process_changes(self):
        """Reimplemented to add locking."""
        self.lock.acquire()
        c = self.get_changes()
        start = self.start
        end = self.end
        while c and c.has_changes():
            self.lock.release()
            self.rebuild(c.text, c.root_lexicon, c.position, c.removed, c.added)
            start = self.start if start == -1 else min(start, self.start)
            end = self.end if end == -1 else max(c.new_position(end), self.end)
            self.lock.acquire()
            c = self.get_changes()
        if start != -1:
            self.start = start
        if end != -1:
            self.end = end

    def finish_processing(self):
        """Called by :meth:`do_processing()` when :meth:`process_changes()` has finished."""
        self.busy = False
        self.process_finished()
        self.lock.release()

    def process_finished(self):
        """Reimplemented to clear the job attribute and call the callbacks."""
        self.job = None
        for cb in self.updated_callbacks:
            cb(self.start, self.end)
        while self.finished_callbacks:
            callback, args, kwargs = self.finished_callbacks.pop()
            callback(*args, **kwargs)

    def wait(self):
        """Wait for completion if a background job is running."""
        while True:
            job = self.job
            if job:
                job.join()
                if self.busy:
                    continue
            break

    def get_root(self, wait=False, callback=None, args=None, kwargs=None):
        """Get the root element of the completed tree.

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
        if not self.job:
            return self.root
        if callback:
            self.add_finished_callback(callback, args, kwargs)
        if wait:
            self.wait()
            return self.root

    def add_build_updated_callback(self, callback):
        """Add a callback to be called when the whole text is tokenized.

        The callback is called with two arguments (start, end) denoting
        the range in the text that was tokenized again.

        """
        if callback not in self.updated_callbacks:
            self.updated_callbacks.append(callback)

    def remove_build_updated_callback(self, callback):
        """Remove a previously registered callback to be called when the whole text is tokenized."""
        if callback in self.updated_callbacks:
            self.updated_callbacks.remove(callback)

    def add_finished_callback(self, callback, args=None, kwargs=None):
        """Add a callback to be called when tokenizing finishes.

        This callback will be called once, directly after being called
        it will be forgotten.

        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        cb = (callback, args, kwargs)
        if cb not in self.finished_callbacks:
            self.finished_callbacks.append(cb)

    def remove_finished_callback(self, callback, args=None, kwargs=None):
        """Remove a callback that was registered to be called when tokenizing finishes."""
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        cb = (callback, args, kwargs)
        if cb in self.finished_callbacks:
            self.finished_callbacks.remove(cb)

