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
Various utility classes and functions.

This module only depends on the Python standard library.

"""

import bisect
import re
import codecs
import contextlib
import functools
import threading
import weakref


class Dispatcher:
    """Dispatches calls via an instance to methods based on the first argument.

    A Dispatcher is used as a decorator when defining a class, and then called
    via an instance to select a method based on the first argument (which must
    be hashable).

    If you override methods in a subclass that were dispatched, the
    dispatcher automatically dispatches to the new method. If you want to add
    new keywords in a subclass, just create a new Dispatcher with the same
    name. It will automatically inherit the references stored in the old
    dispatcher.

    Usage::

        class MyClass:
            dispatch = Dispatcher()

            @dispatch(1)
            def call_one(self, value):
                print("One called", value)

            @dispatch(2)
            def call_two(self, value):
                print("Two called", value)

            def handle_input(self, number, value):
                self.dispatch(number, value)

        >>> i = MyClass()
        >>> i.handle_input(2, 3)
        Two called 3

    Values of the first argument that are not handled are normally silently
    ignored, but you can also specify a default function, that is called when
    a value is not handled::

        class MyClass:
            @Dispatcher
            def dispatch(self, number, value):
                print("Default function called:", number, value)

            @dispatch(1)
            def call_one(self, value):
                print("One called", value)

            @dispatch(2)
            def call_two(self, value):
                print("Two called", value)

            def handle_input(self, number, value):
                self.dispatch(number, value)

        >>> i = MyClass()
        >>> i.handle_input(3, 10)
        Default function called: 3 10


    """

    def __init__(self, default_func=None):
        self._table = {}
        self._tables = weakref.WeakKeyDictionary()
        self._default_func = default_func

    def __call__(self, *args):
        def decorator(func):
            for a in args:
                self._table[a] = func.__name__
            return func
        return decorator

    def __get__(self, instance, owner):
        try:
            table = self._tables[owner]
        except KeyError:
            # find our name, and find Dispatchers in base classes with same name
            # if found, inherit their references
            if self._default_func:
                mro = iter(owner.mro()[1:])
                name = self._default_func.__name__
            else:
                mro = iter(owner.mro())
                def get_name():
                    for c in mro:
                        for n, v in c.__dict__.items():
                            if v is self:
                                return n
                name = get_name()
            dispatchers = []
            for c in mro:
                d = c.__dict__.get(name)
                if type(d) is type(self):
                    dispatchers.append(d)
            _table = {}
            for d in reversed(dispatchers):
                _table.update(d._table)
            _table.update(self._table)
            # now, store the actual functions instead of their names
            table = self._tables[owner] = {a: getattr(owner, name)
                        for a, name in _table.items()}
        def func(key, *args, **kwargs):
            f = table.get(key)
            if f:
                return f(instance, *args, **kwargs)
            if self._default_func:
                return self._default_func(instance, key, *args, **kwargs)
        return func


class _Observer:
    """Helper for Observable class.

    The magic lt/gt methods are to help with sorting on priority and the eq/ne
    methods to see if the function already is added to the list of slots.

    """
    __slots__ = ('func', 'once', 'priority', 'call')
    def __init__(self, func, once=None, prepend_self=False, priority=0):
        self.func = func
        self.once = once
        self.priority = priority
        if prepend_self:
            self.call = func    # Observable calls with self prepended
        else:
            self.call = lambda self, *args, **kwargs: func(*args, **kwargs)

    def __eq__(self, other):
        if type(other) == type(self):
            return self.func == other.func
        return super().__eq__(other)

    def __ne__(self, other):
        if type(other) == type(self):
            return self.func != other.func
        return super().__ne__(other)

    def __lt__(self, other):
        if type(other) == type(self):
            return self.priority < other.priority
        return super().__lt__(other)

    def __gt__(self, other):
        if type(other) == type(self):
            return self.priority > other.priority
        return super().__gt__(other)


class _EmitResult(list):
    """Encapsulates the results of an Observer.emit() call.

    When is it used as a context manager, it enters all results
    that are a context manager as well.

    """
    __slots__ = ('exitstack')
    def __enter__(self):
        self.exitstack = s = contextlib.ExitStack()
        for m in self:
            if hasattr(m, '__enter__') and hasattr(m, '__exit__'):
                s.enter_context(m)
        return s.__enter__()

    def __exit__(self, *exc):
        return self.exitstack.__exit__(*exc)


class Observable:
    """Simple base class for objects that need to announce events.

    Use :meth:`connect` to add a callable to be called when a certain event
    occurs.

    To announce an event from inside methods, use :meth:`emit`. In your
    documentation you should specify *which* arguments are used for *which*
    events; in order to keep this class simple and fast, no checking is
    performed whatsoever.

    Example::

        >>> o = Observable()
        >>>
        >>> def slot(arg):
        ...     print("slot called:", arg)
        ...
        >>> o.connect('test', slot)
        >>>
        >>> o.emit('test', 1)   # in a method of your Observable subclass
        slot called: 1

    Is is also possible to use :meth:`emit` in a :python:ref:`with <with>`
    context. In that case the return values of the connected functions are
    collected and if they are a context manager, they are entered as well. An
    example::

        >>> import contextlib
        >>>
        >>> @contextlib.contextmanager
        ... def f():
        ...     print("one")
        ...     yield
        ...     print("two")
        ...
        >>> o=Observable()
        >>> o.connect('test', f)
        >>>
        >>> with o.emit('test'):
        ...     print("Yo!!!")
        ...
        one
        Yo!!!
        two

    This enables you to announce events, and connected objects can perform a
    task before the event's context starts and another task when the event's
    context exits.

    """
    def __init__(self):
        self._callbacks = {}

    def connect(self, event, func, once=False, prepend_self=False, priority=0):
        """Register a function to be called when a certain event occurs.

        The ``event`` should be a string or any hashable object that identifies
        the event. The ``priority`` determines the order the functions are
        called. Lower numbers are called first. If ``once`` is set to True, the
        function is called once and then removed from the list of callbacks. If
        ``prepend_self`` is True, the callback is called with the treebuilder
        itself as first argument.

        """
        observer = _Observer(func, once, prepend_self, priority)
        slots = self._callbacks.setdefault(event, [])
        try:
            slots.remove(observer)
        except ValueError:
            pass
        bisect.insort_right(slots, observer)

    def disconnect(self, event, func):
        """Remove a previously registered callback function."""
        try:
            slots = self._callbacks[event]
        except KeyError:
            return
        observer = _Observer(func)
        try:
            slots.remove(observer)
        except ValueError:
            return
        if not slots:
            del self._callbacks[event]

    def disconnect_all(self, event=None):
        """Disconnect all functions (from the event).

        If event is None, disconnects all connected functions from all events.

        """
        if event is None:
            self._callbacks.clear()
        else:
            try:
                del self._callbacks[event]
            except KeyError:
                pass

    def has_connections(self, event):
        """Return True when there is at least one callback registered for the event.

        This can be used before performing some task, the task maybe then can
        be optimized because we know nobody needs the events.

        """
        return event in self._callbacks

    def is_connected(self, event, func):
        """Return True if func is connected to event."""
        try:
            slots = self._callbacks[event]
        except KeyError:
            return False
        return _Observer(func) in slots

    def emit(self, event, *args, **kwargs):
        """Call all callbacks for the event.

        Returns a list of the return values of all callbacks. When using this
        list in a ``with`` context, all return values that are context
        managers, are entered. (The list is an :class:`_EmitResult` object that
        extends Python's :class:`list` builtin, so that it can be used as a
        context manager.)

        """
        results = _EmitResult()
        try:
            slots = self._callbacks[event]
        except KeyError:
            return results
        disconnect = []
        for i, observer in enumerate(slots):
            results.append(observer.call(self, *args, **kwargs))
            if observer.once:
                disconnect.append(i)
        if disconnect:
            for i in reversed(disconnect):
                del slots[i]
            if not slots:
                del self._callbacks[event]
        return results


class Symbol:
    """An unique object that has a name."""
    __slots__ = ('_name_',)
    _store_ = {}
    _lock_ = threading.Lock()
    def __new__(cls, name):
        with cls._lock_:
            try:
                obj = cls._store_[name]
            except KeyError:
                obj = cls._store_[name] = object.__new__(cls)
                obj._name_ = name
            return obj

    def __repr__(self):
        return self._name_


def cached_method(func):
    """Wrap a method and caches its return value.

    The method argument tuple should be hashable. Keyword arguments are not
    supported. The cache is thread-safe. Does not keep a reference to the
    instance.

    """
    _cache = weakref.WeakKeyDictionary()
    _locker = weakref.WeakKeyDictionary()
    _lock = threading.Lock()

    def lock(obj):
        with _lock:
            try:
                return _locker[obj]
            except KeyError:
                lock = _locker[obj] = threading.Lock()
                return lock

    @functools.wraps(func)
    def wrapper(self, *args):
        try:
            return _cache[self][args]
        except KeyError:
            with lock(self):
                try:
                    return _cache[self][args]
                except KeyError:
                    v = _cache.setdefault(self, {})[args] = func(self, *args)
                    return v
    return wrapper


def cached_property(func):
    """Like property, but caches the computed value."""
    return property(cached_method(func))


def merge_adjacent(stream, factory=tuple):
    """Yield items from a stream of tuples.

    The first two items of each tuple are regarded as pos and end.
    If they are adjacent, and the rest of the tuples compares the same,
    the items are merged.

    Instead of the default factory `tuple`, you can give a named tuple
    or any other type to wrap the streams items in.

    """
    stream = iter(stream)
    for pos, end, *rest in stream:
        for npos, nend, *nrest in stream:
            if nrest != rest or npos > end:
                yield factory(pos, end, *rest)
                pos, rest = npos, nrest
            end = nend
        yield factory(pos, end, *rest)


def merge_adjacent_actions(tokens):
    """Yield three-tuples (pos, end, action).

    Adjacent actions that are the same are merged into
    one range.

    """
    return merge_adjacent((t.pos, t.end, t.action) for t in tokens)


def merge_adjacent_actions_with_language(tokens):
    """Yield four-tuples (pos, end, action, language).

    Adjacent actions that are the same and occurred in the same language
    are merged into one range.

    """
    return merge_adjacent((t.pos, t.end, t.action, t.parent.lexicon.language)
                          for t in tokens)


def get_bom_encoding(data):
    """Get the BOM (Byte Order Mark) of data, if any.

    A two-tuple is returned (encoding, data). If the data starts with a BOM
    mark, its encoding is determined and the BOM mark is stripped off.
    Otherwise, the returned encoding is None and the data is returned
    unchanged.

    """
    for bom, encoding in (
        (codecs.BOM_UTF8, 'utf-8'),
        (codecs.BOM_UTF16_LE, 'utf_16_le'),
        (codecs.BOM_UTF16_BE, 'utf_16_be'),
        (codecs.BOM_UTF32_LE, 'utf_32_le'),
        (codecs.BOM_UTF32_BE, 'utf_32_be'),
            ):
        if data.startswith(bom):
            return encoding, data[len(bom):]
    return None, data


def split_list(l, separator):
    """Split list on items that compare equal to separator.

    Yields result lists that may be empty.

    """
    try:
        i = l.index(separator)
    except ValueError:
        yield l
    else:
        yield l[:i]
        yield from split_list(l[i+1:], separator)


def quote(s):
    """Like repr, but return s with double quotes, escaping " and \\."""
    return '"' + re.sub(r'([\\"])', r'\\\1', s) + '"'


def tokens(nodes):
    """Helper to yield tokens from the iterable of nodes."""
    for n in nodes:
        if n.is_token:
            yield n
        else:
            yield from n.tokens()


def tokens_bw(nodes):
    """Helper to yield tokens from the iterable in backward direction.

    Make sure nodes is already in backward direction.

    """
    for n in nodes:
        if n.is_token:
            yield n
        else:
            yield from n.tokens_bw()


