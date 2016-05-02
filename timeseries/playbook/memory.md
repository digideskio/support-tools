## Prerequisite knowledge

* Timeseries tool
* FTDC
* https://github.com/10gen/support-tools/blob/master/timeseries/metrics.md
* https://github.com/10gen/support-tools/blob/master/timeseries/README.md        


## Background: Memory usage overview

This section summarizes the organization of overall mongod process
memory usage, both outside and inside the tcmalloc
allocator. Indentation below indicates containment.

* **mem: virtual**: overall process virtual address space.
   * code and initialized data.
   * thread stacks, one per connection.
   * **generic heap_size**: virtual memory under control of the
     allocator.
      * **current_allocated_bytes**: memory allocated by mongod
         * **bytes currently in the cache**: WT cache memory
         * **allocated minus wt cache**: memory allocated outside
           the WT cache
      * freed memory used by mongod and then returned to the allocator
         * **central_cache_free_bytes**: small free regions
         * **pageheap_free_bytes**: large free regions backed by physical memory
         * **pageheap_unmapped_bytes** large free regions not backed by physical memory



## Problem: Performance problems related to high cache utilization

### Problem summary and impact

Generally WT aims to limit cache utilization to 80% of the configured
maximum because the purpose of the cache is to provide a buffer
between application operations and disk i/o.  When the WT cache usage
exceeds 95% of the configured maximum performance decreases and
significant operation latencies will result. Two thresholds are of
note:

* When the cache reaches 95% full, application threads will start
  doing evictions, increasing operation latencies. This is tracked by
  the **application threads doing evictions** metric.

* When the cache reaches 100% full, application threads may have to
  wait for the cache, also increasing operation latencies. [Q:
  **pthread mutex calls** metric?]

### Symptoms and diagnosis

* Performance declines, including
  * slower operation rates
  * logged slow operations
  * queuing indicated by **active readers/writers** and
    **concurrentTransactions read/write out** (aka "tickets")
  * cache utilization exceeds 95% (**bytes currently in the cache** / **maximum bytes configured**)

### Causes and remediations

* Cause: WT cache eviction algorithmic issue

   * Symptoms: high rate of **pages walked for eviction** (typically many
   millions per second) relative to pages evicted, which is sum of
   **modified pages evicted** and **unmodified pages evicted** (typically
   thousands or tens of thousands per second)

   * Remediation: see SERVER-..., SERVER-...


* Cause: disk write bottleneck

   * Symptoms: high proportion of dirty data in cache; *consistent*
     high disk utilization (bursts of 100% utilization are normal and
     expected)

   * Remediation: improve storage performance; throttle workload

* Cause: CPU bottleneck related to reconciliation

   * Symptoms: ...

   * Remediation: ...


* Cause: extended transaction during checkpoints

   * Symptoms: cache fills during checkpoints (**checkpoint currently
     running**), accompanied by large value for **pages pinned by
     checkpoint**)

   * Remediation: ...



## Problem: Excess memory allocated outside the WT cache

### Problem summary and impact 

Generally memory usage outside the WT cache should remain well
bounded.  However there are exceptions, and on occasion bugs have been
found in this area.

### Symptoms and diagnosis

* overall large memory usage
* **allocated minus wt cache** metric grows large

### Causes and remediation

* Cause: various, tbd

   * Remediation: smaller cache, identify offending query, more
     memory, cursor timeouts; escalate within team for further
     analysis


## Problem: Memory fragmentation

### Problem summary and impact

Ideally free memory tracked by tcmalloc should remain small so that
unallocated memory can be used for kernel file cache. If free memory
becomes large this can impact performance, and result in out-of-memory
condition.

### Symptoms and diagnosis

* performance issues or out of memory, accompanied by following
  (more-or-less equivalent):

  * **total free memory** (which is the sum of **pageheap_free_bytes**
    and **central_cache_free_bytes**) is large relative to
    **current_allocated_bytes**

  * **heap_size** minus **pageheap_unmapped_bytes** is large relative
      to **current_allocated_bytes**

  * **mem: resident** is large relative to **current_allocated_bytes**


### Causes and remediation

* Cause: At some point in the past a large amount of memory was
  allocated outside the WT cache and then freed, resulting in a
  current large **heap_size** and **total_free_bytes**.

   * Diagnosis: examine memory usage history since last mongod restart
     (**uptime**) to find high-water mark for
     **current_allocated_bytes**

   * Remediation: see section "Excess memory allocated outside the WT cache"

* Cause: the workload has resulted in memory fragmentation: there is
  memory that has been freed, but it cannot be reused to satisfy new
  allocation requests because it is fragmented.

   * Diagnosis: examine memory usage history since last mongod restart
     (**uptime**) to rule out a large **heap_size** due to a previous
     large **curent_allocated_bytes**

   * Remediation: see SERVER-..., SERVER-...


