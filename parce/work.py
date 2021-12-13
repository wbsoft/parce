# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2019-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
This module defines the :class:`Worker` class.

A Worker is designed to run a TreeBuilder and a Transformer as soon as source
text is updated. It is possible to run those jobs in a background thread.

The whole process is divided in certain stages, and performed by exhausting the
:meth:`Worker.process` generator fully.

The Worker is intended to be used as the compagnon for the
:class:`~parce.Document` class and cause the TreeBuilder and (if set) the
Transformer to do their jobs in a configurable and flexible manner.

It is possible to wait for the parce tree of the transform result, or to
arrange for a callback to be called when the work is done. As Worker inherits
:class:`~.util.Observable`, you can connect to its events to get notified when
a tree or transform is updated.

Inherit of Worker to implement other features or another way to use a
background thread for (parts of) the job.

"""

import threading
import weakref

from . import util


IDLE      = 0       # result is up-to-date
BUILD     = 1       # result is still valid but not up-to-date
REPLACE   = 3       # result is invalid, in process of being replaced
DONE      = 4       # result is ready but finished callbacks still to be done


_STATES = {
    "build": BUILD,
    "replace": REPLACE,
    "done": DONE,
}


class Worker(util.Observable):
    """Runs the TreeBuilder and the Transformer.

    Initialize with a :class:`~.treebuilder.TreeBuilder` and optionally a
    :class:`~.transform.Transformer`. It is not possible to change the
    treebuilder later; but you can set another transformer, or use no
    transformer at all.

    Call :meth:`update` to re-run the treebuilder on changed text, or new text,
    or to use a new root lexicon. Call :meth:`set_transformer` to set another
    Transformer, which triggers a re-run of the transformer alone.

    You can :meth:`~.util.Observable.connect` to the following signals:

    ``"started"``:
        emitted when a build process has started

    ``"tree_updated"``:
        emitted when a tree (re)build has finished; the handler is called with
        two arguments: ``start``, ``end``, that denote the updated text range

    ``"tree_finished"``:
        emitted when a (re)build has finished; the handler is called without
        arguments

    ``"transform_finished"``:
        emitted when a transform rebuild has finished; the handler is called
        without arguments.

    """
    def __init__(self, treebuilder, transformer=None):
        super().__init__()
        self._builder = treebuilder
        self._transformer = transformer

        self._condition = threading.Condition()
        self._transform_lock = threading.Lock() # prevent setting Transformer without noticing
        self._tree_state = IDLE
        self._transform_state = IDLE

        treebuilder.connect("invalidate", self.slot_invalidate)
        treebuilder.connect("replace", self.slot_replace)

    def builder(self):
        """Return the TreeBuilder we were initialized with."""
        return self._builder

    def set_transformer(self, transformer):
        """Set the Transformer to use.

        You may use one Transformer for multiple Workers.  Use None to
        remove the current transformer.

        Setting a new Transformer updates the transform result.
        This method should always be called from the main thread.

        """
        if transformer is not self._transformer:
            with self._transform_lock:
                self._transformer = transformer
                with self._condition:
                    start = self._transform_state & REPLACE == 0
            if start:
                self.start()

    def transformer(self):
        """Return the current Transformer, if set."""
        return self._transformer

    def update(self, text, root_lexicon=False, start=0, removed=0, added=None):
        """Start a process to update the tree and the transform.

        For the meaning of the arguments, see
        :meth:`.treebuilder.TreeBuilder.rebuild`.

        This method should always be called from the main thread.

        """
        self._builder.add_changes(text, root_lexicon, start, removed, added)
        if not self._builder.busy:
            self._builder.busy = True
            self.start()

    def start(self):
        """Start the update process.

        Sets the initial state and then calls :meth:`run_process`. This method
        should always be called from the main thread.

        """
        with self._condition:
            self._tree_state = BUILD
            if self._transformer and self._transform_state == IDLE:
                self._transform_state = BUILD
        self.run_process()

    def run_process(self):
        """Exhaust the :meth:`process` generator.

        Called by :meth:`start`; performs the work after initial state has been
        set up.

        This method should always be called from the main thread, but may be
        reimplemented to do (parts of the) work in a background thread.

        """
        for stage in self.process():
            pass

    def process(self):
        """Generator performing the actual process, exhausted by :meth:`run_process`."""
        c = self._condition

        try:
            ## run the treebuilder
            self.start_build()
            for stage in self._builder.process():
                yield "tree_" + stage
                state = _STATES.get(stage)
                if state:
                    with c:
                        self._tree_state = state
            self.finish_build()
            with c:
                self._tree_state = IDLE
                c.notify_all()

            ## run the transformer
            self._transform_lock.acquire()
            t, old = self._transformer, None
            if t:
                while t and t is not old:
                    self._transform_lock.release()
                    for stage in t.process(self._builder.root):
                        yield "transform_" + stage
                        state = _STATES.get(stage)
                        if state is not None:
                            with c:
                                self._transform_state = state
                    self._transform_lock.acquire()
                    # if the transformer was replaced while running, start again
                    t, old = self._transformer, t
                self._transform_lock.release()
                self.finish_transform()
            else:
                self._transform_lock.release()

        finally:
            with c:
                self._tree_state = IDLE
                self._transform_state = IDLE
                c.notify_all()

    def wait_build(self):
        """Wait for the build job to be completed.

        Immediately returns if there is no build job active.

        """
        with self._condition:
            while self._tree_state & REPLACE:
                self._condition.wait()

    def wait_transform(self):
        """Wait for the transform job to be completed.

        Immediately returns if there is no transform job active.

        """
        with self._condition:
            while self._transform_state & REPLACE:
                self._condition.wait()

    def get_root(self, wait=False, callback=None):
        """Return the root element of the completed tree.

        This is simply the builder's ``root`` instance attribute, but this
        method only returns the tree when it is up-to-date.

        If wait is True, this call blocks until tokenizing is done, and the
        full tree is returned. If wait is False, None is returned if the tree
        is still busy being built.

        If a callback is given and tokenizing is still busy, that callback is
        called once when tokenizing is ready, with the :class:`Worker` as the
        sole argument.

        Note that, for the lifetime of a Worker and a TreeBuilder, the root
        element is always the same. The root element is also accessible in the
        builder's `root` attribute. But using this method you can be sure that
        you are dealing with a complete and fully intact tree.

        """
        with self._condition:
            if self._tree_state & REPLACE:
                if callback:
                    self.connect("tree_finished", callback, True, True)
                if not wait:
                    return
                self.wait_build()
            return self._builder.root

    def get_transform(self, wait=False, callback=None):
        """Return the transformed result.

        If wait is True, the call blocks until (tokenizing and) transforming is
        finished. If wait is False, None is returned if the transform is not
        yet ready.

        If a callback is given and transformation is not finished yet, that
        callback is called once when transforming is ready, with this
        :class:`Worker` as the sole argument.

        If no Transformer was set, None is returned always.

        """
        if self._transformer:
            with self._condition:
                if self._transform_state & REPLACE:
                    if callback:
                        self.connect("transform_finished", callback, True, True)
                    if not wait:
                        return
                    self.wait_transform()
                return self._transformer.result(self._builder.root)

    def slot_invalidate(self, context):
        """Called when TreeBuilder emits ``("invalidate", context)``.

        Clears the node and its parents from the transform cache.

        """
        if self._transformer:
            self._transformer.invalidate_node(context)

    def slot_replace(self):
        """Called when TreeBuilder emits ``"replace"``.

        Interrupts the transformer.

        """
        if self._transformer:
            self._transformer.interrupt(self._builder.root)

    def start_build(self):
        """Called when the build process starts.

        Emits the ``'started'`` event.

        """
        self.emit("started")

    def finish_build(self):
        """Called when the treebuilder is done.

        Emits ``'tree_updated', start, end`` and then ``'tree_finished'``,
        when the tree has been updated.

        """
        self.emit("tree_updated", self._builder.start, self._builder.end)
        self.emit("tree_finished")

    def finish_transform(self):
        """Called when the transform is finished.

        Emits ``'transform_finished'`` when the transform has been updated.

        """
        self.emit("transform_finished")


class BackgroundWorker(Worker):
    """A Worker implementation that does the work in a background thread."""
    def run_process(self):
        """Run the update process in a background thread."""
        threading.Thread(target=super().run_process).start()


class WorkerDocumentMixin:
    """Adds a Worker to a Document to automatically update the tokenized
    tree and the transformed result.

    Combine this class with a subclass of AbstractDocument (see the
    :mod:`.document` module).

    Everytime the text is modified, only the modified part is retokenized. If
    that changes the lexicon in which the last part (after the modified part)
    starts, that part is also retokenized, until the state (the list of active
    lexicons) matches the state of existing tokens.

    Also the transformed result, if a transformer is set, is updated.

    """
    def __init__(self, worker):
        """Initialize with a :class:`Worker` instance, which is doing the work."""
        self._worker = worker

    def worker(self):
        """Return the Worker we were instantiated with."""
        return self._worker

    def builder(self):
        """Return the worker's TreeBuilder."""
        return self._worker._builder

    def transformer(self):
        """Return the worker's Transformer, if set."""
        return self._worker._transformer

    def set_transformer(self, transformer):
        """Set a new Transformer in the worker.

        Specify None to remove the current transformer.

        .. seealso:: :meth:`Worker.set_transformer`

        """
        self._worker.set_transformer(transformer)

    def root_lexicon(self):
        """Return the currently set root lexicon."""
        return self.builder().root.lexicon

    def set_root_lexicon(self, root_lexicon):
        """Set the root lexicon to use to tokenize the text.

        Triggers an update of the tokenized tree.

        """
        self._worker.update(self.text(), root_lexicon)

    def get_root(self, wait=False, callback=None):
        """Get the root element of the completed tree.

        If wait is True, this call blocks until tokenizing is done, and the
        full tree is returned. If wait is False, None is returned if the tree
        is still busy being built.

        If a callback is given and tokenizing is still busy, that callback is
        called once when tokenizing is ready, with this Document as the
        sole argument.

        .. seealso:: :meth:`Worker.get_root`
        """
        if callback:
            callback = self._callback_to_self(callback)
        return self._worker.get_root(wait, callback)

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

    def get_transform(self, wait=False, callback=None):
        """Return the transformed result (if a Transformer is active in the Worker).

        If wait is True, the call blocks until (tokenizing and) transforming is
        finished. If wait is False, None is returned if the transform is not
        yet ready.

        If a callback is given and transformation is not finished yet, that
        callback is called once when transforming is ready, with this
        Document as the sole argument.

        .. seealso:: :meth:`Worker.get_transform`
        """
        if callback:
            callback = self._callback_to_self(callback)
        return self._worker.get_transform(wait, callback)

    def text_changed(self, start, removed, added):
        """Called after modification of the text.

        Retokenizes the modified part and updates the transformation.

        """
        self._worker.update(self.text(), False, start, removed, added)
        super().text_changed(start, removed, added)

    def token(self, pos):
        """Returns the token at the specified position, in an intuitive way.

        If a token starts at position, it is returned. Otherwise, if a token
        ends at position, it is returned. Will not return a token that is in a
        different block. Returns None if there are no tokens in the block.

        """
        token = self.get_root(True).find_token(pos)
        if token:
            if token.pos <= pos:
                return token
            # token is to the right, see if left token touches pos
            left_token = token.previous_token()
            if left_token and left_token.end == pos:
                return left_token
            # see if token (to the right) is on the same line
            if self.block_separator not in self[pos:token.pos]:
                return token

    def _callback_to_self(self, callback):
        """Return a callable that calls callback with self as first argument.

        The original first argument is ignored (that's the Worker). Does not
        store a reference to self.

        """
        selfref = weakref.ref(self)
        def cb(worker):
            self = selfref()
            if self:
                callback(self)
        return cb

