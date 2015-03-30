## Full-Time Data Capture ("Black Box")

This document describes some requirements, a strawman design, and a
proof-of-concept implementation for a full-time data capture facility
for mongod. The goal is to capture time-series data useful for
analyzing issues in production. A good analogy is the "flight data
recorder" or "black box" used to capture real-time data on airplanes
for later analysis.

Goals and requirements:

* Collect timeseries metrics in mongod to enable post-mortem RCA and
  analysis of recurring problems for support and engineering team.

* It should be unobtrusive, not noticeable to a customer until it is
  needed in the wake of an incident.

* The facility should be on full time, enabled by default.

* It should retain as much data for as long as possible, at as high a
  sampling rate as possible, consistent with minimal performance and
  space impact.

* It should have customer-configurable parameters to control sampling
  rate, classes of data captured, retention period, and space
  utilization.

* Flexible schema: can accommodate platform specific and optional
  measurements

Rationale

* RCA of production issues is very difficult without a full array of data

* Currently, we have two primary sources of timeseries data: log files and MMS
    * Log files do not capture everything and are often at too low verbosity
    * MMS has a different set of goals and audience
        * sampling rate is too coarse, retention of data too short.
        * we have to support customers who cannot or will not use MMS


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

The initial proof of concept and strawman integration proposal
addresses serverStatus only, which is sufficient for a wide range of
problems. Possibility for enhancement in the future with additional
data capture is tbd.

## Data capture format strawman design

This section describes a general format for space-efficient storage of
time series monitoring data by mongod. Assumptions:

* Space efficiency is paramount, to maximize retention time, and to
  minimize storage i/o.

* Time efficiency is also very important. Impact on performance should
  be at noise levels.

* The data is presented and recovered in the form of BSON documents
  with an arbitrary schema. The schema may change during the course of
  a time series, but such changes are infrequent.

* The data may be transformed arbitrarily for storage, necessitating
  the use of decoding software to recover the data. This software may
  be external, that is, the data need not be recovered internal to
  mongod.

* The data of interest is numeric, specifically integer. In
  particular, string data is (largely) ignored, and floating-point
  data must be integer. Precise numeric data type information does not
  need to be recovered.

* Efficient storage is required for all storage engines. In
  particular, the storage format cannot rely on storage engine
  compression to achieve space efficiency, but rather must provide its
  own compression.


### Data capture container format

This section describes the storage of timeseries data in a capped
collection. If needed, a similar storage format for flat files could
be devised; a flat file could have some advantages, for example, it
might be more feasible to store the last samples immediately preceding
a crash in a flat file.

Following is a schematic overview of the capped collection
storage format:

    capped collection (ns "local.ftdc")
        document
            _id: BSON datetime (ms since Unix epoch)
            type: 0
            data: BinData containing
                zlib stream containing
                    sample chunk
                        full reference BSON sample
                        delta sample 1
                        delta sample 2
                        ...
        ...

As illustrated above, data is encapsulated in a time-sequential stream
of *chunks*. Each chunk represents a sequence of consecutive samples,
and contains

* A *reference sample* consisting of a BSON document representing a
  full data sample. This sample determines the schema that the
  subsequent delta samples must follow up until the next reference
  sample, and it is the first sample of the sequence of samples
  represented by this chunk.

* A sequence of *delta samples* each represented by a delta from the
  previous sample, starting with the reference sample. Since the delta
  samples must have the same schema as the reference sample, only the
  numeric field values need to be stored. In addition to delta coding,
  several compression techniques (described below) are applied to the
  deltas to form the delta sample chunk, prior to zlib compression as
  shown above.

A ms-resolution BSON timestamp is used for the _id. This allows
efficient retrieval of a time range of samples, while supporting
sampling rates up to 1 kHz. Typically the samples will contain their
own timestamp, which precisely defines the timing of the individual
samples; the relationship of the _id to the sample timestamps is
approximate and is not precisely defined.

### Delta compression

In the interest of space efficiency, most samples are captured as
compressed deltas relative the preceding sample, starting with a full
reference sample, and are processed together in groups of delta
samples.

* The data-bearing elements of the reference sample are
  identified. These consist of all elements with BSON numeric types,
  recursively enumerated in the order they occur in the reference
  sample.

* The data-bearing elements of a delta sample must be of the same name
  (including matching names of enclosing documents), and in the same
  order, as the data-bearing elements of the reference sample. In
  practical terms this means that a schema change requires terminating
  the chunk and starting a new chunk with a new reference sample.

* The types of the data-bearing elements in the delta sample need not
  match the type of the corresponding element in the reference sample
  or in other delta samples; the only requirement is that they be
  numeric. This is to allow for efficient representation of metrics
  that vary their representation among the various BSON numeric
  types. The practical consequence of this is that the numeric type of
  the recorded metrics may not be reconstructed after decompression,
  and there may be some edge-case issues related to the differing
  ranges that each numeric type can represent.

