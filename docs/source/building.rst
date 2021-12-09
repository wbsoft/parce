Building and rebuilding a tree
==============================

Earlier we saw the simple function::

    import parce
    tree = parce.root(lexicon, text)

to get the tree with all tokens read from the text using the specified root
lexicon. This work is done by a :class:`~parce.treebuilder.TreeBuilder`.

There are many ways to use TreeBuilder, but first we will look at using it
directly.

Using TreeBuilder
-----------------

The TreeBuilder builds a tree by parsing text and is also capable of rebuilding
a tree partly when there are (smaller or larger) text changes. To build a tree
from new text::

    import parce.treebuilder
    builder = parce.treebuilder.TreeBuilder(lexicon)
    tree = builder.tree(text)

Although we do not need the builder anymore, it has some interesting info left
for us. After building, the ``lexicons`` attribute of the ``builder`` lists the
lexicons that were left open (if any) when the end of the document was reached.

This can be useful if we want to know that the source text was somehow
"complete" and all nested constructions were finished. For example, when
using the Nonsense.root lexicon from the Getting started section::

    >>> builder = parce.treebuilder.TreeBuilder(Nonsense.root)
    >>> tree = builder.tree(r'an "unfinished string')
    >>> builder.lexicons
    [Nonsense.string]

If we add a double quote, we see that there are no lexicons left open anymore::

    >>> tree = builder.tree(r'an "unfinished string"')
    >>> builder.lexicons
    []

The TreeBuilder also stores the region that was tokenized in its ``start``
and ``end`` attribute::

    >>> builder.start, builder.end
    (0, 22)

Now comes the interesting part. Instead of building the tree again,
we can just tell the builder about the changes to the text, and only retokenize
as few text as possible. We need to keep the TreeBuilder for this to work::

    >>> builder = parce.treebuilder.TreeBuilder(Nonsense.root)
    >>> builder.root.dump()
    <Context Nonsense.root at ?-? (0 children)>

We did not give it any text, so the root context is still empty.
Now we feed it the unfinished string::

    >>> builder.rebuild(r'an "unfinished string')
    >>> builder.lexicons
    [Nonsense.string]
    >>> builder.start, builder.end
    (0, 21)
    >>> builder.root.dump()
    <Context Nonsense.root at 0-21 (3 children)>
     ├╴<Token 'an' at 0:2 (Text)>
     ├╴<Token '"' at 3:4 (Literal.String)>
     ╰╴<Context Nonsense.string at 4-21 (1 child)>
        ╰╴<Token 'unfinished string' at 4:21 (Literal.String)>

Now we instruct the TreeBuilder that we want to append 1 character at position
21, a double quotation mark, so we finish the string::

    >>> builder.rebuild(r'an "unfinished string"', False, 21, 0, 1)
    >>> builder.root.dump()
    <Context Nonsense.root at 0-22 (3 children)>
     ├╴<Token 'an' at 0:2 (Text)>
     ├╴<Token '"' at 3:4 (Literal.String)>
     ╰╴<Context Nonsense.string at 4-22 (2 children)>
        ├╴<Token 'unfinished string' at 4:21 (Literal.String)>
        ╰╴<Token '"' at 21:22 (Literal.String)>
    >>> builder.lexicons
    []
    >>> builder.start, builder.end
    (21, 22)

Note that we gave the builder the full new text (because it does not store the
text anywhere), but we tell it explicitly at what position how many characters
were removed and added. We see that now there are no more lexicons open, and
that only the range 21 to 22 has been retokenized, the other tokens remained
the same.

TreeBuilder is quite smart in determining what to retokenize, for example when
the modified text would cause the tokens left from the insert position to be
changed, those changes would be handled as well. Actually the parser goes back
a reasonable amount of tokens to be sure that at least part of the old tokens
before the insertion position remain the same. When that is not the case, the
parser goes even back further.

And after the changed region, the old tokens are only reused in the case they
have exactly the same ancestry. Typing a character that opens a new context of
course changes the meaning of the following text, and also that is handled
correctly.

If you manually change the root lexicon, you need to call
:meth:`~parce.treebuilder.TreeBuilder.rebuild` in order to rebuild the tree
with the new root lexicon.


Using Worker
------------

.. currentmodule:: parce.work

When using the TreeBuilder directly, we can't take advantage of all the power
it provides; but using a :class:`Worker` we can for example run the
TreeBuilder in a background thread, and then it is even possible to modify the
text while a tree is being built. The Worker adds the text changes and the
TreeBuilder immediately adapts the build procedure, going back as far as
necessary, and resumes the parsing process.

You will need the Worker when you want to use parce for e.g. a GUI text editor,
that needs to stay responsive while tokenizing the text continuously.

An example::

    >>> import parce.work, parce.treebuilder
    >>> w = parce.work.BackgroundWorker(parce.treebuilder.TreeBuilder())
    >>> def func(worker):
    ...     print("Worker finished!")
    ...     print(worker.get_root())
    ...
    >>> text = open('parce/themes/default.css').read()
    >>> w.update(text, parce.find('css'));w.get_root(callback=func)
    >>> Worker finished!
    <Context Css.root at 0-4625 (208 children)>

Note that, for a :class:`BackgroundWorker`, :meth:`Worker.update` immediately
returns. Then :meth:`Worker.get_root` gets the root context if building already
has finished. But if not, it returns None and calls the callback when done, if
a callback was given. In this case, ``func`` got called in the background
thread.

When you really want to have the root context at a certain moment, and don't
mind having to wait a (very short) while, simply call
:meth:`Worker.get_root(True) <Worker.get_root>`. When you want to be updated on
*every* change to the tokenized tree, you can connect to one of the events that
is emitted by the Worker on certain moments.
