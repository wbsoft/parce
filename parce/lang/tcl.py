# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2021-2021 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Tcl (Tool Command Language)

"""

__all__ = ('Tcl',)

import re

from parce import Language, lexicon, default_action
from parce.action import (
    Comment, Delimiter, Escape, Keyword, Name, Number, Operator, String, Text
)
from parce.rule import MATCH, bygroup, ifgroup, findmember, gselect


RE_TCL_NUMBER = (r'[-+]?(?:'
    r'0(?:([oO]?[0-7]+)'                            # 1 octal
        r'|([bB][01]+)'                             # 2 binary
        r'|([xX][0-9a-fA-F]+))'                     # 3 hexadecimal
    r'|((?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?)'  # 4 decimal
    r')(?!\w)'
)


class Tcl(Language):
    """Tool command language."""

    @classmethod
    def values(cls):
        yield r'\[', Delimiter, cls.command
        yield r'"', String, cls.quoted
        yield r'\{', Delimiter.Bracket, cls.braced
        yield r'(\$(?:[0-9a-zA-Z_]|::+)+)(\()?', \
            bygroup(Name.Variable, Delimiter), ifgroup(2, cls.index)
        yield r'\${.*?\}', Name.Variable
        yield r'\\(?:[0-7]{1,3}|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|\n|.)', Escape
        yield r'^\s*(#)', bygroup(Comment), cls.comment
        yield RE_TCL_NUMBER, gselect(Number.Octal, Number.Binary, Number.Hexadecimal, Number.Decimal)
        yield r'(;)(?:[ \t]*(#))?', bygroup(Delimiter.Separator, Comment), \
            ifgroup(2, cls.comment)

    @lexicon(re_flags=re.MULTILINE)
    def root(cls):
        yield r'\A#!.*?$', Comment.Special
        yield from cls.values()
        yield r"([^\s\\{}[\]$'();]+)(\()?", bygroup(
            findmember(MATCH[1], ((operators, Operator),
                                  (tcl_commands, Keyword),
                                  (tk_commands, Name.Command)), Text.Word),
            Delimiter), ifgroup(2, cls.index)
        yield r'\(\)', Delimiter

    @lexicon(re_flags=re.MULTILINE)
    def command(cls):
        yield r'\]', Delimiter, -1
        yield from cls.root

    @lexicon
    def quoted(cls):
        yield r'"', String, -1
        yield r'\[', Delimiter, cls.command
        yield from cls.values()
        yield default_action, String

    @lexicon(re_flags=re.MULTILINE)
    def braced(cls):
        yield r'\}', Delimiter.Bracket, -1
        yield from cls.root

    @lexicon(re_flags=re.MULTILINE)
    def index(cls):
        """Index of a variable reference like $name(index)."""
        yield r'\)', Delimiter, -1
        yield from cls.root

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield r'$', None, -1
        yield from cls.comment_common()


# from https://www.tcl.tk/man/tcl/TclCmd/contents.htm
tcl_commands = (
    "after", "errorInfo", "load", "re_syntax", "tcl_startOfNextWord", "append",
    "eval", "lrange", "read", "tcl_startOfPreviousWord", "apply", "exec",
    "lrepeat", "refchan", "tcl_traceCompile", "argc", "exit", "lreplace",
    "regexp", "tcl_traceExec", "argv", "expr", "lreverse", "registry",
    "tcl_version", "argv0", "fblocked", "lsearch", "regsub",
    "tcl_wordBreakAfter", "array", "fconfigure", "lset", "rename",
    "tcl_wordBreakBefore", "auto_execok", "fcopy", "lsort", "return",
    "tcl_wordchars", "auto_import", "file", "mathfunc", "safe", "tcltest",
    "auto_load", "fileevent", "mathop", "scan", "tell", "auto_mkindex",
    "filename", "memory", "seek", "throw", "auto_path", "flush", "msgcat",
    "self", "time", "auto_qualify", "for", "my", "set", "timerate",
    "auto_reset", "foreach", "namespace", "socket", "tm", "bgerror", "format",
    "next", "source", "trace", "binary", "gets", "nextto", "split",
    "transchan", "break", "glob", "oo::class", "string", "try", "catch",
    "global", "oo::copy", "subst", "unknown", "cd", "history", "oo::define",
    "switch", "unload", "chan", "http", "oo::objdefine", "tailcall", "unset",
    "clock", "if", "oo::object", "Tcl", "update", "close", "incr", "open",
    "tcl::prefix", "uplevel", "concat", "info", "package", "tcl_endOfWord",
    "upvar", "continue", "interp", "parray", "tcl_findLibrary", "variable",
    "coroutine", "join", "pid", "tcl_interactive", "vwait", "dde", "lappend",
    "pkg::create", "tcl_library", "while", "dict", "lassign", "pkg_mkIndex",
    "tcl_nonwordchars", "yield", "encoding", "lindex", "platform",
    "tcl_patchLevel", "yieldto", "env", "linsert", "platform::shell",
    "tcl_pkgPath", "zlib", "eof", "list", "proc", "tcl_platform", "error",
    "llength", "puts", "tcl_precision", "errorCode", "lmap", "pwd",
    "tcl_rcFileName",
)

# from https://www.tcl.tk/man/tcl/TkCmd/contents.htm
tk_commands = (
    "bell", "grab", "scale", "tk_optionMenu", "ttk::menubutton", "bind",
    "grid", "scrollbar", "tk_patchLevel", "ttk::notebook", "bindtags", "image",
    "selection", "tk_popup", "ttk::panedwindow", "bitmap", "keysyms", "send",
    "tk_setPalette", "ttk::progressbar", "busy", "label", "spinbox",
    "tk_strictMotif", "ttk::radiobutton", "button", "labelframe", "text",
    "tk_textCopy", "ttk::scale", "canvas", "listbox", "tk", "tk_textCut",
    "ttk::scrollbar", "checkbutton", "lower", "tk::mac", "tk_textPaste",
    "ttk::separator", "clipboard", "menu", "tk_bisque", "tk_version",
    "ttk::sizegrip", "colors", "menubutton", "tk_chooseColor", "tkerror",
    "ttk::spinbox", "console", "message", "tk_chooseDirectory", "tkwait",
    "ttk::style", "cursors", "option", "tk_dialog", "toplevel",
    "ttk::treeview", "destroy", "options", "tk_focusFollowsMouse",
    "ttk::button", "ttk::widget", "entry", "pack", "tk_focusNext",
    "ttk::checkbutton", "ttk_image", "event", "panedwindow", "tk_focusPrev",
    "ttk::combobox", "ttk_vsapi", "focus", "photo", "tk_getOpenFile",
    "ttk::entry", "winfo", "font", "place", "tk_getSaveFile", "ttk::frame",
    "wm", "fontchooser", "radiobutton", "tk_library", "ttk::intro", "frame",
    "raise", "tk_menuSetFocus", "ttk::label", "geometry", "safe::loadTk",
    "tk_messageBox", "ttk::labelframe",
)

operators = (
    "-",  "+",  "~",  "!",
    "**",
    "*",  "/",  "%",
    "+",  "-",
    "<<",  ">>",
    "<",  ">",  "<=",  ">=",
    "==",  "!=",
    "eq",  "ne",
    "in",  "ni",
    "&",
    "^",
    "|",
    "&&",
    "||",
    "?",  ":",
)

