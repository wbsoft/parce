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
This module defines the TreeBuilder, which is used to build() a tree structure
from a text, using a root lexicon.

Using the rebuild() method, TreeBuilder is also capable of regenerating only
part of an existing tree, e.g. when part of a long text is modified through a
text editor. It is smart enough to recognize whether existing tokens before and
after the modified region can be reused or not, and it reuses tokens as much as
possible.

BackgroundTreeBuilder can be used to tokenize a text into a tree in a background
thread.

"""


import sys
import contextlib
import itertools
import threading

from parce.action import DynamicAction
from parce.target import DynamicTarget
from parce.tree import Context, Token, _GroupToken


class TreeBuilder:
    """Build a tree directly from parsing the text.

    The root node of the tree is in the `root` instance attribute.

    After calling build() or rebuild(), three instance variables are set:

        start, end:
            indicate the region the tokens were changed. After build(), start
            is always 0 and end = len(text), but after rebuild(), these values
            indicate the range that was actually re-tokenized.

        lexicons:
            the list of open lexicons (excluding the root lexicon) at the end
            of the document. This way you can see in which lexicon parsing
            ended.

            If a tree was rebuilt, and old tail tokens were reused, the
            lexicons variable is not set, meaning that the old value is still
            valid. If the TreeBuilder was not used before, lexicons is then
            None.

    No other variables or state are kept, so if you don't need the above
    information anymore, you can throw away the TreeBuilder after use.

    """
    changes = None

    start = 0
    end = 0
    lexicons = None

    def __init__(self, root_lexicon=None):
        self.root = Context(root_lexicon, None)

    def tree(self, text):
        """Convenience method returning the tree with all tokens."""
        self.build(text)
        return self.root

    def build(self, text):
        """Tokenize the full text.

        Sets three instance variables start, end, lexicons). Start and end
        are always 0 and len(text), respectively. lexicons is a list of the
        lexicons that were not closed at the end of the text. (If the parser
        ended in the root context, the list is empty.)

        """
        self.rebuild(text, 0, 0, len(text))

    def rebuild(self, text, start, removed, added):
        """Tokenize the modified part of the text again and update the tree.

        Sets, just like build(), three instance variables start, end, lexicons,
        describing the region in the thext the tokens were changed. This range
        can be larger than (start, start + added).

        The text is the new text; start is the position where characters were
        removed and others added. The removed and added arguments are integers,
        describing how many characters were removed and added.

        This method finds the place we can start parsing again, and when the
        end of the modified region is reached, automatically recognizes when
        the rest of the tokens can be reused. When old tokens at the end are
        reused, the lexicons instance variable is not reset, the existing
        value is still relevant in that case.

        """
        if not self.root.lexicon:
            self.root.clear()
            self.start, self.end = start, start + added
            return

        # manage end, and record if there is text after the modified part (tail)
        end = start + removed
        tail = start + added < len(text)

        # we may be able to use existing tokens for the start if start > 0
        head = start > 0

        # record the position change for tail tokens that maybe are reused
        offset = added - removed

        # If there remains text after the modified part,
        # we try to reuse the old tokens
        if tail:
            # find the first token after the modified part
            end_token = self.root.find_token_after(end)
            if end_token:
                # make a subtree structure starting with this end_token
                tail_tree = end_token.split()
                tail_gen = ((t, t.pos + offset)
                    for t in tail_tree.tokens()
                        if not t.group or (t.group and t is t.group[0]))
                # store the new position the first tail token would get
                for tail_token, tail_pos in tail_gen:
                    break
                else:
                    tail = False
            else:
                tail = False

        lowest_start = sys.maxsize
        restart = True
        while restart:
            restart = False

            # find the last token before the modified part, we will start parsing
            # before that token. If there are no tokens, we just start at 0.
            # At least go back to just before a newline, if possible.
            if head:
                i = text.rfind('\n', 0, start)
                start_token = self.root.find_token_before(i) if i > -1 else None
                if not start_token:
                    start_token = self.root.find_token_before(start)
                    if start_token:
                        # go back some more tokens, you never know a longer match
                        # could be made. In very particular cases a longer token
                        # could be found. (That's why we tried to go back to a
                        # newline.)
                        gen = start_token.backward()
                        for start_token in itertools.islice(gen, 9):
                            pass
                        start_token = next(gen, None)
                if start_token:
                    # don't start in the middle of a group, as they originate from
                    # one single regexp match
                    if start_token.group:
                        start_token = start_token.group[0]

                    # make a short list of tokens from the start_token to the place
                    # we want to parse. We copy them because some might get moved to
                    # the tail self.root. If they were not changed, we can adjust the
                    # modified region.
                    start_tokens = [start_token.copy()]
                    for t in start_token.forward():
                        start_tokens.append(t.copy())
                        if t.end > start:
                            break
                    start_token_index = 0
                else:
                    head = False

            if head:
                # remove the start token and all tokens to the right
                pos = start = start_token.pos
                context = start_token.parent
                start_token.cut()
            else:
                pos = start = lowest_start = 0
                context = self.root
                context.clear()

            # start parsing
            done = False
            while not done:
                for pos, tokens, target in self.parse_context(context, text, pos):
                    if tokens:
                        if head:
                            # move start if the tokens before start didn't change
                            if (start_token_index + len(tokens) <= len(start_tokens) and
                                all(new.equals(old)
                                    for old, new in zip(start_tokens[start_token_index:], tokens))):
                                start = pos
                                start_token_index += len(tokens)
                            else:
                                start = tokens[0].pos
                                head = False    # stop looking further
                        if tail:
                            if tokens[0].pos > tail_pos:
                                for tail_token, tail_pos in tail_gen:
                                    if tail_pos >= tokens[0].pos:
                                        break
                                else:
                                    tail = False
                            if (tokens[0].pos == tail_pos
                                    and tokens[0].state_matches(tail_token)):
                                # we can attach the tail here.
                                if offset:
                                    # adjust the pos of the old tail tokens.
                                    # We don't use tail_token.forward() because
                                    # it uses parent_index() which depends on sorted
                                    # pos values
                                    tail_token.cut_left()
                                    for t in tail_tree.tokens():
                                        t.pos += offset
                                # add the old tokens to the current context
                                tail_token.join(context)
                                end = tail_pos
                                done = True
                                break
                        context.extend(tokens)
                        # we check for new changes here, so we always have tokens
                        # in the current context
                        if self.changes:
                            c = self.get_changes()
                            if c:
                                # break out and adjust the current tokenizing process
                                text = c.text
                                start = c.position
                                head = start > 0
                                if c.root_lexicon != False:
                                    self.root.lexicon = c.root_lexicon
                                    head = tail = False
                                elif tail:
                                    # reuse old tail?
                                    new_tail_pos = start + c.added
                                    if new_tail_pos >= len(text):
                                        tail = False
                                    else:
                                        offset += c.added - c.removed
                                        tail_pos += offset
                                        if new_tail_pos > tail_pos:
                                            for tail_token, tail_pos in tail_gen:
                                                if tail_pos >= new_tail_pos:
                                                    break
                                            else:
                                                tail = False
                                restart = done = True
                                break # restart at new start position
                    if target:
                        context = self.update_context(context, target)
                        break # continue with new context
                else:
                    end = len(text)
                    self.unwind(context)
                    break
        self.start, self.end = min(start, lowest_start), end

    def unwind(self, context):
        """Recursively remove the context from its parent if empty.

        Leaves the list of lexicons that were left open in the `lexicons`
        attribute. When parsing ended in the root context, that list is empty.

        """
        self.lexicons = []
        while context.parent:
            self.lexicons.append(context.lexicon)
            if not context:
                del context.parent[-1]
            context = context.parent

    def parse_context(self, context, text, pos):
        """Yield Token instances as long as we are in the current context."""
        for pos, txt, match, action, *target in context.lexicon.parse(text, pos):
            if txt:
                if isinstance(action, DynamicAction):
                    tokens = tuple(action.filter_actions(self, pos, txt, match))
                    if len(tokens) == 1:
                        tokens = Token(context, *tokens[0]),
                    else:
                        tokens = tuple(_GroupToken(context, *t) for t in tokens)
                        for t in tokens:
                            t.group = tokens
                else:
                    tokens = Token(context, pos, txt, action),
            else:
                tokens = ()
            if target and isinstance(target[0], DynamicTarget):
                target = target[0].target(match)
            yield pos + len(txt), tokens, target

    def update_context(self, context, target):
        """Move to another context depending on target."""
        for t in target:
            if isinstance(t, int):
                for pop in range(t, 0):
                    if context.parent:
                        if not context:
                            del context.parent[-1]
                        context = context.parent
                    else:
                        break
                for push in range(0, t):
                    context = Context(context.lexicon, context)
                    context.parent.append(context)
            else:
                context = Context(t, context)
                context.parent.append(context)
        return context

    def filter_actions(self, action, pos, txt, match):
        """Handle filtering via DynamicAction instances."""
        if isinstance(action, DynamicAction):
            yield from action.filter_actions(self, pos, txt, match)
        elif txt:
            yield pos, txt, action


class BackgroundTreeBuilder(TreeBuilder):
    """A TreeBuilder that can tokenize a text in a background thread.

    BackgroundTreeBuilder supports tokenizing in a background thread. You
    must specify changes to the document using the Changes object returned by
    the change() context manager method:

        with builder.change() as c:
            c.change_text("new text", position, removed, added)

    Tokenizing then starts in the background. During tokenizing it is still
    possible to add new changes using change(). You can add callbacks to the
    `updated_callbacks` attribute (using add_build_updated_callback()) that are
    called everytime the whole document is tokenized.

    You can also add callbacks to the `finished_callbacks` attribute, using
    add_finished_callback(); those are called once when all pending changes are
    processed and then forgotten again.

    To be sure you get a complete tree, call get_root().

    """
    def __init__(self, root_lexicon=None):
        super().__init__(root_lexicon)
        self.job = None
        self.changes = None
        self.lock = threading.Lock()
        self.updated_callbacks = []
        self.finished_callbacks = []

    @contextlib.contextmanager
    def change(self):
        """Return a Changes object and start a context to add changes."""
        with self.lock:
            c = self.changes or Changes()
            yield c
            if c.has_changes():
                self.changes = c
                self.start_processing()

    def start_processing(self):
        """Start a background job if needed."""
        if not self.job:
            self.job = threading.Thread(target=self.process_and_finish)
            self.job.start()

    def process_and_finish(self):
        """Call process_changes() and then finish_processing()."""
        self.process_changes()
        self.finish_processing()

    def process_changes(self):
        """Process changes as long as they are added. Called in the background."""
        c = self.get_changes()
        start = -1
        end = -1
        while c and c.has_changes():
            if c.root_lexicon != False and c.root_lexicon != self.root.lexicon:
                self.root.lexicon = c.root_lexicon
                self.build(c.text)
            else:
                self.rebuild(c.text, c.position, c.removed, c.added)
            start = self.start if start == -1 else min(start, self.start)
            end = self.end if end == -1 else max(c.new_position(end), self.end)
            c = self.get_changes()
        if start != -1:
            self.start = start
        if end != -1:
            self.end = end

    def finish_processing(self):
        """Called when process_changes() quits. Calls oneshot callbacks.

        In GUI applications, this method should run when the job has finished,
        in the GUI thread.

        """
        with self.lock:
            self.job = None
        # this happens when still changes were added.
        c = self.changes
        if c and c.has_changes():
            start, end = self.start, self.end
            self.process_changes()
            self.start = min(start, self.start)
            self.end = max(c.new_position(end), self.end)
        self.build_updated()
        while self.finished_callbacks:
            callback, args, kwargs = self.finished_callbacks.pop()
            callback(*args, **kwargs)

    def get_changes(self):
        """Get the changes once. To be used from within the thread."""
        with self.lock:
            c, self.changes = self.changes, None
            return c

    def wait(self):
        """Wait for completion if a background job is running."""
        job = self.job
        if job:
            job.join()

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
        with self.lock:
            job = self.job
            if not job:
                return self.root
            if callback:
                self.add_finished_callback(callback, args, kwargs)
        if wait:
            self.wait()
            return self.root

    def build_updated(self):
        """Called when a build() or rebuild() finished and the tree is complete.

        The default implementation calls all callbacks in the
        `updated_callbacks` attribute, with the (start, end) arguments. (The
        same values are also accessible in the `start` and `end` attributes.)

        """
        for cb in self.updated_callbacks:
            cb(self.start, self.end)

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


class Changes:
    """Store changes that have to be made to a tree.

    This object is used through TreeBuilder.change().
    Calling change_contents() merges new changes with the existing changes.
    Calling change_root_lexicon() stores a root lexicon change.
    On init and clear() the changes are reset.

    """
    __slots__ = "root_lexicon", "text", "position", "added", "removed"

    def __init__(self):
        self.root_lexicon = False   # meaning no change is requested
        self.text = ""
        self.position = -1          # meaning no text is altered
        self.removed = 0
        self.added = 0

    def __repr__(self):
        changes = []
        if self.root_lexicon != False:
            changes.append("root_lexicon: {}".format(self.root_lexicon))
        if self.position != -1:
            changes.append("text: {} -{} +{}".format(self.position, self.removed, self.added))
        if not changes:
            changes.append("(no changes)")
        return "<Changes {}>".format(', '.join(changes))

    def change_contents(self, text, position=0, removed=None, added=None):
        """Merge new change with existing changes.

        If added and removed are not given, all text after position is
        considered to be replaced.

        """
        if removed is None:
            removed = len(self.text) - position
        if added is None:
            added = len(text) - position
        self.text = text
        if self.position == -1:
            # there were no previous changes
            self.position = position
            self.removed = removed
            self.added = added
            return
        # determine the offset for removed and added
        if position + removed < self.position:
            offset = self.position - position - removed
        elif position > self.position + self.added:
            offset = position - self.position - self.added
        else:
            offset = 0
        # determine which part of removed falls inside existing changes
        start = max(position, self.position)
        end = min(position + removed, self.position + self.added)
        offset -= max(0, end - start)
        # set the new values
        self.position = min(self.position, position)
        self.removed += removed + offset
        self.added += added + offset

    def change_root_lexicon(self, text, root_lexicon):
        """Store a root lexicon change."""
        self.text = text
        self.root_lexicon = root_lexicon

    def has_changes(self):
        """Return True when there are actually changes."""
        return self.position != -1 or self.root_lexicon != False

    def new_position(self, pos):
        """Return how the current changes would affect an older position."""
        if pos < self.position:
            return pos
        elif pos < self.position + self.removed:
            return self.position + self.added
        return pos - self.removed + self.added

