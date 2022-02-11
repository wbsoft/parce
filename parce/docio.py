# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2022-2022 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
I/O handling for Documents.

This module defines :class:`DocumentIOMixin` to mix in with the other parce
Document base classes, adding load and save methods. These methods are not
mandatory at all; you can choose to implement your own save and load logic.

When a Document is loaded or saved, the filename is stored in the Document's
:attr:`~.document.AbstractDocument.url` attribute, and if you specify an
encoding, it is also stored in the  Document's
:attr:`~.document.AbstractDocument.encoding` attribute.

Besides that, this module enables intelligent encoding determination and
handling, where the language of a Document can point to an :class:`IO` subclass
which implements encoding determination based on the document's language. An
:class:`IO` "sister-class" of a :class:`~parce.language.Language` can define a
default encoding and provides a method to consult the document's contents to
see if an encoding is defined there, and use that for I/O operations.

"""

import codecs
import collections
import io
import os
import re
from urllib.parse import urlparse

from . import util, work


DecodeResult = collections.namedtuple("DecodeResult", "root_lexicon text encoding")
"""The result of the :meth:`DocumentIOMixin.decode_data` method."""
DecodeResult.root_lexicon.__doc__ = "The root lexicon or None."
DecodeResult.text.__doc__ = "The decoded text."
DecodeResult.encoding.__doc__ = "The encoding that was specified or determined, or None."


DEFAULT_ENCODING = "utf-8"      #: The general default encoding, if a Language does not define another
TEMP_TEXT_MAXSIZE = 5000        #: The maximum size of a text snippet that is searched for an encoding


class DocumentIOMixin:
    """Mixin class, adding load and save methods to Document.

    It also expects :class:`~.work.WorkerDocumentMixin` to be mixed in, because
    of the root lexicon handling.

    """
    @classmethod
    def load(cls,
        url,
        root_lexicon = True,
        encoding = None,
        errors = None,
        newline = None,
        registry = None,
        mimetype = None,
        worker = None,
        transformer = None,
    ):
        """Load text from ``url`` and return a Document.

        The current implementation only supports reading a file from the
        local file system.

        The ``url`` is the filename. If the ``root_lexicon`` is None, no
        parsing will be done on the document. If True, guessing will be done
        using the specified ``registry`` or the default parce
        :data:`~parce.registry.registry` (in which case ``url`` and
        ``mimetype`` both can help in determining the language to use). If
        ``root_lexicon`` is a string name, the name will be looked up in the
        registry. Otherwise, it is assumed to be a
        :class:`~parce.lexicon.Lexicon`.

        The ``url`` and the ``encoding`` are stored in the document's
        attributes of the same name. The ``encoding`` is "utf-8" by default.
        The ``errors`` and ``newline`` arguments will be passed to the
        underlying :class:`io.TextIOWrapper` reading the file contents.

        The ``worker`` is a :class:`~.work.Worker` or None. By default, a
        :class:`~.work.BackgroundWorker` is used. The ``transformer`` is a
        :class:`~.transform.Transformer` or None. By default, no Transformer is
        installed. As a convenience, you can specify ``True``, in which case a
        default Transformer is installed.

        """
        data = open(localfile(url), "rb").read()
        return cls.from_bytes(data, url, root_lexicon, encoding, errors, newline, registry, mimetype, worker, transformer)

    def save(self, url=None, encoding=None, newline=None):
        """Save the document to a local file.

        If you specify the ``url`` or ``encoding``, the corresponding Document
        attributes are set as well. If the encoding is not specified and also not
        set in the corresponding document attribute, the encoding to use is
        searched for in the document's text; if that is not found, the
        language's :class:`IO` handler can define the default encoding to use;
        the ultimate default is "utf-8".

        The ``newline`` argument will be passed to the underlying
        :class:`io.TextIOWrapper` that writes the document's contents.

        """
        if url:
            self.url = url
        if encoding:
            self.encoding = encoding
        data = self.to_bytes(encoding, newline)
        with open(localfile(self.url), "wb") as f:
            f.write(data)
        self.modified = False

    @classmethod
    def from_bytes(cls,
        data,
        url = None,
        root_lexicon = True,
        encoding = None,
        errors = None,
        newline = None,
        registry = None,
        mimetype = None,
        worker = None,
        transformer = None,
    ):
        """Load text from bytes or bytearray ``data`` and return a Document.

        For all the other arguments, see :meth:`load`.

        """
        r = decode_data(data, root_lexicon, encoding, errors, newline, registry, url, mimetype)
        return cls(r.root_lexicon, r.text, url, r.encoding, worker, transformer)

    def to_bytes(self, encoding=None, newline=None):
        """Return the binary encoded contents of the document.

        The default implementation uses the :func:`encode_text` function. If
        the encoding is not specified and also not set in the corresponding
        document attribute, the encoding to use is searched for in the
        document's text; if that is not found, the language's :class:`IO`
        handler can define the default encoding to use; the ultimate default is
        "utf-8".

        The ``newline`` argument will be passed to the underlying
        :class:`io.TextIOWrapper` that writes the document's contents.

        """
        return encode_text(self.text(), self.root_lexicon(), encoding or self.encoding, newline)


class IO:
    """Functional base class for language-specific I/O handling.

    You may create a "sister-class" in the same module as a Language, with "IO"
    appended to the class name, to have your IO-subclass automatically found.

    So, if your language has the name "MyLang", a class "MyLangIO" in the same
    module that inherits this class, will be used for encoding handling.

    """
    @classmethod
    def get(cls, lexicon):
        """Get an IO handler for this lexicon's language.

        If the lexicon is None, a new instance of the called IO is returned.

        """
        io_cls = lexicon and util.language_sister_class(lexicon.language, "{}IO", IO, True) or cls
        return io_cls()

    def default_encoding(self):
        """Return the default encoding to use."""

    def find_encoding(self, text):
        """Return an encoding stored inside the piece of ``text``.

        The default implementation recognizes some encoding="xxx" and
        (en)coding: xxxx variants. Returns None if no encoding is found.

        """
        m = re.search(r'\b(?:en)coding[\t ]*?(?::[ \t]*?|=[\t ]*?")([\w_-]+)', text)
        if m:
            return m.group(1)


def localfile(url):
    """Return the local filename the ``url`` points to.

    The url is parsed using :func:`~urllib.parse.urlparse`. If the url has a
    ``file:`` scheme, the path is returned. If the url has no ``scheme`` and no
    ``netloc``, the full url is returned so that it is used as a local file.

    Raises a ValueError if the URL does not point to a local file.

    """
    u = urlparse(url, allow_fragments=False)
    if not u.netloc:
        if u.scheme == "file":
            return u.path
        if not u.scheme:
            return url
    raise ValueError("only local files are supported")


def decode_data(
        data,
        root_lexicon = None,
        encoding = None,
        errors = None,
        newline = None,
        registry = None,
        url = None,
        mimetype = None
    ):
    """Decode text from the binary (bytes or bytearray) ``data``.

    Returns a named tuple :class:`DecodeResult` (``root_lexicon``,
    ``text``, ``encoding``).

    If the data starts with a *byte-order mark* (BOM), the encoding that is
    specified by that BOM is used to read the rest of the data. Otherwise, the
    data is first interpreted as ``latin1`` and examined. If no encoding can be
    determined by looking at the text, the specified ``encoding`` is used, or
    UTF-8 by default.

    The ``root_lexicon`` determines how the data is further interpreted: If
    None, no parsing is done at all. If True, the specified ``registry`` or the
    default parce :data:`~parce.registry.registry` is used to guess the
    language (in this case ``url`` and ``mimetype`` both help in determining
    the language to use). If ``root_lexicon`` is a string name, it is looked up
    in the registry. Otherwise it is assumed to be a :class:`~.lexicon.Lexicon`.

    When the root lexicon's Language (or one of its superclasses) has an
    :class:`IO` "sister-class" (i.e. in the same module with the same name with
    "IO" appended), that IO class's :meth:`~IO.get_encoding` method is called
    to determine the encoding of the text, which may be mentioned in the text
    in a way specific to that language. If that method returns None,
    :meth:`~IO.default_encoding` is called, which also by default returns
    "utf-8".

    E.g. for XML, the ``encoding`` attribute of the first processing
    instruction is consulted, for Html the value of a ``<meta>`` tag with
    ``charset`` or ``http-equiv`` attributes, etc.

    The ``errors`` and ``newline`` arguments will be passed to the underlying
    :class:`io.TextIOWrapper` reading the file contents.

    If no ``encoding`` was specified, the returned ``encoding`` is the encoding
    that was finally used to read the text; otherwise it is the specified
    encoding.

    """
    # check and guess the encoding if needed
    read_enc, data = util.get_bom_encoding(data)

    # make a temporary piece of text to determine language and encoding
    temp_enc = "latin1" if read_enc is None else read_enc
    temp_text = data[:TEMP_TEXT_MAXSIZE].decode(temp_enc, 'ignore')

    if registry is None:
        from parce.registry import registry

    # determine root lexicon (is ultimately a Lexicon or None)
    if isinstance(root_lexicon, str):
        root_lexicon = registry.find(root_lexicon)
    elif root_lexicon is True:
        # guess the language: use registry and url
        root_lexicon = registry.find(filename=os.path.basename(url), mimetype=mimetype, contents=temp_text)

    # find a possible encoding specified in the document
    h = IO.get(root_lexicon)
    doc_enc = _validate_encoding(h.find_encoding(temp_text))

    # If the doc had a BOM (byte order mark), respect that encoding; otherwise
    # use the encoding in the document, the specified encoding, or the default encoding (utf-8).
    actual_read_enc = read_enc or doc_enc or encoding or _validate_encoding(h.default_encoding()) or DEFAULT_ENCODING

    # If no encoding was specified, remember the encoding set in the document
    # or determined via the BOM.
    if not encoding:
        encoding = doc_enc or read_enc

    # now let Python decode the text
    text = io.TextIOWrapper(io.BytesIO(data), actual_read_enc, errors, newline).read()
    return DecodeResult(root_lexicon, text, encoding)


def encode_text(text, root_lexicon=None, encoding=None, newline=None):
    """Return a :class:`bytes` object with the encoded text.

    If ``encoding`` is None, the ``root_lexicon`` is used to help finding
    an encoding set in the document. The ``newline`` argument is passed to
    the underlying :class:`io.TextIOWrapper` writing the file contents.

    """
    if not encoding:
        h = IO.get(root_lexicon)
        encoding = _validate_encoding(h.find_encoding(text[:TEMP_TEXT_MAXSIZE])
                    or h.default_encoding()) or DEFAULT_ENCODING
    b = io.BytesIO()
    with io.TextIOWrapper(b, encoding=encoding, newline=newline) as f:
        f.write(text)
        f.flush()
        return b.getvalue()


def _validate_encoding(encoding):
    """Check if the ``encoding`` is actually usable.

    Returns None if the encoding is not usable, otherwise the encoding itself.

    """
    if encoding:
        try:
            codecs.lookup(encoding)
            return encoding
        except LookupError:
            pass

