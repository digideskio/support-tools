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

* Memory issues often developing slowly, so lower sampling rates can
  generally be used for such issues.




