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
Test the lang.numbers module.
"""

## find parce

import sys
sys.path.insert(0, '.')






def test_main():
    """Write stuff to test here."""
    from parce.lang.numbers import English, Nederlands, Deutsch, Français
    from parce.transform import transform_text

    assert transform_text(English.root, "one two THREE") == [1, 2, 3]
    assert transform_text(English.root, "fiftysix") == [56]
    assert transform_text(English.root, "FiftySixThousandSevenHundredEightyNine") == [56789]
    assert transform_text(English.root, "twelve hundred thirty four") == [1234]
    assert transform_text(English.root, "twelve hundred thirty four five") == [1234, 5]
    assert transform_text(English.root, "Twelve Hundred Thirty Four Twenty Five") == [1234, 25]

    assert transform_text(Nederlands.root, "een twee DRIE") == [1, 2, 3]
    assert transform_text(Nederlands.root, "zesenvijftig") == [56]
    assert transform_text(Nederlands.root, "ZesenVijftigDuizendZevenhonderdNegenenTachtig") == [56789]
    assert transform_text(Nederlands.root, "twaalfhonderd vier en dertig") == [1234]
    assert transform_text(Nederlands.root, "twaalfhonderd vier en dertig vijf") == [1234, 5]
    assert transform_text(Nederlands.root, "twaalfhonderd vier en dertig vijf en twintig") == [1234, 25]

    assert transform_text(Deutsch.root, "ein zwei DREI") == [1, 2, 3]
    assert transform_text(Deutsch.root, "eins zwei DREI") == [1, 2, 3]
    assert transform_text(Deutsch.root, "Sechsundfünfzig") == [56]
    assert transform_text(Deutsch.root, "Sechsundfünfzig Tausend Siebenhundert NeunundAchtzig") == [56789]
    assert transform_text(Deutsch.root, "Zwölfhundert Vierunddreißig") == [1234]
    assert transform_text(Deutsch.root, "Zwölfhundert Vierunddreissig Fünf") == [1234, 5]
    assert transform_text(Deutsch.root, "Zwölfhundert Vierunddreißig Fünf und Zwanzig") == [1234, 25]

    assert transform_text(Français.root, 'un deux TROIS') == [1, 2, 3]
    assert transform_text(Français.root, 'cinquante-six') == [56]
    assert transform_text(Français.root, 'cinquante-six mille sept-cents quatre-vingt neuf') == [56789]
    assert transform_text(Français.root, 'mille deux cent trente-quatre') == [1234]
    assert transform_text(Français.root, 'mille deux cent trente-quatre cinq') == [1234, 5]
    assert transform_text(Français.root, 'mille deux cent trente-quatre vingt-cinq') == [1234, 25]



if __name__ == "__main__":
    test_main()

