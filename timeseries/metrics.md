## Metrics guide

### serverStatus operation rates

<dl>
  <dt>
    ss opcounters: command (/s)<br/>
    ss opcounters: delete (/s)<br/>
    ss opcounters: getmore (/s)<br/>
    ss opcounters: insert (/s)<br/>
    ss opcounters: query (/s)<br/>
    ss opcounters: update (/s)<br/>
  </dt>
  <dd>
    Basic operation rates.
  </dd>

  <dt>
    ss opcounters repl: command (/s)<br/>
    ss opcounters repl: delete (/s)<br/>
    ss opcounters repl: getmore (/s)<br/>
    ss opcounters repl: insert (/s)<br/>
    ss opcounters repl: query (/s)<br/>
    ss opcounters repl: update (/s)<br/>
  </dt>
  <dd>
    Replicated operation rates. If replicated operations are seen then
    this node must have been a secondary at that time. Note that some
    transformation is done to operations as they are replicated,
    so operation rates seen on the secondary for a given type of
    operation may not be the same as on the primary.
  </dd>

  <dt>
    ss metrics: document deleted (/s)<br/>
    ss metrics: document inserted (/s)<br/>
    ss metrics: document returned (/s)<br/>
    ss metrics: document updated (/s)<br/>
  </dt>
  <dd>
    Low-level operation rates. These may be higher than the
    corresponding opcounter rates above because these counters reflect
    individual document operations. *TBD*: clarify this.
  </dd>

  <dt>
    ss metrics: getLastError wtime num (/s)<br/>
    ss metrics: getLastError wtime totalMillis (/s)<br/>
    ss metrics: getLastError wtimeouts (/s)<br/>
  </dt>
  <dd>
    These metrics report on time spent waiting for write concern,
    whether or not associated with getLastError per se.
  </dd>

  <dt>  
    ss metrics: operation writeConflicts (/s)<br/>
  </dt>
  <dd>
    A high rate of write conflicts indicates document-level write
    contention in WiredTiger.
  </dd>

  <dt>
    ss metrics: operation scanAndOrder (/s)<br/>
    ss metrics: queryExecutor scanned (/s)<br/>
    ss metrics: queryExecutor scannedObjects (/s)<br/>
  </dt>
  <dd>
    High rates of scanned, scanned objects (documents), or
    scan-and-order operations indicate inefficient queries that could
    be improved with appropriate indexes. Correlate this with queries
    in the mongod log to find the culprits; if you point the specify
    the mongod log on the timeseries tool command line (in addition to
    the ftdc data) it will help you find the correlated queries, which
    will show up as spikes on the mongod graphs in length and/or
    number of logged queries.
  </dd>

  <dt>
    ss metrics: operation fastmod (/s)<br/>
    ss metrics: operation idhack (/s)<br/>
    ss metrics: record moves (/s)<br/>
  </dt>
  <dd>
  </dd>

</dl>

### serverStatus command rates

For each of the following metrics related to command execution rate
there is a corresponding metric for failed operations.

