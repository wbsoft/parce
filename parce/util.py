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
import codecs
import contextlib
import functools
import threading
import types
import weakref


class Dispatcher:
    """Dispatches calls via an instance to methods based on the first argument.

    A Dispatcher is used as a decorator when defining a class, and then called
    via or in an instance to select a method based on the first argument (which
    must be hashable).

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

    To get the method for a key without calling it directly, e.g. to see of
    a method exists for a key, use::

        >>> meth = i.dispatch.get(1)   # returns a bound method
        >>> if meth:
        ...     meth("hi there")
        ...
        One called hi there

    If you specified a default method on creation of the dispatcher, that
    method is also accessible, in the ``default`` attribute::

        >>> i.dispatch.default(1, 2)
        Default function called: 1 2

    """

    def __init__(self, default_func=None):
        self._lock = threading.Lock()
        self._table = {}
        self._tables = weakref.WeakKeyDictionary()
        self._default_func = default_func

    def __set_name__(self, owner, name):
        self._name = name

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
            with self._lock:
                try:
                    table = self._tables[owner]
                except KeyError:
                    # find Dispatchers in base classes with the same name
                    # if found, inherit their references
                    dispatchers = []
                    for c in owner.mro():
                        d = c.__dict__.get(self._name)
                        if type(d) is type(self):
                            dispatchers.append(d)
                    _table = {}
                    for d in reversed(dispatchers):
                        _table.update(d._table)
                    # now, store the actual functions instead of their names
                    table = self._tables[owner] = {a: getattr(owner, name)
                                for a, name in _table.items()}
        return _Dispatcher(self, table, instance, owner)


class _Dispatcher:
    """Helper class for Dispatcher."""
    __slots__ = ("_dispatcher", "_table", "_instance", "_owner")
    def __init__(self, dispatcher, table, instance, owner):
        self._dispatcher = dispatcher
        self._table = table
        self._instance = instance
        self._owner = owner

    def __repr__(self):
        return "<{}.{} {}.{} of {}>".format(
            self._dispatcher.__class__.__module__,
            self._dispatcher.__class__.__name__,
            self._owner.__name__,
            self._dispatcher._name,
            repr(self._instance))

    def __call__(self, key, *args, **kwargs):
        """Call the stored method based on the key (first argument) with the
        other arguments."""
        f = self._table.get(key)
        if f:
            return f(self._instance, *args, **kwargs)
        f = self.default
        if f:
            return f(key, *args, **kwargs)

    @property
    def default(self):
        """The bound method specified as default, if any."""
        f = self._dispatcher._default_func
        if f:
            return f.__get__(self._instance, self._owner)

    def get(self, key):
        """Return the bound method for the key, without calling it."""
        f = self._table.get(key)
        if f:
            return f.__get__(self._instance, self._owner)


class _Observer:
    """Helper for Observable class.

    The magic lt/gt methods are to help with sorting on priority and the eq/ne
    methods to see if the function already is added to the list of slots.

    """
    __slots__ = ('func', 'once', 'priority', 'call')
    def __init__(self, func, once=None, prepend_self=False, priority=0):
        if isinstance(func, types.MethodType):
            func = weakref.WeakMethod(func)
            self.call = self.call_weakmethod_with_self if prepend_self else self.call_weakmethod
        else:
            self.call = func if prepend_self else self.call_func
        self.func = func
        self.once = once
        self.priority = priority

    def __repr__(self):
        return "<Observer for {}>".format(self.func)

    def __eq__(self, other):
        if type(other) is _Observer:
            return self.func == other.func
        return NotImplemented

    def __ne__(self, other):
        if type(other) is _Observer:
            return self.func != other.func
        return NotImplemented

    def __lt__(self, other):
        if type(other) is _Observer:
            return self.priority < other.priority
        return NotImplemented

    def __gt__(self, other):
        if type(other) is _Observer:
            return self.priority > other.priority
        return NotImplemented

    def call_func(self, observable, *args, **kwargs):
        return self.func(*args, **kwargs)

    def call_weakmethod(self, observable, *args, **kwargs):
        func = self.func()
        if func:
            return func(*args, **kwargs)
        self.once = True

    def call_weakmethod_with_self(self, observable, *args, **kwargs):
        func = self.func()
        if func:
            return func(observable, *args, **kwargs)
        self.once = True


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
        ``prepend_self`` is True, the callback is called with the observable
        itself as first argument.

        If the ``func`` is a method, it is stored using a weak reference.

        """
        observer = _Observer(func, once, prepend_self, priority)
        slots = self._callbacks.setdefault(event, [])
        if observer not in slots:
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

        Returns a :class:`contextlib.ExitStack` instance. When any of the
        connected callbacks returns a context manager, that context is entered,
        and added to the exit stack, so it is exited when the exit stack is
        exited.

        """
        s = contextlib.ExitStack()
        try:
            slots = self._callbacks[event]
        except KeyError:
            return s
        disconnect = []
        for i, observer in enumerate(slots):
            result = observer.call(self, *args, **kwargs)
            try:
                s.enter_context(result)
            except Exception:
                pass
            if observer.once:
                disconnect.append(i)
        if disconnect:
            for i in reversed(disconnect):
                del slots[i]
            if not slots:
                del self._callbacks[event]
        return s


