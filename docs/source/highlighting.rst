Syntax highlighting
===================

The standard actions used in the bundled languages can be mapped to colors and
other text formatting properties, so text in any language can be highlighted in
a pretty way, to improve readability.


How it works
------------

In *parce*, this work is done by combining a
:class:`~parce.formatter.Formatter` with a :class:`~parce.theme.Theme`.

A Formatter iterates over the tokens in a selected range and yields
:class:`~parce.formatter.FormatRange` tuples, describing how a certain piece
of text should be formatted. A format range consists of a starting position
``pos``, an ending position ``end`` and a format ``textformat``.

This textformat is provided by the theme, which maps a standard action to a
:class:`~parce.theme.TextFormat`, and converted to something the formatter can
use using a factory function that is specified when creating the formatter.

A TextFormat provided by the theme is a simple data object with attributes
that define text properties, such as color, font, decoration etc. The default
Theme implementation reads these properties from a CSS (Cascading Style Sheets)
file. Some CSS themes are provided, in the :mod:`~parce.themes` directory.

You can implement any kind of formatting by creating a Formatter with your
factory function, and then iterating over
:meth:`~parce.formatter.AbstractFormatter.format_ranges`.

Optionally, you can inherit from Formatter to implement useful other methods.
In :mod:`parce.out` there are some modules containing often used formatting
utilities.


Creating HTML output
--------------------

Using the :mod:`parce.out.html` module, it is easy to convert tokenized text to
HTML. Here is an example. Let's say we've got a document containing some XML
text::

    >>> import parce
    >>> doc = parce.Document(parce.find("xml"), '''<xml attr="value">text</xml>\n''')

We create a cursor that selects all text (a formatter can also just format
a selection of the text)::

    >>> cur = parce.Cursor(doc, 0, None)

We load a theme, using the ``parce/themes/dark.css`` included CSS theme::

    >>> theme = parce.theme_by_name('dark')

And create an HTML formatter::

    >>> from parce.out.html import HtmlFormatter
    >>> f = HtmlFormatter(theme)

Now we call the formatter to format the selected part of the document::

    >>> print(f.full_html(cur))
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8"/>
      </head>
      <body>
        <div class="parce">
    <pre style="white-space: pre; background-color: #000000; color: #fffff0; fon
    t-family: monospace;">&lt;<span style="color: #87cefa; font-weight: bold;">x
    ml</span> <span style="color: #1e90ff;">attr</span>=<span style="color: #cd5
    c5c;">"value"</span>&gt;text&lt;/<span style="color: #87cefa; font-weight: b
    old;">xml</span>&gt;
    </pre>
        </div>
      </body>
    </html>


Creating your own themes
------------------------

The easiest way to create your own theme is by copying ``default.css`` or
``_template.css`` in the ``themes/`` directory to a new file and start editing
that.

CSS properties
^^^^^^^^^^^^^^