<dl>
  <dt>
    ss metrics: commands _getUserCacheGeneration total (/s)<br/>
    ss metrics: commands _isSelf total (/s)<br/>
    ss metrics: commands _mergeAuthzCollections total (/s)<br/>
    ss metrics: commands _migrateClone total (/s)<br/>
  </dt>
  <dd>
  </dd>

  <dt>
    ss metrics: commands _recvChunkAbort total (/s)<br/>
    ss metrics: commands _recvChunkCommit total (/s)<br/>
    ss metrics: commands _recvChunkStart total (/s)<br/>
    ss metrics: commands _recvChunkStatus total (/s)<br/>
  </dt>
  <dd>
    These commands are executed on the recipient shard of a chunk
    migration. A _recvChunkStart command followed by a continuous
    stream of _recvChunkStatus commands and no _recvChunkCommit
    command indicates a long-running or stuck migration.
  </dd>

  <dt>
    ss metrics: commands _transferMods total (/s)<br/>
    ss metrics: commands aggregate total (/s)<br/>
    ss metrics: commands appendOplogNote total (/s)<br/>
    ss metrics: commands applyOps total (/s)<br/>
    ss metrics: commands authSchemaUpgrade total (/s)<br/>
    ss metrics: commands authenticate total (/s)<br/>
    ss metrics: commands availableQueryOptions total (/s)<br/>
    ss metrics: commands buildInfo total (/s)<br/>
    ss metrics: commands checkShardingIndex total (/s)<br/>
    ss metrics: commands cleanupOrphaned total (/s)<br/>
    ss metrics: commands clone total (/s)<br/>
    ss metrics: commands cloneCollection total (/s)<br/>
    ss metrics: commands cloneCollectionAsCapped total (/s)<br/>
    ss metrics: commands collMod total (/s)<br/>
    ss metrics: commands collStats total (/s)<br/>
    ss metrics: commands compact total (/s)<br/>
    ss metrics: commands connPoolStats total (/s)<br/>
    ss metrics: commands connPoolSync total (/s)<br/>
    ss metrics: commands connectionStatus total (/s)<br/>
    ss metrics: commands convertToCapped total (/s)<br/>
    ss metrics: commands copydb total (/s)<br/>
    ss metrics: commands copydbgetnonce total (/s)<br/>
    ss metrics: commands copydbsaslstart total (/s)<br/>
    ss metrics: commands count total (/s)<br/>
    ss metrics: commands create total (/s)<br/>
    ss metrics: commands createIndexes total (/s)<br/>
    ss metrics: commands createRole total (/s)<br/>
    ss metrics: commands createUser total (/s)<br/>
    ss metrics: commands currentOp total (/s)<br/>
    ss metrics: commands currentOpCtx total (/s)<br/>
    ss metrics: commands cursorInfo total (/s)<br/>
    ss metrics: commands dataSize total (/s)<br/>
    ss metrics: commands dbHash total (/s)<br/>
    ss metrics: commands dbStats total (/s)<br/>
    ss metrics: commands delete total (/s)<br/>
    ss metrics: commands diagLogging total (/s)<br/>
    ss metrics: commands distinct total (/s)<br/>
    ss metrics: commands driverOIDTest total (/s)<br/>
    ss metrics: commands drop total (/s)<br/>
    ss metrics: commands dropAllRolesFromDatabase total (/s)<br/>
    ss metrics: commands dropAllUsersFromDatabase total (/s)<br/>
    ss metrics: commands dropDatabase total (/s)<br/>
    ss metrics: commands dropIndexes total (/s)<br/>
    ss metrics: commands dropRole total (/s)<br/>
    ss metrics: commands dropUser total (/s)<br/>
    ss metrics: commands eval total (/s)<br/>
    ss metrics: commands explain total (/s)<br/>
    ss metrics: commands features total (/s)<br/>
    ss metrics: commands filemd5 total (/s)<br/>
    ss metrics: commands find total (/s)<br/>
    ss metrics: commands findAndModify total (/s)<br/>
    ss metrics: commands forceerror total (/s)<br/>
    ss metrics: commands fsync total (/s)<br/>
    ss metrics: commands fsyncUnlock total (/s)<br/>
    ss metrics: commands geoNear total (/s)<br/>
    ss metrics: commands geoSearch total (/s)<br/>
    ss metrics: commands getCmdLineOpts total (/s)<br/>
    ss metrics: commands getLastError total (/s)<br/>
    ss metrics: commands getLog total (/s)<br/>
    ss metrics: commands getMore total (/s)<br/>
    ss metrics: commands getParameter total (/s)<br/>
    ss metrics: commands getPrevError total (/s)<br/>
    ss metrics: commands getShardMap total (/s)<br/>
    ss metrics: commands getShardVersion total (/s)<br/>
    ss metrics: commands getnonce total (/s)<br/>
    ss metrics: commands grantPrivilegesToRole total (/s)<br/>
    ss metrics: commands grantRolesToRole total (/s)<br/>
    ss metrics: commands grantRolesToUser total (/s)<br/>
    ss metrics: commands group total (/s)<br/>
    ss metrics: commands handshake total (/s)<br/>
    ss metrics: commands hostInfo total (/s)<br/>
    ss metrics: commands insert total (/s)<br/>
    ss metrics: commands invalidateUserCache total (/s)<br/>
    ss metrics: commands isMaster total (/s)<br/>
    ss metrics: commands killCursors total (/s)<br/>
    ss metrics: commands killOp total (/s)<br/>
    ss metrics: commands listCollections total (/s)<br/>
    ss metrics: commands listCommands total (/s)<br/>
    ss metrics: commands listDatabases total (/s)<br/>
    ss metrics: commands listIndexes total (/s)<br/>
    ss metrics: commands logRotate total (/s)<br/>
    ss metrics: commands logout total (/s)<br/>
    ss metrics: commands mapReduce total (/s)<br/>
    ss metrics: commands mapreduce/shardedfinish total (/s)<br/>
    ss metrics: commands medianKey total (/s)<br/>
    ss metrics: commands mergeChunks total (/s)<br/>
  </dt>
  <dd>
  </dd>

  <dt>
    ss metrics: commands moveChunk total (/s)<br/>
  </dt>
  <dd>
   This command is executed on the donor shard of a chunk migration.
  </dd>

  <dt>
    ss metrics: commands parallelCollectionScan total (/s)<br/>
    ss metrics: commands ping total (/s)<br/>
    ss metrics: commands planCacheClear total (/s)<br/>
    ss metrics: commands planCacheClearFilters total (/s)<br/>
    ss metrics: commands planCacheListFilters total (/s)<br/>
    ss metrics: commands planCacheListPlans total (/s)<br/>
    ss metrics: commands planCacheListQueryShapes total (/s)<br/>
    ss metrics: commands planCacheSetFilter total (/s)<br/>
    ss metrics: commands profile total (/s)<br/>
    ss metrics: commands reIndex total (/s)<br/>
    ss metrics: commands renameCollection total (/s)<br/>
    ss metrics: commands repairCursor total (/s)<br/>
    ss metrics: commands repairDatabase total (/s)<br/>
    ss metrics: commands replSetDeclareElectionWinner total (/s)<br/>
    ss metrics: commands replSetElect total (/s)<br/>
    ss metrics: commands replSetFreeze total (/s)<br/>
    ss metrics: commands replSetFresh total (/s)<br/>
    ss metrics: commands replSetGetConfig total (/s)<br/>
    ss metrics: commands replSetGetRBID total (/s)<br/>
    ss metrics: commands replSetGetStatus total (/s)<br/>
    ss metrics: commands replSetHeartbeat total (/s)<br/>
    ss metrics: commands replSetInitiate total (/s)<br/>
    ss metrics: commands replSetMaintenance total (/s)<br/>
    ss metrics: commands replSetReconfig total (/s)<br/>
    ss metrics: commands replSetRequestVotes total (/s)<br/>
    ss metrics: commands replSetStepDown total (/s)<br/>
    ss metrics: commands replSetSyncFrom total (/s)<br/>
    ss metrics: commands replSetUpdatePosition total (/s)<br/>
    ss metrics: commands resetError total (/s)<br/>
    ss metrics: commands resync total (/s)<br/>
    ss metrics: commands revokePrivilegesFromRole total (/s)<br/>
    ss metrics: commands revokeRolesFromRole total (/s)<br/>
    ss metrics: commands revokeRolesFromUser total (/s)<br/>
    ss metrics: commands rolesInfo total (/s)<br/>
    ss metrics: commands saslContinue total (/s)<br/>
    ss metrics: commands saslStart total (/s)<br/>
    ss metrics: commands serverStatus total (/s)<br/>
    ss metrics: commands setParameter total (/s)<br/>
    ss metrics: commands setShardVersion total (/s)<br/>
    ss metrics: commands shardConnPoolStats total (/s)<br/>
    ss metrics: commands shardingState total (/s)<br/>
    ss metrics: commands shutdown total (/s)<br/>
    ss metrics: commands splitChunk total (/s)<br/>
    ss metrics: commands splitVector total (/s)<br/>
    ss metrics: commands stageDebug total (/s)<br/>
    ss metrics: commands text total (/s)<br/>
    ss metrics: commands top total (/s)<br/>
    ss metrics: commands touch total (/s)<br/>
    ss metrics: commands unsetSharding total (/s)<br/>
    ss metrics: commands update total (/s)<br/>
    ss metrics: commands updateRole total (/s)<br/>
    ss metrics: commands updateUser total (/s)<br/>
    ss metrics: commands usersInfo total (/s)<br/>
    ss metrics: commands validate total (/s)<br/>
    ss metrics: commands whatsmyuri total (/s)<br/>
    ss metrics: commands writebacklisten total (/s)<br/>
  </dt>