* A group of deltas is captured, processed, compressed, and emitted
  together in a single chunk as described below. Processing a group of
  delta samples together allows for much more efficient compression.

Assume a reference sample with a list of metrics m1, m2, m3, ...:

    ref sample: m1, m2, m3, ...

For each subsequent delta sample in the chunk, for each metric compute
the deltas between that metric and the corresponding metric in the
previous sample:

    (sample 1) d11, d12, d13, ...
    (sample 2) d21, d22, d23, ...
    ...
    (sample n) dn1, dn2, dn3, ...

Transpose this array of deltas, so that the deltas for each metric are
adjacent:

    (sample 1) (sample 2) ...  (sample n)
    d11,       d21,       ..., dn1
    d12,       d22,       ..., dn2
    d13,       d23,       ..., dn3
    ...

Treating this array of deltas as a sequence of numbers in row-major
order, run-length encode runs of 0s: replace each run of 0s with a 0
followed by n-1, where n is the length of the run.

Form a packed representation of each number by packing groups of 7
bits, starting with the low-order 7 bits, into bytes, with the
high-order bit of the packed representation indicating whether this is
the last group.

Finally, as described in the previous section, a chunk comprising the
reference sample and sequence of deltas compressed as described in
this section are collected together, zlib compressed, and emitted
wrapped in a BinData field of a document, one document per chunk.


### POC implementation

A proof-of-concept implementation is available.
* Source is in [ftdc.cpp](ftdc.cpp).
* A statically linked Linux binary that should work on most distros is included as [ftdc.linux](ftdc.linux).
* For compilation instructions see the compile() function in [test.sh](test.sh).
* Command is documented at [ftdc.md](ftdc.md).

The ftdc command copies samples from a source to a sink as specified
on the command line, doing compression or decompression as necessary,
depending on the type of the source and sink.

Supported sources include
* uncompressed serverStatus samples obtained live from a mongod instance
* compressed samples from a MongoDB collection (for example local.ftdc)
* pre-recorded uncompressed BSON samples from a .bson file
* compressed samples from a file, for testing purposes.

Supported sinks include
* compressed samples stored to a MongoDB collection (for example, a local.ftdc capped collection)
* uncompressed BSON samples stored to a .bson file
* uncompressed JSON samples stored to a .json file
* compressed samples stored to a file, for testing purposes.
* null sink, for compression and decompression measurement purposes

The following two examples illustrate use of the ftdc command to
simulate a built-in FTDC capability by first obtaining serverStatus
samples from a mongod process and storing them in compressed form in a
MongoDB capped collection, and then extracting, decompressing, and
visualizing the samples.

*Collecting the samples* Obtain samples by executing serverStatus at
the specified host once per second until terminated, and then
compressing and storing them in local.ftdc. If local.ftdc does not
exist it will be created as a 100 MB capped collection.

    ftdc mongodb://host mongodb://host

