## NAME
* gdbprof - analyze profile samples collected by gdbmon

## SYNOPSIS
* python gdbprof.py [-h] [--maxdepth MAX_DEPTH] [--templates] [--just JUST]

## DESCRIPTION

Display a call tree analysis of stack trace samples collected by
[gdbmon](gdbmon.md). The stack trace samples are read from stdin.

* -h, --help: show a help message
* --maxdepth, -m: maximum stack depth to display
* --templates, -t: don't suppress template args; normally they are suppressed because they can be quite verbose
* --just, -j: include only stacks matching this pattern

## EXAMPLES

See the [README](README.md).
