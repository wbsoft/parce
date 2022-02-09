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
I/O logic for Documents

"""

import codecs
import collections
import io
import os
import re

from . import util, work


DecodeResult = collections.namedtuple("DecodeResult", "root_lexicon text encoding")
"""The result of the :meth:`DocumentIOMixin.decode_data` method."""
DecodeResult.root_lexicon.__doc__ = "The root lexicon or None."
DecodeResult.text.__doc__ = "The decoded text."
DecodeResult.encoding.__doc__ = "The encoding that was specified or determined, or None."



DEFAULT_ENCODING = "utf-8"
TEMP_TEXT_MAXSIZE = 5000


class DocumentIOMixin:
    """Mixin class, adding load and save methods to Document.

    It also expects :class:`~.work.WorkerDocumentMixin` to be mixed in, because
    of the root lexicon handling.

    Your final class should implement :meth:`create_from_data`, to actually
    instantiate the Document.

    """
    @classmethod
    def load(cls,
        url,
        root_lexicon=False,
        encoding=None,
        errors=None,
        newline=None,
        registry=None,
        worker=None,
        transformer=None,
        mimetype=None,
    ):
        """Load text from ``url`` and return a Document.

        The ``url`` and the ``encoding`` are stored in the document's attributes
        of the same name.

        The current implementation only supports reading a file from the
        local file system.

        The ``url`` is the filename. If the ``root_lexicon`` is None, no
        parsing will be done on the document. If False, guessing will be done
        using the specified ``registry`` or the default parce
        :data:`~parce.registry.registry`. If ``root_lexicon`` is a string name,
        the name will be looked up in the registry. Otherwise, it is assumed to
        be a :class:`~parce.lexicon.Lexicon`.

        The ``encoding`` is "utf-8" by default. The ``errors`` and ``newline``
        argument will be passed to the underlying TextIOWrapper reading the
        file contents.

        The ``worker`` is a :class:`~.work.Worker` or None. By default, a
        :class:`~.work.BackgroundWorker` is used.

        The ``transformer`` is a :class:`~.transform.Transformer` or None. By
        default, no Transformer is installed. As a convenience, you can specify
        ``True``, in which case a default Transformer is installed.

        """
        data = open(url, "rb").read()
        return cls.load_from_data(data, url, root_lexicon, encoding, errors, newline, registry, worker, transformer, mimetype)

    @classmethod
    def load_from_data(cls,
        data,
        url=None,
        root_lexicon=False,
        encoding=None,
        errors=None,
        newline=None,
        registry=None,
        worker=None,
        transformer=None,
        mimetype=None,
    ):
        """Load text from binary ``data`` and return a Document.

        For all the other arguments, see :meth:`load`.

        """
        r = cls.decode_data(data, url, root_lexicon, encoding, errors, newline, registry, mimetype)
        doc = cls.create_from_data(r.root_lexicon, r.text, url, r.encoding, worker, transformer)
        doc.url = url
        doc.encoding = encoding
        return doc

    @staticmethod
    def decode_data(data, url, root_lexicon, encoding, errors, newline, registry, mimetype):
        """Decode text from the binary data, using all the other arguments (see
        :meth:`load`).

        Returns a named tuple DecodeResult(root_lexicon, text, encoding).

        This method tries to determine the encoding and the root lexicon if
        desired. If the root lexicon is determined, a custom :class:`IO` can be
        instantiated (if the lexicon's language has one) to determine the
        encoding of the text in that specific language.



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
        elif root_lexicon is False:
            root_lexicon is None
        else:
            # guess the language: use registry and url
            root_lexicon = registry.find(filename=os.path.basename(url), mimetype=mimetype, contents=temp_text)

        # find a possible encoding specified in the document
        io_cls = root_lexicon and util.language_sister_class(root_lexicon.language, "{}IO", IO, True) or IO
        io_handler = io_cls()
        doc_enc = io_handler._find_existing_encoding(temp_text)

        # If the doc had a BOM (byte order mark), respect that encoding; otherwise
        # use the encoding in the document, the specified encoding, or the default encoding (utf-8).
        actual_read_enc = read_enc or doc_enc or encoding or io_handler.default_encoding()

        # If no encoding was specified, remember the encoding set in the document
        # or determined via the BOM.
        if encoding is None:
            encoding = doc_enc or read_enc

        # now let Python decode the text
        text = io.TextIOWrapper(io.BytesIO(data), actual_read_enc, errors, newline).read()
        return DecodeResult(root_lexicon, text, encoding)

    @classmethod
    def create_from_data(cls, root_lexicon, text, url, encoding, worker, transformer):
        """Implement to instantiate a document from data."""
        raise NotImplementedError

    def save(self, url=None, encoding=None, newline=None):
        """Save the document to a local file.

        If you specify the ``url`` or ``encoding``, the corresponding
        attributes are set as well. If encoding is not specified and also not
        set in the corresponding attribute, an encoding to use is searched for
        in the document's text; if that is not found, the language's
        :class:`IO` handler can define the default encoding to use.

        """
        text = self.text()
        if url is not None:
            self.url = url
        if encoding is not None:
            self.encoding = encoding
        elif self.encoding is None:
            lexicon = self.root_lexicon()
            io_cls = lexicon and util.language_sister_class(lexicon.language, "{}IO", IO, True) or IO
            io_handler = io_cls()
            encoding = io_handler._find_existing_encoding(text) or io_handler.default_encoding()
        else:
            encoding = self.encoding
        with open(self.url, "w", encoding=encoding, newline=newline) as f:
            f.write(self.text())
        self.modified = False


class IO:
    """Functional base class for Language-specific IO handling."""
    def default_encoding(self):
        """Return the default encoding to use."""
        return DEFAULT_ENCODING

    def _find_existing_encoding(self, text):
        """Call :meth:`find_encoding` but only return an encoding if it actually exists."""
        encoding = self.find_encoding(text[:TEMP_TEXT_MAXSIZE])
        try:
            codecs.lookup(encoding)
        except LookupError:
            return
        return encoding

    def find_encoding(self, text):
        """Return an encoding stored inside the piece of ``text``.

        The default implementation recognizes some encoding="xxx" and (en)coding: xxxx
        variants. Returns None if no encoding is found.

        """
        m = re.search(r'\b(?:en)coding[\t ]*?(?::[ \t]*?|=[\t ]*?")([\w_-]+)', text)
        if m:
            return m.group(1)