*Extracting and visualizing the samples* Read all compressed samples
from local.ftdc on the specified host, decompress them, and store them
as JSON documents in ss.json. Then visualize the samples using the
[timeseries tool](https://github.com/10gen/support-tools/tree/master/timeseries).

    ftdc mongodb://host/?ns=local.ftdc ss.json
    python timeseries.py ss:ss.json >ts.html
    open /a "Google Chrome" ts.html


### Space cost

Space requirements and compression ratios were measured on three data
sets collected while running workloads:

* A mixed workload of about 20 k ops/s running under WiredTiger

* The same mixed workload running under mmapv1. Space requirements are
  less for mmapv1 because it collects fewer metrics.

* An idle mongod under WiredTiger. Space requirements drop
  dramatically for an idle workload because most of the deltas are 0.

Details follow:

ss-wt-20k-mixed-600.bson: 3.0.0, wt, ~20 k mixed ops/s, 600 samples @ 1 sample/s, 300 samples per chunk

                           bytes/   incr    comp
                           sample   redn   ratio  MB/day
    
    raw bson                16126    ---     ---    1329
    delta                    4367    73%     4:1     360
    delta+zlib                222    95%    73:1    18.3
    delta+zlib+pack           181    18%    89:1    15.0
    delta+zlib+pack+run       178     2%    91:1    14.7
    
ss-mmapv1-20k-mixed-600.bson: 3.0.0, mmapv1, ~20 k mixed ops/s, 600 samples @ 1 sample/s, 300 samples per chunk

                           bytes/   incr    comp
                           sample   redn   ratio  MB/day
    
    raw bson                11650    ---     ---    960
    delta                    3409    71%     3:1    281
    delta+zlib                112    97%   104:1    9.2
    delta+zlib+pack            92    18%   127:1    7.6
    delta+zlib+pack+run        89     3%   131:1    7.3

ss-wt-idle-600.bson: 3.0.0, wt, idle, 600 samples @ 1 sample/s, 300 samples per chunk

                           bytes/   incr    comp
                           sample   redn   ratio  MB/day
    
    raw bson               16081     ---     ---   1325
    delta                   4367     73%     4:1    360
    delta+zlib                26     99%   619:1    2.1
    delta+zlib+pack           20     23%   804:1    1.6
    delta+zlib+pack+run       18     10%   893:1    1.5


### Effect of chunk size on compression

Larger chunks result in a smaller number of bytes/sample, I believe
for two reasons:

* Fixed overheads, including general zlib overhead and the overhead of
  the full sample are amortized over a larger number of delta samples.

* The samples are transposed so that all samples for a given metric
  are adjacent. Since a given metric will tend to have similar deltas
  from one sample to the next, a larger chunk therefore results in
  longer runs of similar sample deltas.

The effect of chunk size on compression was measured using the same
three sample data sets described in the preceding section.

            ----- bytes/sample ----
    chunk     WT     mmapv1     WT
    size    20kop/s  20kop/s   idle
   
      60      251      138      80
     120      207      101      41
     300      178       89      18
     600      168       44      10

While a larger chunk size decreases storage requirements due to better
compression, it has the drawback that more samples may be lost in case
of a crash. A chunk size of 300 (5 minutes at 1 sample per second) was
chosen for the remainder of the tests.

A more complicated strategy for managing chunks is possible: the last
chunk can be updated more frequently - for example, every 30 seconds -
to reduce the number of samples lost in case of a crash. Then when a
certain number of samples - say 300 - have been accumulated in a
chunk, an new chunk can be started, to keep the chunk from growing in
size indefinitely. This strategy has not been implemented yet; the
time cost would need to be evaluated.

In addition, it may be possible to attempt to write the last sample
chunk on abort or segfault.


### Time cost

CPU cost of obtaining, compressing, and storing samples was estimated
using the POC implementation described above. Measurements were taking
using MongoDB 3.0.1 on OS/X on a MacBook Pro.

These measurements were also confirmed by a more complicated procedure
involving instrumenting the POC implemenation with timers; only the
simpler methodology is presented here.

To estimate the CPU requirements the system time command was used to
measure mongod and the POC client CPU utilization while performing
various tests. In most cases system CPU utilization was excluded
because that mostly represents time related to the client-server
implementation that would not be relevant in an integrated
implementation.

* To estimate CPU time used to process serverStatus, the total user
  CPU time used by mongod while processing 1M serverStatus commands
  was measured. This may overestimate the cost as it includes some
  message processing time that would not be relevant in an integrated
  implementation.

* To estimate CPU time used to process (compress and store) chunks of
  samples, total CPU time of mongod and of the client were measured
  while processing 1M samples. The sample data in this case was
  pre-recorded data.

    * The user CPU time used by the client represents the time required
      to compress the chunks of samples.

    * The CPU time used by mongod represents the time required to
      store the samples. System CPU time was included in this case
      because some system CPU time is used by WT in normal operation,
      but in any case the total CPU time for storing the samples was
      negligible.

Results below. Times shown are per-sample, so the times shown to
compress and store chunks are amortized over the samples in each
chunk.


                             wiredTiger    mmapv1
    serverStatus (mongod)       165 µs      56 µs
    compress chunks (client)     63 µs      46 µs
    store chunks (mongod)         2 µs       1 µs
    total per sample            230 µs     103 µs


### Strawman integration proposal

Assuming the worst case of the scenarios measured, a rate of 1 sample
per second would

* Require about 0.02% or so of a single CPU core, or less than 0.01%
  of the total CPU resources of a typical machine. Assuming this holds
  up under further testing (under way), the performance impact of a
  rate of 1 sample per second should be unmeasurable.

* Require about 100 MB per week of storage. Storing ftdc data for
  a week would be a useful goal because a typical backup strategy with a
  retention of weekly backups for some period of time would ensure
  retention of continuous ftdc data for a corresponding period of
  time. This would be very useful when, as is occasionally the case,
  we are asked to do a post-mortem of a performance-related outage
  substantially after the fact.

Given performance data so far, propose that ftdc collecting
serverStatus samples be integrated into mongod, capturing samples in a
new local.ftdc capped collection, on by default, controlled by the
following parameters:

* ftdc.samplePeriod - floating point seconds between samples. 0
  disables ftdc. Default 1.0.

* ftdc.chunkSize - number of samples per chunk. 0 disables ftdc
  collection. Default 300.

* ftdc.maxSizeMB - maximum size of local.ftdc capped collection, in
  MB. 0 disables ftdc. Default 100 MB.

### Related tooling

Following related tooling is needed. Simplest approach is to keep
these internal for now, possibly to be made public at some point.

* [Timeseries visualization
  tool](https://github.com/10gen/support-tools/tree/master/timeseries). Provides
  support for visualizing decompressed ftdc serverStatus timeseries.

* Utility for decompressing ftdc samples. The POC implementation
  described above may be sufficient for this for internal use.











