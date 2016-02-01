## Tips

* When collecting timeseries data manually to analyze a reproducible
  problem it is best to start the data collection before the onset of
  the problem and to continue to collect data after the end of the
  problem. This will show changes in metrics that are correlated with
  the problem. It's a good idea to give the customer explicit
  instructions in this regard.

* When collecting serverStatus manually for 3.0 a delay of 1 second
  produces manageable file sizes for up to about a day; beyond that a
  lower sampling rate can be used.

* Memory issues often developing slowly, so lower sampling rates can
  generally be used for such issues.




