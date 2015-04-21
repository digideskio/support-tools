## NAME
* ftdc - ftdc proof-of-concept implementation

## SYNOPSIS

* ftdc [-n NSAMPLES] [-t DELAY] [-c CHUNKSIZE] [-u UPDATESIZE] [-r] [--fork] source [sink]

## DESCRIPTION

Copy samples from source to sink.

* -n NSAMPLES - number of samples to copy. Default is to copy until
  source is exhausted, or indefinitely in the case of a live source.

* -t DELAY - delay in floating point seconds between samples. Default
   is 0 for recorded sources, 1 in the case of a live source.

* -c CHUNKSIZE - number of samples accumulated in each chunk. Default
   is 300.

* -u UPDATESIZE - write interim chunk updates for the last chunk after
   accumulating this many samples in order to minimize sample loss on
   crash. Default is 0 (disabled).

* -r - enable replSetGetStatus data collection

* --fork - execute in the background


**Source may be one of:**

* *.bson - a file containing a sequence of uncompressed samples as
   BSON documents.

* mongodb://host[:port] - specifies a live source of uncompressed
  samples: samples are obtained by repeatedly running a serverStatus
  command on the specified mongodb instance.

* mongodb://host[:port]/?ns=NS - specifies a mongodb instance and
  collection to read compressed samples from. The samples are
  decompressed before being sent to the sink.

* *.ftdc - a file containing compressed samples, produced by
   specifying this file as a sink to a previous ftdc command. This
   defines a simple container of compressed samples and is intended
   for testing purposes only.

**Sink may be one of:**

* *.bson - a file containing a sequence of uncompressed samples as
   BSON documents.

* *.json - a file containing a sequence of uncompressed samples as
   JSON documents.

* mongodb://host[:port][?ns=NS][&sizeMB=MB] - compressed samples are
  stored in the specified collection in a mongod instance. If the
  collection does not exist it is created as a capped collection with
  the specified size. Default size if sizeMB is not specified is 100
  MB.

* *.ftdc - a file containing compressed samples, to be read by
   specifying this file as a source in a subsequent ftdc command. This
   defines a simple container of compressed samples and is intended
   for testing purposes only.

* if no sink is specfied samples are collected and chunks are
  compressed and then discarded. This is useful for computing
  compression or decompression statistics on a source and then
  discarding the result.



## EXAMPLES

See the [README](README.md).
