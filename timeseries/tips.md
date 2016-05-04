## Tips

* Customer some customers may be reluctant to upload the binary
  diagnostic.data without knowing what's in it. Here is some suggested
  wording, taken from [this
  comment](https://jira.mongodb.org/browse/SERVER-22000?focusedCommentId=1121384&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-1121384):
  
  I understand your concern. We don't at the moment have a viewer for
  the data that is ready for external use. However you can see the
  data that it collects
  [here](https://github.com/mongodb/mongo/blob/master/src/mongo/db/ftdc/ftdc_mongod.cpp#L314),
  consisting of the following, with the commands you can run from the
  mongo shell to see what data is collected:

        serverStatus: db.serverStatus({tcmalloc: true})
        replSetGetStatus: rs.status()
        collStats for local.oplog.rs: db.getSiblingDB('local').oplog.rs.stats()
        getCmdLineOpts: db.adminCommand({getCmdLineOpts: true})
        buildInfo: db.adminCommand({buildInfo: true})
        hostInfo: db.adminCommand({hostInfo: true})

* You can use the "@" command to view FTDC metadata, including for
  example host name, amount of memory, MongoDB version, command line
  options, O/S information, and so on.

* The diagnostic.data directory that contains the FTDC data in 3.2 and
  later can be safely copied off of a running instance. It is already
  compressed so additional compression is not beneficial (but is also
  harmless). The size is capped at 100 MB so it can be directly
  attached to a JIRA ticket. This is sufficient to capture 4-7 days
  worth of data for a busy instance, significantly longer if it is
  idle.  Suggested wording: "Please archive (tar or zip) the
  $dbpath/diagnostic.data directory and attach it to this ticket."

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

* If you have a very large serverStatus timeseries generated manually,
  for example a length timeseries sampled at 1-second intervals, you
  can subsample it by taking every nth line before giving it to the
  timeseries tool. For example if you take every 10th line from a
  timeseries at 1-second intervals this effectively gives you a
  timeseries sampled at 10-second intervals. Most of the metrics are
  cumulative counters from which rates are computed, and subsampling
  will give you average rates over the longer interval for such
  counters. Here's a simple perl script for taking every nth line:

      # example: every 10 <ss.log >ss-every10.log
      function every {
          every=$1; shift
          perl -n -e "\$. % $every == 1 && print" $*
      }

* WT i/o tends to be bursty, and it's not unusual to see 100%
  utilization during checkpoints, and this by itself does not
  necessarily indicate a disk bottleneck. Note that if you are looking
  at a graph that is showing an extended period it may appear that the
  disk is constantly 100% utilized when in fact if you zoom in you
  will see that it is only peaking at 100% briefly during checkpoints.

* You can get a rough estimate of replication lag from serverStatus
  metrics on the secondary by dividing "repl buffer sizeBytes", which
  is the amount of replicated data buffered on the secondary awaiting
  application, by the rate of incoming data, given by the "repl
  network bytes" metric. Note that this is only valid if "repl buffer
  sizeBytes" doesn't exceed the cap, "repl buffer maxSizeBytes", and
  if there isn't a network bottleneck causing significant replication
  lag.
