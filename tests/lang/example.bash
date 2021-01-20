#!/bin/sh

uri=$1

col=${uri##*:}  uri=${uri%:*}
char=${uri##*:} uri=${uri%:*}
line=${uri##*:} uri=${uri%:*}
proto=${uri%%:*}
file="file:${uri#*:}"

if kde-config --version |grep -q 'KDE: [23]'
then
        # for KDE 3.x:
        let line=--line
else
        # for KDE 4.x:
        let col=++col
fi

exec kate --use --line $line --column $col "$file"
