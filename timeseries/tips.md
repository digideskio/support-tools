## Tips

* When collecting timeseries data manually to analyze a reproducible
  problem it is best to start the data collection before the onset of
  the problem and to continue to collect data after the end of the
  problem.

  So for example if it's a sporadic problem, collect data for long
  enough to capture a few occurrences of the problem, or at least to
  cover the transition from the good state into the bad state. If it's
  a problem that ramps up over time, begin data collection with the
  system in a good state and continue until it gets into the bad
  state, plus a little time after that.

  This will show changes in metrics that are correlated with the
  problem, which will identify potential causes. It's a good idea to
  give the customer explicit instructions in this regard.

* When collecting serverStatus manually for 3.0 a delay of 1 second
  produces manageable file sizes for up to about a day; beyond that a
  lower sampling rate can be used.

* When collecting serverStatus manually for 3.0 the mongo command may
  need to be adjusted to do authentication if that is required.

* Memory issues often developing slowly, so lower sampling rates can
  generally be used for such issues.

* Rule of thumb: if you are diagnosing an issue where some metric has
  gone low, look for a correlated metric that has gone high, and that
  could be a candidate for a culprit. Generally speaking, metrics
  reflect consumption of some resource or resources, and if one
  particular metric is low, it will often be because of contention for
  some resource, and there will be other metrics that are high,
  pointing to what is consuming that resource.

* The iostat command does not include timezone information in its
  output, so you will need to specify that on the timeseries command
  line. If you don't have direct information from the customer about
  the timezone, the timezone in the mongod log will generally be the
  correct timezone for iostat. For example, if mongod log timestamps
  have timezone "-0500", specify "--itz -5" on the timeseries command
  line.

* Most metrics are cumulative counters of some event, and are
  typically differentiated to get a rate for display. These metrics
  provide accurate information even when the captured or displayed
  sample rate is low: the displayed rate is the average over the
  displayed sample interval. However some metrics record instantaneous
  values; for example, the "checkpoint currently running" is 0 or 1
  according to whether a checkpoint is running at that particular
  sample. If the monitored event (checkpoint in this case) is short,
  or if the sample rate is low, events can be missed by such
  metrics. Other sampling artifacts, similar to moiré patterns or beat
  notes in music, can result from a sampling rate that is close to the
  rate of a periodically signal. Exercise caution when interpreting
  any metrics that isn't based on cumulative counters, that is, which
  is not identified as a rate ("/s") of some quantity.

* Connection spikes associated with performance problems are often a
  sign of client-side timeouts and retries: when client-side timeouts
  occur generally the operations continue on the server, so when the
  client retries it only increases the load and makes the problem
  worse. To avoid this we
  [recommend](http://jmikola.net/blog/mongodb-timeouts) using
  server-side timeouts.