The following subset of CSS properties is supported by the default TextFormat
used by the theming engine:

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Property:
      - Supported values:

    * - ``color``
      - named CSS color (like ``antiquewhite``), hex color (like ``#02030A``)
        with optional alpha value, ``rgb()`` and ``rgba()`` colors.

    * - ``background-color``
      - same as ``color``

    * - ``background``
      - only colors are supported, same as ``color``

    * - ``text-decoration-color``
      - same as ``color``

    * - ``text-decoration-line``
      - one or more of ``underline``, ``overline``, ``line-through`` and ``none``

    * - ``text-decoration-style``
      - one of ``solid``, ``double``, ``dotted``, ``dashed`` or ``wavy``

    * - ``text-decoration``
      - in order a color, line, and style value

    * - ``font-family``
      - one or more generic or quoted font names; generic names are:
        ``serif``, ``sans-serif``, ``monospace``, ``cursive``, ``fantasy``,
        ``system-ui``, ``math``, ``emoji`` and ``fangsong``.

    * - ``font-kerning``
      - one of ``auto``, ``normal`` or ``none``

    * - ``font-size``
      - one of ``xx-small``, ``x-small``, ``small``, ``medium``, ``large``,
        ``x-large``, ``xx-large``, ``xxx-large``, ``larger``, ``smaller`` or
        a numeric value, optionally with a ``%`` or unit like ``pt``, ``em`` etc.

    * - ``font-stretch``
      - one of ``ultra-condensed``, ``extra-condensed``, ``condensed``,
        ``semi-condensed``, ``semi-expanded``, ``expanded``, ``extra-expanded``
        or ``ultra-expanded``, or a numerical value with a ``%``.

    * - ``font-style``
      - ``normal``, ``italic``, or ``oblique`` with an optional slant value and unit

    * - ``font-variant-caps``
      - one of ``normal``, ``small-caps``, ``all-small-caps``, ``petite-caps``,
        ``all-petite-caps``, ``unicase``, ``titling-caps``

    * - ``font-variant-position``
      - one of ``normal``, ``sub``, or ``super``

    * - ``font-weight``
      - one of ``normal``, ``bold``, ``lighter``, ``bolder``, or a number

    * - ``font``
      - all of the above ``font-*`` properties, or one of: ``caption``,
        ``icon``, ``menu``, ``message-box``, ``small-caption``, ``status-bar``


.. note::

   It is possible that not all formatters support all properties. For
   example Qt5's QTextCharFormat does not support double underline.


CSS classes
^^^^^^^^^^^

To determine the style properties to use for a token, the token's action
(which must be a standard action) is mapped to one or more CSS classes.
This is described in :doc:`theme`, under "Mapping actions to CSS classes."
The matching CSS rules are then combined to determine the actual style
properties to use for the action.

All rules should have a ``.parce`` ancestor class selector, so that the theme
css file can directly be used in HTML (where tokens are mapped to class names,
e.g. using the :class:`~parce.out.html.SimpleHtmlFormatter`), without much
chance that other parts of a web page's style are clobbered by the parce css
file, for example:

.. code-block:: css

   .parce
   .comment {
       color: dimgray;
       font-family: serif;
       font-style: italic;
   }

This maps the ``Comment`` standard action to these color and font settings.

General classes
^^^^^^^^^^^^^^^

There are some special classes that define other style aspects than that of
individual tokens:


.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - CSS Selector
     - defines properties to use for:

   * - ``.parce``
     - the text view or block as a whole; e.g. a text editor window, or an HTML
       ``<pre>`` block. A text editor is free to ignore font settings.

   * - ``.parce.current-line``
     - the line the cursor is in (only *background* probably makes sense)

   * - ``.parce::selection``
     - text selected by the user (also works in straight HTML in a modern browser)

   * - ``.parce.current-line:focus``
     - the current line when the window has focus

   * - ``.parce::selection:focus``
     - selected text when the window has focus

   * - ``.parce:disabled``
     - the text editor widget when it is disabled (i.e. the user can't interact
       with it). If a text editor supports this at all, probably only the
       changed colors will be used (via a widget's palette), not the font.

   * - ``.parce.current-line:disabled``
     - the current line when the text widget is disabled

   * - ``.parce::selection:disabled``
     - selected text when the text widget is disabled

   * - ``.parce.leading-whitespace``
     - highlighting leading whitespace, if desired.
       Not supported by the default formatter, but a text editor could implement
       this and use a color from the theme.

   * - ``.parce.trailing-whitespace``
     - highlighting trailing whitespace, if desired.
       Not supported by the default formatter, but a text editor could implement
       this and use a color from the theme.

   * - ``.parce.eol-marker``
     - drawing an "end-of-line" marker, if desired.
       Not supported by the default formatter, but a text editor could implement
       this and use a color from the theme.


Using multiple themes together
------------------------------

Suppose you want to highlight tokens from embedded pieces of a different
language with a different theme. E.g. you have document containing HTML markup
and want to highlight embedded CSS with a different color theme.

To do this, you create a formatter and then add other themes for specific
languages::

    >>> import parce
    >>> doc = parce.Document(parce.find("html"), '''
    <html>
    <head>
    <style type="text/css">
    h2 {
        color: green;
    }
    </style>
    </head>
    </html>
    ''')
    >>> from parce.out.html import HtmlFormatter
    >>> f = HtmlFormatter(parce.theme_by_name('default'))
    >>> f.add_theme(parce.find("css").language, parce.theme_by_name('dark'))
    >>> print(f.full_html(parce.Cursor(doc, 0, None)))
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8"/>
      </head>
      <body>
        <div class="parce">
    <pre style="white-space: pre; background-color: #fffff0; color: #000000; font-family: monospace;">
    &lt;<span style="color: #00008b; font-weight: bold;">html</span>&gt;
    &lt;<span style="color: #00008b; font-weight: bold;">head</span>&gt;
    &lt;<span style="color: #00008b; font-weight: bold;">style</span> <span style="color: #1e90ff;">type</span>=<span style="color: #b22222;">"text/css"</span>&gt;
    <span style="color: #87cefa; font-weight: bold;">h2</span> <span style="font-weight: bold;">{</span>
        <span style="color: #4169e1; font-weight: bold;">color</span>: <span style="color: #2e8b57;">green</span>;
    <span style="font-weight: bold;">}</span>
    &lt;/<span style="color: #00008b; font-weight: bold;">style</span>&gt;
    &lt;/<span style="color: #00008b; font-weight: bold;">head</span>&gt;
    &lt;/<span style="color: #00008b; font-weight: bold;">html</span>&gt;
    </pre>
        </div>
      </body>
    </html>

We used the ``default`` theme as default theme, and the ``dark`` theme for
stuff that's parsed by the :mod:`CSS <parce.lang.css>` language.

In your browser, the resulting HTML-formatted text looks like this:

.. admonition:: HTML

   .. raw:: html

      <pre style="white-space: pre; background-color: #fffff0; color: #000000; font-family: monospace;">
      &lt;<span style="color: #00008b; font-weight: bold;">html</span>&gt;
      &lt;<span style="color: #00008b; font-weight: bold;">head</span>&gt;
      &lt;<span style="color: #00008b; font-weight: bold;">style</span> <span style="color: #1e90ff;">type</span>=<span style="color: #b22222;">"text/css"</span>&gt;
      <span style="color: #87cefa; font-weight: bold;">h2</span> <span style="font-weight: bold;">{</span>
          <span style="color: #4169e1; font-weight: bold;">color</span>: <span style="color: #2e8b57;">green</span>;
      <span style="font-weight: bold;">}</span>
      &lt;/<span style="color: #00008b; font-weight: bold;">style</span>&gt;
      &lt;/<span style="color: #00008b; font-weight: bold;">head</span>&gt;
      &lt;/<span style="color: #00008b; font-weight: bold;">html</span>&gt;
      </pre>


This example is not particularly beautiful, because the two themes are not
really related; the css colors are quite light, because they expect a dark
background. By default, the background of embedded language themes is not used.
To force the formatter to use the default background color of embedded themes,
add them to the formatter with ``add_baseformat = True``::

    >>> f.add_theme(parce.find("css").language, parce.theme_by_name('dark'), True)
    >>> print(f.full_html(parce.Cursor(doc, 0, None)))
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8"/>
      </head>
      <body>
        <div class="parce">
    <pre style="white-space: pre; background-color: #fffff0; color: #000000; font-family: monospace;">
    &lt;<span style="color: #00008b; font-weight: bold;">html</span>&gt;
    &lt;<span style="color: #00008b; font-weight: bold;">head</span>&gt;
    &lt;<span style="color: #00008b; font-weight: bold;">style</span> <span style="color: #1e90ff;">type</span>=<span style="color: #b22222;">"text/css"</span>&gt;<span style="background-color: #000000; color: #fffff0; font-family: monospace;">
    </span><span style="background-color: #000000; color: #87cefa; font-family: monospace; font-weight: bold;">h2</span><span style="background-color: #000000; color: #fffff0; font-family: monospace;"> </span><span style="background-color: #000000; color: #fffff0; font-family: monospace; font-weight: bold;">{</span><span style="background-color: #000000; color: #fffff0; font-family: monospace;">
        </span><span style="background-color: #000000; color: #4169e1; font-family: monospace; font-weight: bold;">color</span><span style="background-color: #000000; color: #fffff0; font-family: monospace;">: </span><span style="background-color: #000000; color: #2e8b57; font-family: monospace;">green</span><span style="background-color: #000000; color: #fffff0; font-family: monospace;">;
    </span><span style="background-color: #000000; color: #fffff0; font-family: monospace; font-weight: bold;">}</span>
    &lt;/<span style="color: #00008b; font-weight: bold;">style</span>&gt;
    &lt;/<span style="color: #00008b; font-weight: bold;">head</span>&gt;
    &lt;/<span style="color: #00008b; font-weight: bold;">html</span>&gt;
    </pre>
        </div>
      </body>
    </html>


This output looks like:

.. admonition:: HTML

   .. raw:: html

      <pre style="white-space: pre; background-color: #fffff0; color: #000000; font-family: monospace;">
      &lt;<span style="color: #00008b; font-weight: bold;">html</span>&gt;
      &lt;<span style="color: #00008b; font-weight: bold;">head</span>&gt;
      &lt;<span style="color: #00008b; font-weight: bold;">style</span> <span style="color: #1e90ff;">type</span>=<span style="color: #b22222;">"text/css"</span>&gt;<span style="background-color: #000000; color: #fffff0; font-family: monospace;">
      </span><span style="background-color: #000000; color: #87cefa; font-family: monospace; font-weight: bold;">h2</span><span style="background-color: #000000; color: #fffff0; font-family: monospace;"> </span><span style="background-color: #000000; color: #fffff0; font-family: monospace; font-weight: bold;">{</span><span style="background-color: #000000; color: #fffff0; font-family: monospace;">
          </span><span style="background-color: #000000; color: #4169e1; font-family: monospace; font-weight: bold;">color</span><span style="background-color: #000000; color: #fffff0; font-family: monospace;">: </span><span style="background-color: #000000; color: #2e8b57; font-family: monospace;">green</span><span style="background-color: #000000; color: #fffff0; font-family: monospace;">;
      </span><span style="background-color: #000000; color: #fffff0; font-family: monospace; font-weight: bold;">}</span>
      &lt;/<span style="color: #00008b; font-weight: bold;">style</span>&gt;
      &lt;/<span style="color: #00008b; font-weight: bold;">head</span>&gt;
      &lt;/<span style="color: #00008b; font-weight: bold;">html</span>&gt;
      </pre>

Of course the ``dark`` and ``default`` themes do not look good at all when used
together, but this example shows that you, with well-designed themes and
language definitions, can create sophisticated highlighting and code formatting
with *parce*.

