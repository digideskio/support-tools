## Full-Time Data Capture ("Flight Data Recorder")

This document describes some requirements and design options around a
full-time data capture facility for mongod. The goal is to capture
time-series data useful for analyzing issues in production after the
fact. A good analogy is the "flight data recorder" used to capture
real-time data on airplanes for later analysis.

* The facility should be on full time, enabled by default.

* It should be unobtrusive, not noticeable to a customer until it is
  needed in the wake of an incident.

* It should retain as much data for as long as possible, at as high a
  sampling rate as possible, conistent with minimal performance and
  space impact.

* It should have customer-configurable parameters to control sampling
  rate, classes of data captured, retention period, and space
  utilization.


### Data to capture

* db.serverStatus(). Contains a wealth of mongod-global information,
  including storage-engine-specific counters.

* db.c.stats(). Contains similar data per-namespace. Ideally data
  would be collected for all namespaces, if consistent with
  performance and space goals. Potentially high volume of data, but
  see section below on minimizing storage.

* System data - CPU, disk at least. Collecting this for Linux is
  fairly easy (see for example
  [sysmon.py](../timeseries/sysmon.py)). Equivalent APIs presumably
  exist for Windows. Some thought towards a cross-platform view might
  be needed, although this could be provided downstream in the
  analysis and visualization tooling, with mongod collecting only raw
  data. Third-party libraries for collecting this?

* Stack trace samples. Can be very useful for diagnosing issues,
  particularly mongod bugs. Potentially high volume of data, but see
  section below on minimizing storage.

### Storage container

Some options:

* Flat file managed as a circular buffer (or possibly a ring of flat files).

    * +dead simple.

* Capped collection

    * +built-in compression
    * +less obtrusive
    * -may be difficult to recover in case of db corruption
    * -performance may not be as good?

### Storage format

Requirements:

* minimize storage

* minimize CPU overhead

* avoid excessive code complexity on producing end

* avoid excessive code complexity on consuming end

Following are some options; some simple experiments to evaluate are
needed.

#### Adaptive sampling rate

Simple fixed sampling rate does not account for the fact that
often not much is changing between samples.

For example, at first glance it seems that collecting stats() for all
namespaces could be prohibitively expensive. However, the total rate
of change of sample values across all namespaces combined for
collection.stats() should be roughly comparable to the total rate of
change for the global serverStats(), since each change affects
(roughly) 1) global serverStats() and 2) stats for one namespace (tbd
how accurate this is with a large number of indexes).

This could be captured by using an adaptive sampling rate that samples
each group of stats depending on how fast it changing. How to measure
that?

* capture a sample for each sampling group after a certain accumulated
  magnitude of changes. Probably not the right thing to do: the
  counters have wildly varying numerical magnitudes.

* capture a sample for each sampling group after a certain number of
  changes.

* some thought might be needed towards giving some stats extra weight
  in the above. For example, it would be nice to capture "checkpoint
  currently running" at or near each transition in order to precisely
  record the checkpoints.

Some of this might be achieved "for free" by using fixed-rate sampling
along with compression (using standard or customer compression
techniques) - if not much is changing, things will compress well.


#### Raw bson

Will have a high degree of redundancy. For example

* serverStatus() metrics have an unchanging schema with some very long
  field names (e.g. wiredTiger section). However much of that should
  compress out.

* Stack trace samples will have a large number of traces, one for each
  thread, but with a high degree of redundancy: many common prefixes
  (if represented root to leaf) or common suffixes (if represented
  leaf to root). Common prefixes or suffixes could be explicitly
  captured in the sample representation, or be left to be compressed
  out.

#### Delta coding

Very high degree of coherence from one sample to the next:

* schema does not change

* many of the recorded values do not change, or change slowly

Delta coding could consist of

* Periodic "full samples" consisting of a full raw bson document

* Between the full samples would be delta samples:

    * field names not recorded; field values recorded
      positionally. Change in schema (can this occur?) triggers full
      sample.

    * numeric values recorded as numeric delta

    * string values (not many of these) recorded as symbol indicating
      "same value", or symbol indicating "different value" followed by
      new value. Alternatively, string values not recorded at all, and
      change in string value triggers full sample.

TBD how this interacts with standard compression; suspect it might be
particularly effective with custom compression.

#### Standard compression

Need to evaluate effectiveness of snappy and zlib on raw bson and
delta codings.

#### Custom compression

Might benefit from custom compression, particularly with delta coding,
using a custom fixed(?) symbol dictionary and either

* Huffman coding - fairly simple, works well down to 1-2 bits per
  symbol.

* Dead simple variant of Huffman coding in conjunction with delta coding:

    * single bit value to encode "same value"

    * different values encoded as opposite bit value followed by some
      compact representation of delta (e.g. something like WT compact
      int representation).

* Arithmetic coding - can achieve coded rates of <1 bit per
  symbol. Given the high degree of coherency between samples (that is,
  lots of deltas with a value of 0) it is possible entropy will be <1
  bit per symbol, so this option could be explored.

CPU efficiency of this compared to standard compression TBD, but I
suspect it could compare favorably.
