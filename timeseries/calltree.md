## NAME
* calltree - calltree visualization tool

## SYNOPSIS

* python calltree.py [--max-depth MAX_DEPTH] [--templates]
  [--no-line-numbers] [--just JUST] [--tree {utf-8,ascii,none}]
  [--after AFTER] [--before BEFORE] [--text] [--graph-width WIDTH]
  [--graph-scale {common,separate,log}] [--graph-ticks GRAPH_TICKS]
  [--buckets BUCKETS]


## DESCRIPTION

Display a call tree analysis of stack trace samples. Expects input in a form produced by one of the fold_*.py scripts.


* --max-depth, -m: maximum stack depth to display
* --templates, -t: don't suppress template args; normally they are suppressed because they can be quite verbose
* --no-line-numbers, -l: don't include line numbers in function names
* --just, -j: include only stacks matching this pattern
* --tree, -e: tree lines can be drawn with utf-8 (default) or ascii, or can be omitted
* --after, -a: include only samples at or after this time, in yyyy-mm-ddThh:mm:ss format
* --before, -b: include only samples before this time, in yyyy-mm-ddThh:mm:ss format
* --text: generate text output instead of interactive html view for browser use.
* --graph-width: show a graph with the specified width (in characters)
* --graph-scale:
    * common: timeline graphs are on a common linear scale (default)
    * separate: timeline graphs are on separate linear scales
    * log: timeline graphs are on a common log scale
* --graph-ticks: number of graph tick marks to show
* --buckets: smooth the timeline by grouping samples into buckets of the specified length, in floating-point seconds

## EXAMPLES

See the [README](README.md).
