## Examples

![c27449](examples/c27449.png)

* Around 19:50 UTC we see a complete stall in the opcounters, both
  replicated ops and secondary queries.

* Coinciding with this we see high iowait CPU percentage, which means
  everything is stuck waiting for i/o completion.

* Both sdb and sda show a stall in data rates accompanied by long
  queues, high wait times, and high utilization. Since utilization
  measures the ratio between operating rate and capacity, and
  operating rate has dropped during this time, this means that
  effectively capacity has also dropped.

* All of the above point to an issue in the storage layer, which could
  be a problem in the kernel, in device controllers, or the devices
  themselves. Since it affects both sda and sdb, this points to
  something common between the two.


![s22224](examples/s22224.png)

* Initial period of high insert rate was setup for experiment.

* Then a query was run, and memory usage grew. During this time both
  WT cache usage (bytes currently in the cache) and total memory usage
  (current_allocated_bytes) grew. Peak memory usage (read from "max"
  column) is about 13 GB () in excess of WT cache.

* Query has scanned 20M documents (queryExecutor scannedObjects). Note
  that these are all accounted for at once at the end of the query, so
  we see an instanteous bump of 20M documents scanned in 1 second.

* This demonstrates an issue: very high (non-cache) memory utilization
  for this particular query.


