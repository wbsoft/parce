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
text is updated. It is possible to run those jobs in a background thread,
completely or partially.

The whole process is divided in certain stages, performed by exhausting the
:meth:`Worker.process` generator fully.

The Worker is intended to be used as the compagnon for the
:class:`~parce.Document` class and cause the TreeBuilder and (if set) the
Transformer to do their jobs in a configurable and flexible manner.

It is possible to wait for the parce tree of the transform result, or to
arrange for a callback to be called when the work is done.

Inherit Worker to implement other features or another way to use a background
thread for (parts of) the job.

"""

import threading

from . import util


IDLE      = 0       # result is up-to-date
BUILD     = 1       # result is still valid but not up-to-date
REPLACE   = 3       # result is invalid, in process of being replaced
DONE      = 4       # result is ready but finished callbacks still to be done


class Worker(util.Observable):
    """Runs the TreeBuilder and the Transformer.

    Initialize with a TreeBuilder and optionally a transformer. It is not
    possible to change the TreeBuilder later; but you can set another
    transformer, or use no transformer at all.

    Call :meth:`update` to re-run the treebuilder on changed text, or new text,
    or to use a new root lexicon.

    Call :meth:`set_transformer` to set another Transformer, which triggers
    a re-run of the transformer alone.

    """
    def __init__(self, treebuilder, transformer=None):
        super().__init__()
        self._builder = treebuilder
        self._transformer = transformer

        self._condition = threading.Condition()
        self._tree_state = IDLE
        self._transform_state = IDLE

        treebuilder.connect("invalidate", self.slot_invalidate)
        treebuilder.connect("replace", self.slot_replace)

    def builder(self):
        """Return the TreeBuilder we were initialized with."""
        return self._builder

    def set_transformer(self, transformer):
        """Set the :class:`~.transform.Transformer` to use.

        You may use one Transformer for multiple Workers.  Use None to
        remove the current transformer.

        Setting a new Transformer updates the transform result.
        This method should always be called from the main thread.

        """
        if transformer is not self._transformer:
            self._transformer = transformer
            with self._condition:
                if self._transform_state & REPLACE == 0:
                    self.start()

    def transformer(self):
        """Return the current Transformer, if set."""
        return self._transformer

    def update(self, text, root_lexicon=False, start=0, removed=0, added=None):
        """Start a process to update the tree and the transform.

        For the meaning of the arguments, see
        :meth:`.treebuilder.TreeBuilder.add_changes`.

        This method should always be called from the main thread.

        """
        self._builder.add_changes(text, root_lexicon, start, removed, added)
        if not self._builder.busy:
            self.start()

    def start(self):
        """Start the update process.

        Sets the initial state and then calls meth:`run_process`. This method
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

        ## run the treebuilder
        for stage in self._builder.process():
            yield "tree " + stage
            if stage == "replace":
                with c:
                    self._tree_state = REPLACE
        with c:
            self._tree_state = DONE
        self.finish_build()
        with c:
            self._tree_state = IDLE
            c.notify_all()

        ## run the transformer
        t, old = self._transformer, None
        if t:
            while t and t is not old:
                for stage in t.process(self._builder.root):
                    yield "transform " + stage
                    if stage == "replace":
                        with c:
                            self._transform_state = REPLACE
                # if the transformer was replaced while running, start again
                t, old = self._transformer, t
            with c:
                self._transform_state = DONE
            self.finish_transform()
        with c:
            self._transform_state = IDLE
            c.notify_all()

    def wait_build(self):
        """Implement to wait for the build job to be completed.

        The default implementation immediately returns.

        """
        with self._condition:
            while self._tree_state & REPLACE:
                self._condition.wait()

    def wait_transform(self):
        """Implement to wait for the transform job to be completed.

        The default implementation immediately returns.

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

    def finish_build(self):
        """Called when the treebuilder is done.

        Emits ``'tree_updated', (start, end)`` and then ``'tree_finished'``,
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


