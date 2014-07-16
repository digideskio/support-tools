demanglers
==========

Various scripts that will take human-oriented output from monitoring programs and "de-mangle" them into simple, space-separated column-based text format, suitable for further (machine) analysis.  I like feeding these resulting files into [GNUplot](http://gnuplot.info) (mainly because I've used gnuplot for years).

These require various text processing utilities like `awk`, `sed`, `grep`, and `column`.  Apologies if I've used any GNU extensions (reasonably likely, especially `gawk`).

So far:
* `mongostat`
* `iostat`
* `vmstat`
* `sar -b`

Originally developed to aid analysis in [CS-13181](https://jira.mongodb.org/browse/CS-13181) (ebay), there may be some hard-coded rubbish to deal with those specific files.  Pull requests to make them more generally applicable are warmly welcomed.

Owner: [Kevin Pulo](mailto:kevin.pulo@mongodb.com)

