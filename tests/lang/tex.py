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


from parce.lang.tex import Latex

def examples():
    yield Latex.root, r"""% Latex example from wikipedia
\documentclass[a4paper]{article}
\usepackage[dutch]{babel}
\begin{document}
\section{Example paragraph}
A formula follows:
% a comment
\[
\pi = \sqrt{6\sum_{n=1}^{\infty}\frac{1}{n^2}}
   = \left(\int_{-\infty}^{+\infty}e^{-x^2}\,dx\right)^2
\]
\end{document} % End of document

"""