</dl>

### serverStatus general

<dl>

  <dt>
    ss asserts: msg (/s)<br/>
    ss asserts: regular (/s)<br/>
    ss asserts: rollovers (/s)<br/>
    ss asserts: user (/s)<br/>
    ss asserts: warning (/s)<br/>
  </dt>
  <dd>
  </dd>

  <dt>
    ss connections: available<br/>
    ss connections: created (/s)<br/>
    ss connections: current<br/>
  </dt>
  <dd>
    Connection spikes associated with performance problems are often a
    sign of client-side timeouts and retries: when client-side
    timeouts occur generally the operations continue on the server, so
    when the client retries it only increases the load and makes the
    problem worse. To avoid this we
    [recommend](http://jmikola.net/blog/mongodb-timeouts/) using
    server-side timeouts.
  </dd>

  <dt>
    ss metrics: cursor open noTimeout<br/>
    ss metrics: cursor open pinned<br/>
    ss metrics: cursor open total<br/>
    ss metrics: cursor timedOut (/s)<br/>
    ss cursors: clientCursors_size<br/>
    ss cursors: note<br/>
    ss cursors: pinned<br/>
    ss cursors: timedOut<br/>
    ss cursors: totalNoTimeout<br/>
  </dt>
  <dd>
  </dd>

  <dt>
    ss cursors: totalOpen<br/>
  </dt>
  <dd>
     A large number of open cursors can cause performance
     problems. Note that these metrics reflect mongod client cursors;
     there are related WiredTiger statistics for WT cursors and
     sessions, but those are managed in a cache so aren't directly
     related to mongod client cursors.
  </dd>

  <dt>
    ss metrics: ttl deletedDocuments<br/>
    ss metrics: ttl deletedDocuments (/s)<br/>
    ss metrics: ttl passes (/s)<br/>
  </dt>
  <dd>
  </dd>

  <dt>
    ss network: bytesIn (MB/s)<br/>
    ss network: bytesOut (MB/s)<br/>
    ss network: numRequests (/s)<br/>
  </dt>
  <dd>
     Network bytes in and out can give a general sense of the overall
     "weight" of operations being processed by mongod.
  </dd>

  <dt>
    ss uptime: <br/>
    ss uptimeEstimate: <br/>
    ss uptimeMillis: <br/>
  </dt>
  <dd>
    Use the uptime statistic to identify mongod restarts.
  </dd>

  <dt>
    ss ok: <br/>
    ss pid: <br/>
    ss process: <br/>
    ss storageEngine: <br/>
    ss version: <br/>
  </dt>
  <dd>
    Version and storageEngine are string data so they aren't shown in
    the timeseries graphs; however they can be determined by using the
    timeseries "@" command which will display metadata, such as
    version and storageEngine, at a selected time.
  </dd>

</dl>

### serverStatus locking and queuing

<dl>

  <dt>
    ss global: active read queue<br/>
    ss global: active write queue<br/>
  </dt>
  <dd>
    Total number of client threads currently performing an operation,
    including those waiting for some lock.
  </dd>

  <dt>
    ss global: read queue<br/>
    ss global: write queue<br/>
  </dt>
  <dd>
    Of the active client threads, number waiting for a lock. *NOTE*:
    due to [SERVER-21859](https://jira.mongodb.org/browse/SERVER-21859)
    this does not include clients queued waiting for the global
    lock. Use "timeAcquiringMicros global", described below, to get
    that information.
  </dd>
</dl>

In the following set of metrics, &lt;resource&gt; is one of
* Collection
* Database
* Global
* Metadata
* oplog
* MMAPV1Journal

and &lt;lock&gt; is one of

* R - MODE_S - read lock
* W - MODE_X - write lock
* r - MODE_IS - read intent lock
* w - MODE_IX - write intent lock

<dl>
  <dt>
    ss locks: &lt;resource&gt; acquireCount &lt;lock&gt; (/s)<br/>
  </dt>
  <dd>
    This is bumped every time the respective lock is
    acquired. Normally this happens relatively frequently, but on
    occasion an isolated bump in this metric can point to a lock
    acquisition that has caused a stall; the stall will show up in the
    timeAcuiringMicros metrics, as described below.
  </dd>
  <dt>
    ss locks: &lt;resource&gt; acquireWaitCount &lt;lock&gt; (/s)<br/>
  </dt>
  <dd>
  </dd>

  <dt>
    ss locks: &lt;resource&gt; deadlockCount &lt;lock&gt; (/s)<br/>
  </dt>
  <dd>
    This is bad.
  </dd>

  <dt>
    ss locks: &lt;resource&gt; timeAcquiringMicros &lt;lock&gt; (/s)<br/>
  </dt>
  <dd>
    The timeAcquiringMicros metric indicates the total amount of time,
    in microseconds, across all threads spent waiting for a given
    lock, per second. Divide this by 1,000,000 to get the number of
    threads waiting for that resource at a given time.
  </dd>
</dl>

<dl>
  <dt>
    ss wiredTiger: concurrentTransactions read available<br/>
    ss wiredTiger: concurrentTransactions read out<br/>
    ss wiredTiger: concurrentTransactions read totalTickets<br/>
    ss wiredTiger: concurrentTransactions write available<br/>
    ss wiredTiger: concurrentTransactions write out<br/>
    ss wiredTiger: concurrentTransactions write totalTickets<br/>
  </dt>
  <dd>
    The WiredTiger "ticket" mechanism is a gate in the mongod
    integraton layer to prevent a very large number of concurrent
    threads executing in WT, which would cause performance issues. The
    number of tickets "out" indicates how many active operations are
    inside WT, and can be used to diagnose bottlenecks.  If all of the
    active clients have a ticket "out", or this number is saturated at
    the "totalTickets" number (128 by default), this indicates a
    bottleneck in WT, which could be caused by contention for access
    to WT data structures, or by i/o contention.
  </dd>
</dl>


### serverStatus system info

<dl>

  <dt>

    ss extra_info: availPageFileMB (MB)<br/>
    ss extra_info: heap_usage_bytes (MB)<br/>
    ss extra_info: note<br/>
    ss extra_info: page_faults (/s)<br/>
    ss extra_info: ramMB (MB)<br/>
    ss extra_info: totalPageFileMB (MB)<br/>
    ss extra_info: usagePageFileMB (MB)<br/>

  </dt>

</dl>

### serverStatus memory usage

<dl>

  <dt>

    ss mem: bits<br/>
    ss mem: mapped (MB)<br/>
    ss mem: mappedWithJournal (MB)<br/>
    ss mem: resident (MB)<br/>
    ss mem: supported<br/>
    ss mem: virtual (MB)<br/>

    ss tcmalloc: generic current_allocated_bytes (MB)<br/>
    ss tcmalloc: generic heap_size (MB)<br/>
    ss tcmalloc: tcmalloc aggressive_memory_decommit (MB)<br/>
    ss tcmalloc: tcmalloc central_cache_free_bytes (MB)<br/>
    ss tcmalloc: tcmalloc current_total_thread_cache_bytes (MB)<br/>
    ss tcmalloc: tcmalloc max_total_thread_cache_bytes (MB)<br/>
    ss tcmalloc: tcmalloc pageheap_free_bytes (MB)<br/>
    ss tcmalloc: tcmalloc pageheap_unmapped_bytes (MB)<br/>
    ss tcmalloc: tcmalloc thread_cache_free_bytes (MB)<br/>
    ss tcmalloc: tcmalloc transfer_cache_free_bytes (MB)<br/>

  </dt>

</dl>

### replication

<dl>

  <dt>

    ss metrics: repl apply batches num (/s)<br/>
    ss metrics: repl apply batches totalMillis (/s)<br/>
    ss metrics: repl apply ops (/s)<br/>
    ss metrics: repl buffer count<br/>
    ss metrics: repl buffer maxSizeBytes (MB)<br/>
    ss metrics: repl buffer sizeBytes (MB)<br/>
    ss metrics: repl executor counters cancels (/s)<br/>
    ss metrics: repl executor counters eventCreated (/s)<br/>
    ss metrics: repl executor counters eventWait (/s)<br/>
    ss metrics: repl executor counters scheduledDBWork (/s)<br/>
    ss metrics: repl executor counters scheduledNetCmd (/s)<br/>
    ss metrics: repl executor counters scheduledWork (/s)<br/>
    ss metrics: repl executor counters scheduledWorkAt (/s)<br/>
    ss metrics: repl executor counters scheduledXclWork (/s)<br/>
    ss metrics: repl executor counters schedulingFailures (/s)<br/>
    ss metrics: repl executor counters waits (/s)<br/>
    ss metrics: repl executor eventWaiters<br/>
    ss metrics: repl executor queues dbWorkInProgress<br/>
    ss metrics: repl executor queues exclusiveInProgress<br/>
    ss metrics: repl executor queues free<br/>
    ss metrics: repl executor queues networkInProgress<br/>
    ss metrics: repl executor queues ready<br/>
    ss metrics: repl executor queues sleepers<br/>
    ss metrics: repl executor shuttingDown<br/>
    ss metrics: repl executor unsignaledEvents<br/>
    ss metrics: repl network bytes (MB/s)<br/>
    ss metrics: repl network getmores num (/s)<br/>
    ss metrics: repl network getmores totalMillis (/s)<br/>
    ss metrics: repl network ops (/s)<br/>
    ss metrics: repl network readersCreated (/s)<br/>
    ss metrics: repl preload docs num (/s)<br/>
    ss metrics: repl preload docs totalMillis (/s)<br/>
    ss metrics: repl preload indexes num (/s)<br/>
    ss metrics: repl preload indexes totalMillis (/s)<br/>

  </dt>

</dl>

### mmapv1

<dl>

  <dt>

    ss dur: commits (/s)<br/>
    ss dur: commitsInWriteLock (/s)<br/>
    ss dur: compression<br/>
    ss dur: earlyCommits (/s)<br/>
    ss dur: journaledMB (/s)<br/>
    ss dur: timeMs commitsInWriteLockMicros (/s)<br/>
    ss dur: timeMs dt<br/>
    ss dur: timeMs prepLogBuffer<br/>
    ss dur: timeMs remapPrivateView<br/>
    ss dur: timeMs writeToDataFiles<br/>
    ss dur: timeMs writeToJournal<br/>
    ss dur: writeToDataFilesMB (/s)<br/>

    ss backgroundFlushing: average_ms<br/>
    ss backgroundFlushing: flushes<br/>
    ss backgroundFlushing: last_finished<br/>
    ss backgroundFlushing: last_ms<br/>
    ss backgroundFlushing: total_ms<br/>

    ss metrics: storage freelist search bucketExhausted (/s)<br/>
    ss metrics: storage freelist search requests (/s)<br/>
    ss metrics: storage freelist search scanned (/s)<br/>

    ss locks: MMAPV1Journal acquireCount R (/s)<br/>
    ss locks: MMAPV1Journal acquireCount W (/s)<br/>
    ss locks: MMAPV1Journal acquireCount r (/s)<br/>
    ss locks: MMAPV1Journal acquireCount w (/s)<br/>
    ss locks: MMAPV1Journal acquireWaitCount R (/s)<br/>
    ss locks: MMAPV1Journal acquireWaitCount W (/s)<br/>
    ss locks: MMAPV1Journal acquireWaitCount r (/s)<br/>
    ss locks: MMAPV1Journal acquireWaitCount w (/s)<br/>
    ss locks: MMAPV1Journal deadlockCount R (/s)<br/>
    ss locks: MMAPV1Journal deadlockCount W (/s)<br/>
    ss locks: MMAPV1Journal deadlockCount r (/s)<br/>
    ss locks: MMAPV1Journal deadlockCount w (/s)<br/>
    ss locks: MMAPV1Journal timeAcquiringMicros R (/s)<br/>
    ss locks: MMAPV1Journal timeAcquiringMicros W (/s)<br/>
    ss locks: MMAPV1Journal timeAcquiringMicros r (/s)<br/>
    ss locks: MMAPV1Journal timeAcquiringMicros w (/s)<br/>

  </dt>

</dl>

### WiredTiger

<dl>

  <dt>

    ss wiredTiger: concurrentTransactions read available<br/>
    ss wiredTiger: concurrentTransactions read out<br/>
    ss wiredTiger: concurrentTransactions read totalTickets<br/>
    ss wiredTiger: concurrentTransactions write available<br/>
    ss wiredTiger: concurrentTransactions write out<br/>
    ss wiredTiger: concurrentTransactions write totalTickets<br/>
    ss wiredTiger: uri<br/>
    ss writeBacksQueued: <br/>
<!--
    ss wt LSM: application work units currently queued<br/>
    ss wt LSM: bloom filter false positives (/s)<br/>
    ss wt LSM: bloom filter hits (/s)<br/>
    ss wt LSM: bloom filter misses (/s)<br/>
    ss wt LSM: bloom filter pages evicted from cache (/s)<br/>
    ss wt LSM: bloom filter pages read into cache (/s)<br/>
    ss wt LSM: bloom filters in the LSM tree<br/>
    ss wt LSM: chunks in the LSM tree<br/>
    ss wt LSM: highest merge generation in the LSM tree<br/>
    ss wt LSM: merge work units currently queued<br/>
    ss wt LSM: queries that could have benefited from a Bloom filter that did not ex (/s)<br/>
    ss wt LSM: rows merged in an LSM tree (/s)<br/>
    ss wt LSM: sleep for LSM checkpoint throttle (/s)<br/>
    ss wt LSM: sleep for LSM merge throttle (/s)<br/>
    ss wt LSM: switch work units currently queued<br/>
    ss wt LSM: total size of bloom filters<br/>
    ss wt LSM: tree maintenance operations discarded (/s)<br/>
    ss wt LSM: tree maintenance operations executed (/s)<br/>
    ss wt LSM: tree maintenance operations scheduled (/s)<br/>
    ss wt LSM: tree queue hit maximum<br/>
    ss wt async: current work queue length<br/>
    ss wt async: maximum work queue length<br/>
    ss wt async: number of allocation state races (/s)<br/>
    ss wt async: number of flush calls (/s)<br/>
    ss wt async: number of operation slots viewed for allocation (/s)<br/>
    ss wt async: number of times operation allocation failed (/s)<br/>
    ss wt async: number of times worker found no work (/s)<br/>
    ss wt async: total allocations (/s)<br/>
    ss wt async: total compact calls (/s)<br/>
    ss wt async: total insert calls (/s)<br/>
    ss wt async: total remove calls (/s)<br/>
    ss wt async: total search calls (/s)<br/>
    ss wt async: total update calls (/s)<br/>
-->
    ss wt block-manager: allocations requiring file extension (/s)<br/>
    ss wt block-manager: blocks allocated (/s)<br/>
    ss wt block-manager: blocks freed (/s)<br/>
    ss wt block-manager: blocks pre-loaded (/s)<br/>
    ss wt block-manager: blocks read (/s)<br/>
    ss wt block-manager: blocks written (/s)<br/>
    ss wt block-manager: bytes read (MB/s)<br/>
    ss wt block-manager: bytes written (MB/s)<br/>
    ss wt block-manager: checkpoint size<br/>
    ss wt block-manager: file allocation unit size<br/>
    ss wt block-manager: file bytes available for reuse (MB)<br/>
    ss wt block-manager: file magic number<br/>
    ss wt block-manager: file major version number<br/>
    ss wt block-manager: file size in bytes (MB)<br/>
    ss wt block-manager: mapped blocks read (/s)<br/>
    ss wt block-manager: mapped bytes read (MB/s)<br/>
    ss wt block-manager: minor version number<br/>
    ss wt btree: column-store fixed-size leaf pages<br/>
    ss wt btree: column-store internal pages<br/>
    ss wt btree: column-store variable-size deleted values<br/>
    ss wt btree: column-store variable-size leaf pages<br/>
    ss wt btree: cursor create calls (/s)<br/>
    ss wt btree: cursor insert calls (/s)<br/>
    ss wt btree: cursor next calls (/s)<br/>
    ss wt btree: cursor prev calls (/s)<br/>
    ss wt btree: cursor remove calls (/s)<br/>
    ss wt btree: cursor reset calls (/s)<br/>
    ss wt btree: cursor search calls (/s)<br/>
    ss wt btree: cursor search near calls (/s)<br/>
    ss wt btree: cursor update calls (/s)<br/>
    ss wt btree: fixed-record size<br/>
    ss wt btree: maximum internal page item size<br/>
    ss wt btree: maximum internal page size<br/>
    ss wt btree: maximum leaf page item size<br/>
    ss wt btree: maximum leaf page size<br/>
    ss wt btree: maximum tree depth<br/>
    ss wt btree: number of key/value pairs<br/>
    ss wt btree: overflow pages<br/>
    ss wt btree: pages rewritten by compaction (/s)<br/>
    ss wt btree: row-store internal pages<br/>
    ss wt btree: row-store leaf pages<br/>
  </dt>
  <dd>
  </dd>
  <dt>
    ss wt cache: bytes currently in the cache (MB)<br/>
  </dt>
  <dd>
      Normally this number is kept at 80% of the configured maximum
      ("maximum bytes configured" metric) in order to allow room for
      growth. When the cache becomes completely full expect to see
      write stalls.
  </dd>
  <dt>
    ss wt cache: bytes read into cache (MB/s)<br/>
    ss wt cache: bytes written from cache (MB/s)<br/>
    ss wt cache: checkpoint blocked page eviction (/s)<br/>
    ss wt cache: data source pages selected for eviction unable to be evicted<br/>
    ss wt cache: eviction server candidate queue empty when topping up (/s)<br/>
    ss wt cache: eviction server candidate queue not empty when topping up (/s)<br/>
    ss wt cache: eviction server evicting pages (/s)<br/>
    ss wt cache: eviction server populating queue, but not evicting pages (/s)<br/>
    ss wt cache: eviction server unable to reach eviction goal (delta)<br/>
    ss wt cache: eviction worker thread evicting pages (/s)<br/>
    ss wt cache: failed eviction of pages that exceeded the in-memory maximum (/s)<br/>
    ss wt cache: hazard pointer blocked page eviction (/s)<br/>
    ss wt cache: in-memory page passed criteria to be split (/s)<br/>
    ss wt cache: in-memory page splits (/s)<br/>
    ss wt cache: internal pages evicted (/s)<br/>
    ss wt cache: internal pages split during eviction (/s)<br/>
    ss wt cache: leaf pages split during eviction (/s)<br/>
    ss wt cache: lookaside table insert calls (/s)<br/>
    ss wt cache: lookaside table remove calls (/s)<br/>
  </dt>
  <dd>
  </dd>

  <dt>
    ss wt cache: maximum bytes configured (MB)<br/>
  </dt>
  <dd>
      Amount of memory configured for WT cache, either by the user or
      by the default setting.
  </dd>

  <dt>
    ss wt cache: maximum page size at eviction (MB)<br/>
    ss wt cache: modified pages evicted (/s)<br/>
    ss wt cache: overflow pages read into cache (/s)<br/>
    ss wt cache: overflow values cached in memory<br/>
    ss wt cache: page split during eviction deepened the tree (/s)<br/>
    ss wt cache: page written requiring lookaside records (/s)<br/>
    ss wt cache: pages currently held in the cache<br/>
    ss wt cache: pages evicted because they exceeded the in-memory maximum (/s)<br/>
    ss wt cache: pages evicted because they had chains of deleted items (/s)<br/>
    ss wt cache: pages evicted by application threads (/s)<br/>
    ss wt cache: pages read into cache (/s)<br/>
    ss wt cache: pages read into cache requiring lookaside entries (/s)<br/>
    ss wt cache: pages selected for eviction unable to be evicted (/s)<br/>
    ss wt cache: pages split during eviction (/s)<br/>
    ss wt cache: pages walked for eviction (/s)<br/>
    ss wt cache: pages written from cache (/s)<br/>
    ss wt cache: pages written requiring in-memory restoration (/s)<br/>
    ss wt cache: percentage overhead<br/>
    ss wt cache: tracked bytes belonging to internal pages in the cache (MB)<br/>
    ss wt cache: tracked bytes belonging to leaf pages in the cache (MB)<br/>
    ss wt cache: tracked bytes belonging to overflow pages in the cache (MB)<br/>
    ss wt cache: tracked dirty bytes in the cache (MB)<br/>
    ss wt cache: tracked dirty pages in the cache<br/>
    ss wt cache: unmodified pages evicted (/s)<br/>
    ss wt compression: compressed pages read (/s)<br/>
    ss wt compression: compressed pages written (/s)<br/>
    ss wt compression: page written failed to compress (/s)<br/>
    ss wt compression: page written was too small to compress (/s)<br/>
    ss wt compression: raw compression call failed, additional data available (/s)<br/>
    ss wt compression: raw compression call failed, no additional data available (/s)<br/>
    ss wt compression: raw compression call succeeded (/s)<br/>
    ss wt connection: files currently open<br/>
    ss wt connection: memory allocations (/s)<br/>
    ss wt connection: memory frees (/s)<br/>
    ss wt connection: memory re-allocations (/s)<br/>
    ss wt connection: pthread mutex condition wait calls (/s)<br/>
    ss wt connection: pthread mutex shared lock read-lock calls (/s)<br/>
    ss wt connection: pthread mutex shared lock write-lock calls (/s)<br/>
    ss wt connection: total read I/Os (/s)<br/>
    ss wt connection: total write I/Os (/s)<br/>
    ss wt cursor: bulk-loaded cursor-insert calls (/s)<br/>
    ss wt cursor: create calls (/s)<br/>
    ss wt cursor: cursor create calls (/s)<br/>
    ss wt cursor: cursor insert calls (/s)<br/>
    ss wt cursor: cursor next calls (/s)<br/>
    ss wt cursor: cursor prev calls (/s)<br/>
    ss wt cursor: cursor remove calls (/s)<br/>
    ss wt cursor: cursor reset calls (/s)<br/>
    ss wt cursor: cursor restarted searches (/s)<br/>
    ss wt cursor: cursor search calls (/s)<br/>
    ss wt cursor: cursor search near calls (/s)<br/>
    ss wt cursor: cursor update calls (/s)<br/>
    ss wt cursor: cursor-insert key and value bytes inserted (MB)<br/>
    ss wt cursor: cursor-remove key bytes removed (MB)<br/>
    ss wt cursor: cursor-update value bytes updated (MB)<br/>
    ss wt cursor: insert calls (/s)<br/>
    ss wt cursor: next calls (/s)<br/>
    ss wt cursor: prev calls (/s)<br/>
    ss wt cursor: remove calls (/s)<br/>
    ss wt cursor: reset calls (/s)<br/>
    ss wt cursor: search calls (/s)<br/>
    ss wt cursor: search near calls (/s)<br/>
    ss wt cursor: truncate calls (/s)<br/>
    ss wt cursor: update calls (/s)<br/>
    ss wt data-handle: connection candidate referenced (/s)<br/>
    ss wt data-handle: connection data handles currently active<br/>
    ss wt data-handle: connection dhandles swept (/s)<br/>
    ss wt data-handle: connection sweep candidate became referenced<br/>
    ss wt data-handle: connection sweep dhandles closed (/s)<br/>
    ss wt data-handle: connection sweep dhandles removed from hash list (/s)<br/>
    ss wt data-handle: connection sweep time-of-death sets (/s)<br/>
    ss wt data-handle: connection sweeps (/s)<br/>
    ss wt data-handle: connection time-of-death sets (/s)<br/>
    ss wt data-handle: session dhandles swept (/s)<br/>
    ss wt data-handle: session sweep attempts (/s)<br/>
    ss wt log: busy returns attempting to switch slots (/s)<br/>
    ss wt log: consolidated slot closures (/s)<br/>
    ss wt log: consolidated slot join races (/s)<br/>
    ss wt log: consolidated slot join transitions (/s)<br/>
    ss wt log: consolidated slot joins (/s)<br/>
    ss wt log: consolidated slot unbuffered writes (/s)<br/>
    ss wt log: failed to find a slot large enough for record (/s)<br/>
    ss wt log: joins per closure<br/>
    ss wt log: log buffer size increases (/s)<br/>
    ss wt log: log bytes of payload data (MB/s)<br/>
    ss wt log: log bytes written (MB/s)<br/>
    ss wt log: log files manually zero-filled (/s)<br/>
    ss wt log: log flush operations (/s)<br/>
    ss wt log: log read operations (/s)<br/>
    ss wt log: log records compressed (/s)<br/>
    ss wt log: log records not compressed (/s)<br/>
    ss wt log: log records too small to compress (/s)<br/>
    ss wt log: log release advances write LSN (/s)<br/>
    ss wt log: log scan operations (/s)<br/>
    ss wt log: log scan records requiring two reads (/s)<br/>
    ss wt log: log server thread advances write LSN (/s)<br/>
    ss wt log: log sync operations (/s)<br/>
    ss wt log: log sync_dir operations (/s)<br/>
    ss wt log: log write operations (/s)<br/>
    ss wt log: logging bytes consolidated (MB/s)<br/>
    ss wt log: maximum log file size (MB)<br/>
    ss wt log: number of pre-allocated log files to create<br/>
    ss wt log: pre-allocated log files not ready and missed (/s)<br/>
    ss wt log: pre-allocated log files prepared (/s)<br/>
    ss wt log: pre-allocated log files used (/s)<br/>
    ss wt log: record size exceeded maximum (/s)<br/>
    ss wt log: records processed by log scan (/s)<br/>
    ss wt log: slots selected for switching that were unavailable (/s)<br/>
    ss wt log: total in-memory size of compressed records (MB)<br/>
    ss wt log: total log buffer size (MB)<br/>
    ss wt log: total size of compressed records (MB)<br/>
    ss wt log: written slots coalesced (/s)<br/>
    ss wt log: yields waiting for previous log file close (/s)<br/>
    ss wt reconciliation: dictionary matches (/s)<br/>
    ss wt reconciliation: fast-path pages deleted (/s)<br/>
    ss wt reconciliation: internal page key bytes discarded using suffix compression (MB)<br/>
    ss wt reconciliation: internal page multi-block writes (/s)<br/>
    ss wt reconciliation: internal-page overflow keys (/s)<br/>
    ss wt reconciliation: leaf page key bytes discarded using prefix compression (MB)<br/>
    ss wt reconciliation: leaf page multi-block writes (/s)<br/>
    ss wt reconciliation: leaf-page overflow keys (/s)<br/>
    ss wt reconciliation: maximum blocks required for a page<br/>
    ss wt reconciliation: overflow values written (/s)<br/>
    ss wt reconciliation: page checksum matches (/s)<br/>
    ss wt reconciliation: page reconciliation calls (/s)<br/>
    ss wt reconciliation: page reconciliation calls for eviction (/s)<br/>
    ss wt reconciliation: pages deleted (/s)<br/>
    ss wt reconciliation: split bytes currently awaiting free (MB)<br/>
    ss wt reconciliation: split objects currently awaiting free<br/>
    ss wt session: object compaction<br/>
    ss wt session: open cursor count<br/>
    ss wt session: open session count<br/>
    ss wt thread-yield: page acquire busy blocked (/s)<br/>
    ss wt thread-yield: page acquire eviction blocked (/s)<br/>
    ss wt thread-yield: page acquire locked blocked (/s)<br/>
    ss wt thread-yield: page acquire read blocked (/s)<br/>
    ss wt thread-yield: page acquire time sleeping (usecs) (/s)<br/>
    ss wt transaction: number of named snapshots created (/s)<br/>
    ss wt transaction: number of named snapshots dropped (/s)<br/>
    ss wt transaction: transaction begins (/s)<br/>
  </dt>
  <dd>
  </dd>
  <dt>
    ss wt transaction: transaction checkpoint currently running<br/>
  </dt>
  <dd>
    1 if a checkpoint is running, 0 if it is not. Note that since this
    is a sampled value, not a cumulative counter, if a checkpoint is
    short or the captured or displayed samples are too far apart this
    metric may miss checkpoints. In this case the "transaction
    checkpoints (delta)" metric may provide better information about
    the occurrence of checkpoints, and "transaction checkpoint most
    recent time (msecs)" may provide better information about the
    length of checkpoints.
  </dd>
  <dt>
    ss wt transaction: transaction checkpoint generation<br/>
    ss wt transaction: transaction checkpoint max time (msecs)<br/>
    ss wt transaction: transaction checkpoint min time (msecs)<br/>
    ss wt transaction: transaction checkpoint most recent time (msecs)<br/>
    ss wt transaction: transaction checkpoint total time (msecs)<br/>
    ss wt transaction: transaction checkpoints (delta)<br/>
    ss wt transaction: transaction failures due to cache overflow (/s)<br/>
    ss wt transaction: transaction range of IDs currently pinned<br/>
    ss wt transaction: transaction range of IDs currently pinned by a checkpoint<br/>
    ss wt transaction: transaction range of IDs currently pinned by named snapshots<br/>
    ss wt transaction: transaction sync calls (/s)<br/>
    ss wt transaction: transactions committed (/s)<br/>
    ss wt transaction: transactions rolled back (/s)<br/>
    ss wt transaction: update conflicts (/s)<br/>

  </dt>

</dl>

### Collection stats

Note: these also appear as oplog stats in ftdc data.

<dl>

  <dt>

    cs: avgObjSize<br/>
    cs: capped<br/>
    cs: count<br/>
    cs: errmsg<br/>
    cs: maxSize (MB)<br/>
    cs: nindexes<br/>
    cs: ns<br/>
    cs: ok<br/>
    cs: size (MB)<br/>
    cs: sleepCount (/s)<br/>
    cs: sleepMS (/s)<br/>
    cs: storageSize (MB)<br/>
    cs: totalIndexSize (MB)<br/>

    cs wt: block-manager allocations requiring file extension (/s)<br/>
    cs wt: block-manager blocks allocated (/s)<br/>
    cs wt: block-manager blocks freed (/s)<br/>
    cs wt: block-manager checkpoint size (MB)<br/>
    cs wt: block-manager file allocation unit size<br/>
    cs wt: block-manager file bytes available for reuse (MB)<br/>
    cs wt: block-manager file magic number<br/>
    cs wt: block-manager file major version number<br/>
    cs wt: block-manager file size in bytes (MB)<br/>
    cs wt: block-manager minor version number<br/>
    cs wt: btree btree checkpoint generation<br/>
    cs wt: btree column-store fixed-size leaf pages<br/>
    cs wt: btree column-store internal pages<br/>
    cs wt: btree column-store variable-size deleted values<br/>
    cs wt: btree column-store variable-size leaf pages<br/>
    cs wt: btree fixed-record size<br/>
    cs wt: btree maximum internal page key size<br/>
    cs wt: btree maximum internal page size<br/>
    cs wt: btree maximum leaf page key size<br/>
    cs wt: btree maximum leaf page size<br/>
    cs wt: btree maximum leaf page value size<br/>
    cs wt: btree maximum tree depth<br/>
    cs wt: btree number of key/value pairs<br/>
    cs wt: btree overflow pages<br/>
    cs wt: btree pages rewritten by compaction (/s)<br/>
    cs wt: btree row-store internal pages<br/>
    cs wt: btree row-store leaf pages<br/>
    cs wt: cache bytes read into cache (MB/s)<br/>
    cs wt: cache bytes written from cache (MB/s)<br/>
    cs wt: cache checkpoint blocked page eviction<br/>
    cs wt: cache data source pages selected for eviction unable to be evicted (/s)<br/>
    cs wt: cache hazard pointer blocked page eviction (/s)<br/>
    cs wt: cache in-memory page splits (/s)<br/>
    cs wt: cache internal pages evicted (/s)<br/>
    cs wt: cache modified pages evicted (/s)<br/>
    cs wt: cache overflow pages read into cache (/s)<br/>
    cs wt: cache overflow values cached in memory<br/>
    cs wt: cache page split during eviction deepened the tree (/s)<br/>
    cs wt: cache pages read into cache (/s)<br/>
    cs wt: cache pages split during eviction (/s)<br/>
    cs wt: cache pages written from cache (/s)<br/>
    cs wt: cache unmodified pages evicted (/s)<br/>
    cs wt: compression compressed pages read (/s)<br/>
    cs wt: compression compressed pages written (/s)<br/>
    cs wt: compression page written failed to compress (/s)<br/>
    cs wt: compression page written was too small to compress (/s)<br/>
    cs wt: compression raw compression call failed, additional data available (/s)<br/>
    cs wt: compression raw compression call failed, no additional data available (/s)<br/>
    cs wt: compression raw compression call succeeded (/s)<br/>
    cs wt: creationString<br/>
    cs wt: cursor bulk-loaded cursor-insert calls (/s)<br/>
    cs wt: cursor create calls (/s)<br/>
    cs wt: cursor cursor-insert key and value bytes inserted (/s)<br/>
    cs wt: cursor cursor-remove key bytes removed (/s)<br/>
    cs wt: cursor cursor-update value bytes updated (/s)<br/>
    cs wt: cursor insert calls (/s)<br/>
    cs wt: cursor next calls (/s)<br/>
    cs wt: cursor prev calls (/s)<br/>
    cs wt: cursor remove calls (/s)<br/>
    cs wt: cursor reset calls (/s)<br/>
    cs wt: cursor search calls (/s)<br/>
    cs wt: cursor search near calls (/s)<br/>
    cs wt: cursor update calls (/s)<br/>
    cs wt: metadata formatVersion<br/>
    cs wt: metadata oplogKeyExtractionVersion<br/>
    cs wt: reconciliation dictionary matches (/s)<br/>
    cs wt: reconciliation internal page key bytes discarded using suffix compression (/s)<br/>
    cs wt: reconciliation internal page multi-block writes (/s)<br/>
    cs wt: reconciliation internal-page overflow keys<br/>
    cs wt: reconciliation leaf page key bytes discarded using prefix compression (/s)<br/>
    cs wt: reconciliation leaf page multi-block writes (/s)<br/>
    cs wt: reconciliation leaf-page overflow keys<br/>
    cs wt: reconciliation maximum blocks required for a page<br/>
    cs wt: reconciliation overflow values written (/s)<br/>
    cs wt: reconciliation page checksum matches (/s)<br/>
    cs wt: reconciliation page reconciliation calls (/s)<br/>
    cs wt: reconciliation page reconciliation calls for eviction (/s)<br/>
    cs wt: reconciliation pages deleted (/s)<br/>
    cs wt: session object compaction<br/>
    cs wt: session open cursor count<br/>
    cs wt: transaction update conflicts (/s)<br/>
    cs wt: type<br/>
    cs wt: uri<br/>
  </dt>
</dl>

