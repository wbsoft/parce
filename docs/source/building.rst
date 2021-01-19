Building and rebuilding a tree
==============================

Earlier we saw the simple function::

    import parce
    tree = parce.root(lexicon, text)

to get the tree with all tokens read from the text using the specified root
lexicon. This work is done by a :py:mod:`TreeBuilder <parce.treebuilder>`.

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

If you manually change the root lexicon, you need to call ``rebuild()`` in
order to rebuild the tree with the new root lexicon.


Using BackgroundTreeBuilder
---------------------------

The :py:class:`BackgroundTreeBuilder <parce.treebuilder.BackgroundTreeBuilder>`
builds upon the TreeBuilder, adding functionality to perform the tokenization
of text in a background thread, which can be important when using parce in
GUI applications.

A BackgroundTreeBuilder is instantiated the same as a TreeBuilder, preferably
with a root lexicon, but updates are managed differently.

You can just call ``rebuild()`` like before, but it returns immediately, and the
(re)building of the tree happens in the background.

The :meth:`~parce.treebuilder.BackgroundTreeBuilder.get_root`
method is used to be notified when parsing is ready. It can be used for three
things:

* just knowing parsing is ready: when ``get_root()`` returns None you know
  parsing is not yet finished. Otherwise the tree is returned.

* get called back when parsing is done: ``get_root(callback=func)`` calls ``func``
  when parsing is finished

* just hang on waiting...: ``get_root(True)`` awaits the process if needed and
  returns the finished tree.

You can also connect to emitted events, for example using::

    builder.connect("updated", func)

The supplied ``func`` will then be called with two arguments ``start`` and
``end`` that denote the range that was re-tokenized.

Finally you can also inherit from BackgroundTreeBuilder and reimplement
the ``process_finished()`` method to do anything you like.

Of course you can also access the tree directly via the root element, but it is
not recommended to do so while parsing is busy, because you won't get reliable
results.

For more information, study the documentation and source code of the
:mod:`~parce.treebuilder` module.



