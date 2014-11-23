## NAME
* gdbprof - analyze profile samples collected by gdbmon

## SYNOPSIS

* python gdbprof.py [--max-depth MAX_DEPTH] [--templates]
  [--no-line-numbers] [--just JUST] [--tree {utf-8,ascii,none}]
  [--after AFTER] [--before BEFORE]

## DESCRIPTION

Display a call tree analysis of stack trace samples collected by
[gdbmon](gdbmon.md). The stack trace samples are read from stdin.

* --maxdepth, -m: maximum stack depth to display
* --templates, -t: don't suppress template args; normally they are suppressed because they can be quite verbose
* --no-line-numbers, -l: don't include line numbers in function names
* --just, -j: include only stacks matching this pattern
* --tree, -e: tree lines can be drawn with utf-8 (default) or ascii, or can be omitted
* --after, -a: include only samples at or after this time, in yyyy-mm-ddThh:mm:ss format
* --before, -b: include only samples before this time, in yyyy-mm-ddThh:mm:ss format


## EXAMPLES

See the [README](README.md).