class Switch:
    """A context manager that evaluates to True when in a context, else to False.

    Example::

        clicking = Switch()

        def myfunc():
            with clicking:
                blablabl()

        # and elsewhere:
        def blablabl():
            if not clicking:
                do_something()

        # when blablabl() is called from myfunc, clicking evaluates to True,
        # so do_something() is not called then.

    A Switch can also be used in a class definition; via the descriptor
    protocol it will then create per-instance Switch objects which will be
    stored using a weak reference to the instance. For example::

        class MyClass:
            clicking = Switch()

            def click_event(self, event):
                with self.clicking:
                    self.blablabla()

            def blablabla(self):
                do_something()
                if not self.clicking:
                    # this only runs when blablabla() was not called
                    # from click_event()
                    update_something()


    """
    __slots__ = ('_value',)

    def __init__(self):
        self._value = 0

    def __enter__(self):
        self._value += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._value -= 1

    def __bool__(self):
        return bool(self._value)

    def __get__(self, instance, owner):
        try:
            return self._value[instance]
        except TypeError:
            # value still was 0, replace it with a weakref dict
            self._value = weakref.WeakKeyDictionary()
        except KeyError:
            pass
        s = self._value[instance] = type(self)()
        return s


def object_locker():
    """Return a callable that can hold a lock on an object.

    The Lock is automatically created when requested for the first time, and
    deleted when released for the last time. Keeps a reference to the object
    until the last lock is released.

    Usage example::

        >>> lock = object_locker()
        >>> with lock(obj):
        ...     do_something()

    The lock callable should remain alive as long as the object is alive, so it
    is reused; it is the context where the locking is active. This function is
    an alternative to::

        >>> class Object:
        ...     def __init__(self):
        ...         self._lock = threading.Lock()
        ...
        >>> o = Object()

    and then later::

        >>> with o._lock:
        ...     do_something()

    In this use case the allocated Lock lives as long as the object, which
    might not be desirable if you have a large amount of objects of this type.

    """
    locker = {}
    locker_lock = threading.Lock()

    def lock_object(obj):
        with locker_lock:
            try:
                return locker[obj]
            except KeyError:
                lock = locker[obj] = threading.Lock()
                @contextlib.contextmanager
                def cleanup():
                    try:
                        with lock:
                            yield
                    finally:
                        del locker[obj]
                return cleanup()
    return lock_object


def cached_method(func):
    """Wrap a method and caches its return value.

    The method argument tuple should be hashable. Keyword arguments are not
    supported. The cache is thread-safe. Does not keep a reference to the
    instance.

    """
    lock = object_locker()
    cache = weakref.WeakKeyDictionary()

    @functools.wraps(func)
    def wrapper(self, *args):
        with lock(self):
            try:
                return cache[self][args]
            except KeyError:
                v = cache.setdefault(self, {})[args] = func(self, *args)
                return v
    return wrapper


def cached_property(func):
    """Like property, but caches the computed value."""
    return property(cached_method(func))


def cached_func(func):
    """Wrap a normal function and caches the return value.

    The function's argument tuple should be hashable; keyword arguments are not
    supported. The cache is thread-safe.

    """
    cache = caching_dict(func, True)
    @functools.wraps(func)
    def wrapper(*args):
        return cache[args]
    return wrapper


def caching_dict(func, unpack=False):
    """Create a dict with a thread-safe factory function for missing keys.

    When a key is not present, the factory function is called. The difference
    with :class:`collections.defaultdict` is that the factory function is
    called with the key as argument, or, if ``unpack`` is set to True, with the
    key arguments unpacked. Built-in locking makes sure another thread cannot
    call the factory function at the same time.

    """
    lock = threading.Lock()

    class cache(dict):
        if unpack:
            def __getitem__(self, key):
                with lock:
                    try:
                        return super().__getitem__(key)
                    except KeyError:
                        value = self[key] = func(*key)
                        return value
        else:
            def __getitem__(self, key):
                with lock:
                    try:
                        return super().__getitem__(key)
                    except KeyError:
                        value = self[key] = func(key)
                        return value
    return cache()


class Symbol:
    """An unique object that has a name; the same name returns the same object."""
    def __repr__(self):
        return self._name

    @cached_func
    def __new__(cls, name):
        obj = object.__new__(cls)
        obj._name = name
        return obj


def fix_boundaries(stream, start, end):
    """Yield all items from the stream of tuples.

    The first two items of each tuple are regarded as pos and end. This
    function adjusts the pos of the first item and the end of the last item so
    that they do not stick out of the range start..end. If the pos of the first
    item is below start, it is set to start; if the end of the last item is
    beyond end, it is set to end.

    If start == 0, the first item will never be adjusted; if end is None, the
    last item will not be adjusted.

    """
    if start == 0 and end is None:
        yield from stream   # do nothing
    else:
        stream = iter(stream)
        for i in stream:
            if i[0] < start:
                i = type(i)((start, i[1], *i[2:]))
            for j in stream:
                yield i
                i = j
            if end is not None and i[1] > end:
                i = type(i)((i[0], end, *i[2:]))
            yield i


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
    i = 0
    try:
        while True:
            j = l.index(separator, i)
            yield l[i:j]
            i = j + 1
    except ValueError:
        yield l[i:]


def unroll(obj):
    """Unroll a tuple or list.

    If the object is a tuple or list, yields the unrolled members recursively.
    Otherwise just the object itself is yielded.

    """
    if type(obj) in (tuple, list):
        for i in obj:
            yield from unroll(i)
    else:
        yield obj


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


