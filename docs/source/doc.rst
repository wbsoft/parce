The Document class
==================

*parce* provides a ``Document`` which can keep the text, collect changes
to the text and internally call the TreeBuilder to process the changes. The
Document simply behaves as a *mutable string* with some extra features.

To instantiate a Document::

    import parce
    from parce.lang.xml import Xml   # just for example

    d = parce.Document()
    d.set_root_lexicon(Xml.root)
    d.set_text(r'<xml attr="value">')

You can also give root lexicon and text on instantiation::

    d = parce.Document(Xml.root, r'<xml attr="value">')

To get the tree::

    >>> tree = d.get_root(True) # same args as TreeBuilder.get_root()
    >>> tree.dump()
    <Context Xml.root at 0-18 (3 children)>
     ├╴<Token '<' at 0:1 (Delimiter)>
     ├╴<Token 'xml' at 1:4 (Name.Tag)>
     ╰╴<Context Xml.attrs at 5-18 (5 children)>
        ├╴<Token 'attr' at 5:9 (Name.Attribute)>
        ├╴<Token '=' at 9:10 (Delimiter.Operator)>
        ├╴<Token '"' at 10:11 (Literal.String)>
        ├╴<Context Xml.dqstring at 11-17 (2 children)>
        │  ├╴<Token 'value' at 11:16 (Literal.String)>
        │  ╰╴<Token '"' at 16:17 (Literal.String)>
        ╰╴<Token '>' at 17:18 (Delimiter)>


Accessing and modifying text
----------------------------

All text is available through the ``text()`` method, and, just like a Python
string, a fragment of text in the Document can be read using the ``[ ]``
syntax::

    >>> d.text()
    '<xml attr="value">'
    >>> d[5:17]
    'attr="value"'

But you can also modify the text, using the slice syntax::

    >>> d[11:16]="Something Completely Else!!"
    >>> d.text()
    '<xml attr="Something Completely Else!!">'
    >>> d.get_root(True).dump()
    <Context Xml.root at 0-40 (3 children)>
     ├╴<Token '<' at 0:1 (Delimiter)>
     ├╴<Token 'xml' at 1:4 (Name.Tag)>
     ╰╴<Context Xml.attrs at 5-40 (5 children)>
        ├╴<Token 'attr' at 5:9 (Name.Attribute)>
        ├╴<Token '=' at 9:10 (Delimiter.Operator)>
        ├╴<Token '"' at 10:11 (Literal.String)>
        ├╴<Context Xml.dqstring at 11-39 (2 children)>
        │  ├╴<Token 'Something Completely Else!!' at 11:38 (Literal.String)>
        │  ╰╴<Token '"' at 38:39 (Literal.String)>
        ╰╴<Token '>' at 39:40 (Delimiter)>

Note that we requested the tree again (and awaited it being tokenized) using
``get_root(True)``, but the tree returned will always be the same object, for
the lifetime of the Document (or to be more precise, of the TreeBuilder the
document internally uses).

Using ``Document.modified_range()`` we get information about the part that
was retokenized since the last change::

    >>> d.modified_range()
    (11, 38)

This information is provided by the TreeBuilder. Using
``Document.open_lexicons()`` we can get the list of lexicons that the
TreeBuilder found to be left open by the document::

    >>> d.open_lexicons()
    [Xml.tag]

In this case, because the xml tag was not closed, an ``Xml.tag`` context was
left open. We can change that. Using ``Document.insert()`` we add one
character::

    >>> d.insert(39, '/')
    >>> d.open_lexicons()
    []
    >>> d.get_root().last_token()
    <Token '/>' at 39:41 (Delimiter)>
    >>> d.modified_range()
    (39, 41)

Instead of ``insert()``, we could also have written ``d[39:39]='/'``.


Performing multiple edits in once
---------------------------------

When you have a Document and you have found that you want to perform multiple
edits in one go, you can start a ``with`` context, and apply changes using the
slice syntax. Those changes may not overlap. The document does not change
during these edits, so all ranges remain valid during the process.

Only when the ``with`` block is exited, the changes are applied and the tree
of tokens is updated::

    >>> from parce.action import Name
    >>> with d:
    ...     for token in d.get_root().query.all.action(Name.Tag):
    ...         d[token.pos:token.end] = "yo:" + token.text.upper()
    ...
    >>> d.text()
    '<yo:XML attr="Something Completely Else!!"/>'

This incantation replaces all XML tag names with the same name in upper case
and with ``"yo:"`` prepended.


Cursor and Block
----------------

Related to Document are :class:`~parce.document.Cursor` and
:class:`~parce.document.Block`.

A Cursor simply describes a position (``pos``) in the document, or a selected
range (from ``pos`` to ``end``). If you write routines that inspect the tokens
and then change the text in some way, you can write them so that they expect
the cursor as argument, so they get the cursor's Document, the selected range
and the tokenized tree in one go.

A cursor keeps its position updated as the Document changes, as long as you
keep a reference to it.

A Block describes a line of text and is instantiated using
:meth:`Document.find_block() <parce.document.AbstractDocument.find_block>`,
:meth:`Document.blocks() <parce.document.AbstractDocument.blocks>`,
:meth:`Cursor.block() <parce.document.Cursor.block>` or
:meth:`Cursor.blocks() <parce.document.Cursor.blocks>`,
and then knows its ``pos`` and ``end`` in the Document. You can easily iterate
over lines of text using the ``blocks()`` methods.


Getting at the tokens
---------------------

Of course, you can get to the tokens by examining the tree, but there are a few
convenience methods. :meth:`Document.token(pos)
<parce.treedocument.TreeDocumentMixin.token>` returns the token closest at the
specified position (and on the same line), and :meth:`Cursor.token()
<parce.document.Cursor.token>` does the same. :meth:`Cursor.tokens()
<parce.document.Cursor.tokens>` yields the tokens in the selected range, if
any.

:meth:`Block.tokens() <parce.document.Block.tokens>` returns a tuple of the
tokens at that line::

    >>> from parce import Document
    >>> from parce.lang.css import Css
    >>> d = Document(Css.root, open('parce/themes/default.css').read())
    >>> b = d.find_block(200)
    >>> b.tokens()
    (<Token 'background' at 203:213 (Name.Property.Definition)>, <Token ':' at 213:214 (Delimiter)>,
    <Token 'ivory' at 215:220 (Literal.Color)>, <Token ';' at 220:221 (Delimiter)>)


More goodies
------------

The ``parce.Document`` class is in fact built from two base classes:
``AbstractDocument``/``Document`` from the :py:mod:`document <parce.document>`
module and ``TreeDocumentMixin`` from the :py:mod:`treedocument
<parce.treedocument>` module.

Using both base classes, it is not difficult to design a class that wraps an
object representing a text document in a GUI editor. You need only to provide
two methods in your wrapper: ``text()`` to get all text, and
``_update_contents()`` to change the text programmatically. When the text is
changed, AbstractDocument calls ``contents_changed``, which in
``TreeDocumentMixin`` is implemented to inform the TreeBuilder about a part of
text that needs to be retokenized. Also your wrapper class should call
``contents_changed`` whenever the user has typed in the editor.

Because a Document is basically a mutable string, we added some more nice
methods to perform certain actions like search, replace, and substitution using
regular expressions. And even undo/redo! See the :doc:`document module's
documentation <document>`.
