import collections
import datetime as dt
import re
import process

import graphing
import util

################################################################################
#
# built-in descriptors
#
# levels:
# 1 - important basic non-engine-specific
# 2 - add basic engine-specific
# 3 - everything not of dubious meaning
# 9 - dubious meaning; investigate these further
#

descriptors = []     # descriptors loaded from various def files
split_ords = {}      # sort order for each split_key - first occurrence of split_key in def file
descriptor_ord = 0

def descriptor(**desc):
    global descriptor_ord
    desc['_ord'] = descriptor_ord
    if 'split_key' in desc:
        split_key = desc['split_key']
        if not split_key in split_ords:
            split_ords[split_key] = desc['_ord']
    if 'split_on_key_match' in desc:
        split_on_key_match = desc['split_on_key_match']
        if not split_on_key_match in split_ords:
            split_ords[split_on_key_match] = desc['_ord']
    descriptors.append(desc)
    descriptor_ord += 1

def list_descriptors():
    for desc in sorted(descriptors, key=lambda desc: desc['name'].lower()):
        d = collections.defaultdict(lambda: '...')
        d.update(desc)
        util.msg(graphing.get(d, 'name'))

#
# generic grep descriptor
# usage: timeseries 'grep(pat=pat):fn
#     pat - re to locate data; must include one re group identifying data
#     fn - file to be searched
# this descriptor supplies a generic re to identify a timestamp
# assumes the timestamp precedes the data
#

descriptor(
    name = 'grep {pat}',
    re = '^.*(....-..-..T..:..:..(?:\....)?Z?|(?:... )?... .. .... ..:..:..).*{pat}',
    file_type = 'text',
    parser = 're'
)


#
# generic csv
#

descriptor(
    name = 'csv {fn}: {key}',
    file_type = 'text',
    parser = process.parse_csv,
    time_key = 'time',
    split_on_key_match = '(?P<key>.*)',
)

#
# windows csv - special header processing
#

def win_headers(series, headers):
    tz = headers[0].split('(')[3].strip(')')
    tz = dt.timedelta(hours = -float(tz)/60)
    for s in series:
        s.tz = tz
    return [' '.join(h.split('\\')[3:]) for h in headers]

descriptor(
    name = 'win {fn}: {field_name}',
    file_type = 'text',
    parser = process.parse_csv,
    time_key = 'time',
    process_headers = win_headers, # xxx?
    split_on_key_match = '(?P<key>.*)',
)

#
# serverStatus json output, for example:
# mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep($delay*1000)}"
#

MB = 1024*1024

def desc_units(scale, rate):
    units = ''
    if scale==MB: units = 'MB'
    if rate=='delta': units += 'delta'
    elif rate: units += '/s'
    return units

def ss(json_data, name=None, scale=1, rate=False, units=None, level=3, **kwargs):

    if not name:
        name = ' '.join(s for s in json_data[1:] if s!='floatApprox')
        name = 'ss ' + json_data[0] +  ': ' + name
        if not units: units = desc_units(scale, rate)
        if units: units = ' (' + units + ')'
        name = name + units

    # for parsing direct serverStatus command output
    descriptor(
        file_type = 'json',
        parser = process.parse_json,
        name = name,
        data_key = util.join(*json_data),
        time_key = util.join('localTime'),
        scale = scale,
        rate = rate,
        level = level,
        **kwargs
    )

    # for parsing serverStatus section of ftdc represented as json documents
    descriptor(
        file_type = 'json',
        parser = process.parse_json,
        name = 'ftdc ' + name,
        data_key = util.join('serverStatus', *json_data),
        time_key = util.join('serverStatus', 'localTime'),
        scale = scale,
        rate = rate,
        level = level,
        **kwargs
    )

    # for parsing serverStatus section of ftdc represented as metrics dictionaries
    descriptor(
        file_type = 'metrics',
        parser = process.parse_ftdc,
        name = 'ftdc ' + name,
        data_key = util.join('serverStatus', *json_data),
        time_key = util.join('serverStatus', 'localTime'),
        scale = scale,
        rate = rate,
        level = level,
        time_scale = 1000.0, # times are in ms
        **kwargs
    )

def ss_opcounter(opcounter, **kwargs):
    ss(
        json_data = ['opcounters', opcounter],
        merge = 'ss_opcounters',
        name = 'ss opcounters: ' + opcounter + ' (/s)',
        level = 1,
        rate = True,
        **kwargs
    )
    ss(
        json_data = ['opcountersRepl', opcounter],
        merge = 'ss_opcounters_repl',
        name = 'ss opcounters repl: ' + opcounter + ' (/s)',
        level = 1,
        rate = True,
        **kwargs
    )

ss_opcounter('insert')
ss_opcounter('update')
ss_opcounter('delete')
ss_opcounter('query')
ss_opcounter('getmore')
ss_opcounter('command')

ss(
    json_data = ['globalLock', 'activeClients', 'readers'],
    name = 'ss global: active read queue',
    merge = '_ss_active_queue',
    level = 1
)

ss(
    json_data = ['globalLock', 'activeClients', 'writers'],
    name = 'ss global: active write queue',
    merge = '_ss_active_queue',
    level = 1
)

ss(
    json_data = ['globalLock', 'currentQueue', 'readers'],
    name = 'ss global: read queue',
    merge = '_ss_queue',
    level = 1
)


ss(
    json_data = ['globalLock', 'currentQueue', 'writers'],
    name = 'ss global: write queue',
    merge = '_ss_queue',
    level = 1
)

ss(['globalLock', 'activeClients', 'total'], level=99)
ss(['globalLock', 'currentQueue', 'total'], level=99)
ss(['globalLock', 'totalTime'], level=99)

ss(["asserts", "msg"], rate=True, level=1)
ss(["asserts", "regular"], rate=True, level=1)
ss(["asserts", "rollovers"], rate=True, level=1)
ss(["asserts", "user"], rate=True, level=1)
ss(["asserts", "warning"], rate=True, level=1)
ss(["backgroundFlushing", "average_ms"], level=9)
ss(["backgroundFlushing", "flushes"], level=9)
ss(["backgroundFlushing", "last_finished"], level=9)
ss(["backgroundFlushing", "last_ms"], level=9)
ss(["backgroundFlushing", "total_ms"], level=9)
ss(["connections", "available"], level=9)
ss(["connections", "current"], level=1)
ss(["connections", "totalCreated"], name="ss connections: created (/s)", level=3, rate=True)
ss(["cursors", "clientCursors_size"], level=9)
ss(["cursors", "note"], level=99)
ss(["cursors", "pinned"], level=9)
ss(["cursors", "timedOut"], level=9)
ss(["cursors", "totalNoTimeout"], level=9)
ss(["cursors", "totalOpen"], level=9)
ss(["dur", "commits"], rate=True) # CHECK rc5
ss(["dur", "commitsInWriteLock"], rate=True) # CHECK rc5
ss(["dur", "compression"]) # CHECK rc5
ss(["dur", "earlyCommits"], rate=True) # CHECK rc5
ss(["dur", "journaledMB"], rate=True) # CHECK rc5
ss(["dur", "timeMs", "commitsInWriteLockMicros"], rate=True) # CHECK rc5
ss(["dur", "timeMs", "dt"]) # CHECK rc5
ss(["dur", "timeMs", "prepLogBuffer"]) # CHECK rc5
ss(["dur", "timeMs", "remapPrivateView"]) # CHECK rc5
ss(["dur", "timeMs", "writeToDataFiles"]) # CHECK rc5
ss(["dur", "timeMs", "writeToJournal"]) # CHECK rc5
ss(["dur", "writeToDataFilesMB"], rate=True) # CHECK rc5
ss(["extra_info", "heap_usage_bytes"], scale=MB, wrap=2.0**31, level=9)
ss(["extra_info", "note"], level=99)
ss(["extra_info", "page_faults"], rate=True, level=1)
ss(['extra_info', 'availPageFileMB'], units="MB", level=1)
ss(['extra_info', 'ramMB'], units="MB", level=1)
ss(['extra_info', 'totalPageFileMB'], units="MB", level=1)
ss(['extra_info', 'usagePageFileMB'], units="MB", level=1)
ss(['tcmalloc', 'generic', 'current_allocated_bytes'], scale=MB, level=1)
ss(['tcmalloc', 'generic', 'heap_size'], scale=MB, level=1)
ss(['tcmalloc', 'tcmalloc', 'pageheap_free_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'pageheap_unmapped_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'max_total_thread_cache_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'current_total_thread_cache_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'central_cache_free_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'transfer_cache_free_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'thread_cache_free_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'aggressive_memory_decommit'], scale=MB, level=4) # ???
ss(["host"], level=99)

def ss_lock(name):
    for a in ["acquireCount", "acquireWaitCount", "deadlockCount", "timeAcquiringMicros"]:
        for b in ["r", "w", "R", "W"]:
            ss(["locks", name, a, b], rate=True, level=9)

ss_lock("Collection") # CHECK rc5
ss_lock("Database") # CHECK rc5
ss_lock("Global") # CHECK rc5
ss_lock("MMAPV1Journal") # CHECK rc5
ss_lock("Metadata") # CHECK rc5
ss_lock("oplog") # CHECK rc5

ss(["mem", "bits"], level=99)
ss(["mem", "mapped"], scale=MB)
ss(["mem", "mappedWithJournal"], scale=MB)
ss(["mem", "resident"], units="MB")
ss(["mem", "supported"], level=99)
ss(["mem", "virtual"], units="MB", level=1)

# don't know what this is
ss(["metrics", "commands", "<UNKNOWN>"], rate=True, level=4)

# XXX make these auto-split instead of listing explicitly
def ss_command(command, level=4):
    ss(["metrics", "commands", command, "total"], rate=True, level=level)
    ss(["metrics", "commands", command, "failed"], rate=True, level=level)

ss_command("collStats")
ss_command("count")
ss_command("createIndexes")
ss_command("currentOp")
ss_command("drop")
ss_command("fsyncUnlock")
ss_command("getMore")
ss_command("getnonce")
ss_command("insert")
ss_command("isMaster")
ss_command("killCursors")
ss_command("killOp")
ss_command("mapreduce.shardedfinish")
ss_command("ping")
ss_command("replSetDeclareElectionWinner")
ss_command("replSetRequestVotes")
ss_command("serverStatus")
ss_command("update")
ss_command("whatsmyuri")
ss_command('_getUserCacheGeneration')
ss_command('_isSelf')
ss_command('_mergeAuthzCollections')
ss_command('_migrateClone')
ss_command('_recvChunkAbort')
ss_command('_recvChunkCommit')
ss_command('_recvChunkStart')
ss_command('_recvChunkStatus')
ss_command('_transferMods')
ss_command('aggregate')
ss_command('appendOplogNote')
ss_command('applyOps')
ss_command('authSchemaUpgrade')
ss_command('authenticate')
ss_command('availableQueryOptions')
ss_command('buildInfo')
ss_command('checkShardingIndex')
ss_command('cleanupOrphaned')
ss_command('clone')
ss_command('cloneCollection')
ss_command('cloneCollectionAsCapped')
ss_command('collMod')
ss_command('compact')
ss_command('connPoolStats')
ss_command('connPoolSync')
ss_command('connectionStatus')
ss_command('convertToCapped')
ss_command('copydb')
ss_command('copydbgetnonce')
ss_command('copydbsaslstart')
ss_command('create')
ss_command('createRole')
ss_command('createUser')
ss_command('currentOpCtx')
ss_command('cursorInfo')
ss_command('dataSize')
ss_command('dbHash')
ss_command('dbStats')
ss_command('delete')
ss_command('diagLogging')
ss_command('distinct')
ss_command('driverOIDTest')
ss_command('dropAllRolesFromDatabase')
ss_command('dropAllUsersFromDatabase')
ss_command('dropDatabase')
ss_command('dropIndexes')
ss_command('dropRole')
ss_command('dropUser')
ss_command('eval')
ss_command('explain')
ss_command('features')
ss_command('filemd5')
ss_command('find')
ss_command('findAndModify')
ss_command('forceerror')
ss_command('fsync')
ss_command('geoNear')
ss_command('geoSearch')
ss_command('getCmdLineOpts')
ss_command('getLastError')
ss_command('getLog')
ss_command('getParameter')
ss_command('getPrevError')
ss_command('getShardMap')
ss_command('getShardVersion')
ss_command('grantPrivilegesToRole')
ss_command('grantRolesToRole')
ss_command('grantRolesToUser')
ss_command('group')
ss_command('handshake')
ss_command('hostInfo')
ss_command('invalidateUserCache')
ss_command('listCollections')
ss_command('listCommands')
ss_command('listDatabases')
ss_command('listIndexes')
ss_command('logRotate')
ss_command('logout')
ss_command('mapReduce')
ss_command('mapreduce')
ss_command('medianKey')
ss_command('mergeChunks')
ss_command('moveChunk')
ss_command('parallelCollectionScan')
ss_command('planCacheClear')
ss_command('planCacheClearFilters')
ss_command('planCacheListFilters')
ss_command('planCacheListPlans')
ss_command('planCacheListQueryShapes')
ss_command('planCacheSetFilter')
ss_command('profile')
ss_command('reIndex')
ss_command('renameCollection')
ss_command('repairCursor')
ss_command('repairDatabase')
ss_command('replSetElect')
ss_command('replSetFreeze')
ss_command('replSetFresh')
ss_command('replSetGetConfig')
ss_command('replSetGetRBID')
ss_command('replSetGetStatus')
ss_command('replSetHeartbeat')
ss_command('replSetInitiate')
ss_command('replSetMaintenance')
ss_command('replSetReconfig')
ss_command('replSetStepDown')
ss_command('replSetSyncFrom')
ss_command('replSetUpdatePosition')
ss_command('resetError')
ss_command('resync')
ss_command('revokePrivilegesFromRole')
ss_command('revokeRolesFromRole')
ss_command('revokeRolesFromUser')
ss_command('rolesInfo')
ss_command('saslContinue')
ss_command('saslStart')
ss_command('setParameter')
ss_command('setShardVersion')
ss_command('shardConnPoolStats')
ss_command('shardingState')
ss_command('shutdown')
ss_command('splitChunk')
ss_command('splitVector')
ss_command('stageDebug')
ss_command('text')
ss_command('top')
ss_command('touch')
ss_command('unsetSharding')
ss_command('updateRole')
ss_command('updateUser')
ss_command('usersInfo')
ss_command('validate')
ss_command('writebacklisten')


ss(["metrics", "cursor", "open", "noTimeout"])
ss(["metrics", "cursor", "open", "pinned"])
ss(["metrics", "cursor", "open", "total"])
ss(["metrics", "cursor", "timedOut"], rate=True)
ss(["metrics", "document", "deleted"], rate=True)
ss(["metrics", "document", "inserted"], rate=True)
ss(["metrics", "document", "returned"], rate=True)
ss(["metrics", "document", "updated"], rate=True)
ss(["metrics", "getLastError", "wtime", "num"], rate=True)
ss(["metrics", "getLastError", "wtime", "totalMillis"], rate=True)
ss(["metrics", "getLastError", "wtimeouts"], rate=True)
ss(["metrics", "operation", "fastmod"], rate=True)
ss(["metrics", "operation", "idhack"], rate=True)
ss(["metrics", "operation", "scanAndOrder"], rate=True)
ss(["metrics", "operation", "writeConflicts"], rate=True) # CHECK
ss(["metrics", "queryExecutor", "scanned"], rate=True)
ss(["metrics", "queryExecutor", "scannedObjects"], rate=True)
ss(["metrics", "record", "moves"], rate=True)
ss(["metrics", "repl", "apply", "batches", "num"], rate=True)
ss(["metrics", "repl", "apply", "batches", "totalMillis"], rate=True)
ss(["metrics", "repl", "apply", "ops"], rate=True)
ss(["metrics", "repl", "buffer", "count"])
ss(["metrics", "repl", "buffer", "maxSizeBytes"], scale=MB, level=4)
ss(["metrics", "repl", "buffer", "sizeBytes"], scale=MB)
ss(["metrics", "repl", "network", "bytes"], rate=True, scale=MB)
ss(["metrics", "repl", "network", "getmores", "num"], rate=True)
ss(["metrics", "repl", "network", "getmores", "totalMillis"], rate=True)
ss(["metrics", "repl", "network", "ops"], rate=True)
ss(["metrics", "repl", "network", "readersCreated"], rate=True)
ss(["metrics", "repl", "preload", "docs", "num"], rate=True)
ss(["metrics", "repl", "preload", "docs", "totalMillis"], rate=True)
ss(["metrics", "repl", "preload", "indexes", "num"], rate=True)
ss(["metrics", "repl", "preload", "indexes", "totalMillis"], rate=True)
ss(["metrics", "storage", "freelist", "search", "bucketExhausted"], rate=True)
ss(["metrics", "storage", "freelist", "search", "requests"], rate=True)
ss(["metrics", "storage", "freelist", "search", "scanned"], rate=True)
ss(["metrics", "ttl", "deletedDocuments"])
ss(["metrics", "ttl", "deletedDocuments"], rate=True)
ss(["metrics", "ttl", "passes"], rate=True)
ss(["network", "bytesIn"], rate=True, scale=MB, merge='network bytes', level=1)
ss(["network", "bytesOut"], rate=True, scale=MB, merge='network bytes', level=1)
ss(["network", "numRequests"], rate=True)
ss(["ok"], level=99) # CHECK
ss(["pid"], level=99) # CHECK
ss(["process"], level=99) # CHECK
ss(["storageEngine"], level=99) # CHECK
ss(["uptime"], level=3)
ss(["uptimeEstimate"], level=99) # CHECK
ss(["uptimeMillis"], level=99) # CHECK
ss(["version"], level=99) # CHECK
ss(["writeBacksQueued"], level=9) # CHECK


def cs(json_data, name=None, scale=1, rate=False, units=None, level=3, **kwargs):

    if not units: units = desc_units(scale, rate)
    if units: units = ' (' + units + ')'
    if not name:
        if json_data[0]=='wiredTiger':
            json_name = 'cs wt: ' + ' '.join(json_data[1:]) + units
            ftdc_name = 'ftdc oplog wt: ' + ' '.join(json_data[1:]) + units
        else:
            json_name = 'cs: ' + ' '.join(json_data) + units
            ftdc_name = 'ftdc oplog: ' + ' '.join(json_data) + units

    # bare cs
    descriptor(
        file_type = 'json',
        parser = process.parse_json,
        name = json_name,
        data_key = util.join(*json_data),
        time_key = util.join('time'),
        scale = scale,
        rate = rate,
        level = level,
        **kwargs
    )

    # oplog stats in ftdc data
    descriptor(
        file_type = 'metrics',
        parser = process.parse_ftdc,
        name = ftdc_name,
        data_key = util.join('local.oplog.rs.stats', *json_data),
        time_key = util.join('local.oplog.rs.stats', 'start'),
        scale = scale,
        rate = rate,
        level = 1 if level==1 else 5,
        time_scale = 1000.0,
        **kwargs
    )



cs(["capped"], level=99)
cs(["count"], level=1)
cs(["nindexes"], level=9)
cs(["ns"], level=99)
cs(["ok"], level=99)
cs(["size"], scale=MB, level=1)
cs(["maxSize"], scale=MB, level=1)
cs(["storageSize"], scale=MB, level=1)
cs(["totalIndexSize"], scale=MB, level=1)
cs(["avgObjSize"], level=1)
cs(["sleepCount"], rate=True)
cs(["sleepMS"], rate=True)
cs(["wiredTiger", "LSM", "bloom filter false positives"], level=99)
cs(["wiredTiger", "LSM", "bloom filter hits"], level=99)
cs(["wiredTiger", "LSM", "bloom filter misses"], level=99)
cs(["wiredTiger", "LSM", "bloom filter pages evicted from cache"], level=99)
cs(["wiredTiger", "LSM", "bloom filter pages read into cache"], level=99)
cs(["wiredTiger", "LSM", "bloom filters in the LSM tree"], level=99)
cs(["wiredTiger", "LSM", "chunks in the LSM tree"], level=99)
cs(["wiredTiger", "LSM", "highest merge generation in the LSM tree"], level=99)
cs(["wiredTiger", "LSM", "queries that could have benefited from a Bloom filter that did not exist"], level=99)
cs(["wiredTiger", "LSM", "sleep for LSM checkpoint throttle"], level=99)
cs(["wiredTiger", "LSM", "sleep for LSM merge throttle"], level=99)
cs(["wiredTiger", "LSM", "total size of bloom filters"], level=99)
cs(["wiredTiger", "block-manager", "allocations requiring file extension"], rate=True)
cs(["wiredTiger", "block-manager", "blocks allocated"], rate=True)
cs(["wiredTiger", "block-manager", "blocks freed"], rate=True)
cs(["wiredTiger", "block-manager", "checkpoint size"], scale=MB)
cs(["wiredTiger", "block-manager", "file allocation unit size"], level=99)
cs(["wiredTiger", "block-manager", "file bytes available for reuse"], scale=MB)
cs(["wiredTiger", "block-manager", "file magic number"], level=99)
cs(["wiredTiger", "block-manager", "file major version number"], level=99)
cs(["wiredTiger", "block-manager", "file size in bytes"], scale=MB)
cs(["wiredTiger", "block-manager", "minor version number"], level=99)
cs(["wiredTiger", "btree", "btree checkpoint generation"])
cs(["wiredTiger", "btree", "column-store fixed-size leaf pages"], level=99)
cs(["wiredTiger", "btree", "column-store internal pages"], level=99)
cs(["wiredTiger", "btree", "column-store variable-size deleted values"], level=99)
cs(["wiredTiger", "btree", "column-store variable-size leaf pages"], level=99)
cs(["wiredTiger", "btree", "fixed-record size"])
cs(["wiredTiger", "btree", "maximum internal page key size"])
cs(["wiredTiger", "btree", "maximum internal page size"])
cs(["wiredTiger", "btree", "maximum leaf page key size"])
cs(["wiredTiger", "btree", "maximum leaf page size"])
cs(["wiredTiger", "btree", "maximum leaf page value size"])
cs(["wiredTiger", "btree", "maximum tree depth"])
cs(["wiredTiger", "btree", "number of key/value pairs"])
cs(["wiredTiger", "btree", "overflow pages"])
cs(["wiredTiger", "btree", "pages rewritten by compaction"], rate=True)
cs(["wiredTiger", "btree", "row-store internal pages"])
cs(["wiredTiger", "btree", "row-store leaf pages"])
cs(["wiredTiger", "cache", "bytes read into cache"], rate=True, scale=MB)
cs(["wiredTiger", "cache", "bytes written from cache"], rate=True, scale=MB)
cs(["wiredTiger", "cache", "checkpoint blocked page eviction"])
cs(["wiredTiger", "cache", "data source pages selected for eviction unable to be evicted"], rate=True)
cs(["wiredTiger", "cache", "hazard pointer blocked page eviction"], rate=True)
cs(["wiredTiger", "cache", "in-memory page splits"], rate=True)
cs(["wiredTiger", "cache", "internal pages evicted"], rate=True)
cs(["wiredTiger", "cache", "modified pages evicted"], rate=True)
cs(["wiredTiger", "cache", "overflow pages read into cache"], rate=True)
cs(["wiredTiger", "cache", "overflow values cached in memory"])
cs(["wiredTiger", "cache", "pages read into cache"], rate=True)
cs(["wiredTiger", "cache", "pages split during eviction"], rate=True)
cs(["wiredTiger", "cache", "page split during eviction deepened the tree"], rate=True)
cs(["wiredTiger", "cache", "pages written from cache"], rate=True)
cs(["wiredTiger", "cache", "unmodified pages evicted"], rate=True)
cs(["wiredTiger", "compression", "compressed pages read"], rate=True)
cs(["wiredTiger", "compression", "compressed pages written"], rate=True)
cs(["wiredTiger", "compression", "page written failed to compress"], rate=True)
cs(["wiredTiger", "compression", "page written was too small to compress"], rate=True)
cs(["wiredTiger", "compression", "raw compression call failed, additional data available"], rate=True)
cs(["wiredTiger", "compression", "raw compression call failed, no additional data available"], rate=True)
cs(["wiredTiger", "compression", "raw compression call succeeded"], rate=True)
cs(["wiredTiger", "creationString"], level=99)
cs(["wiredTiger", "cursor", "bulk-loaded cursor-insert calls"], rate=True)
cs(["wiredTiger", "cursor", "create calls"], rate=True)
cs(["wiredTiger", "cursor", "cursor-insert key and value bytes inserted"], rate=True)
cs(["wiredTiger", "cursor", "cursor-remove key bytes removed"], rate=True)
cs(["wiredTiger", "cursor", "cursor-update value bytes updated"], rate=True)
cs(["wiredTiger", "cursor", "insert calls"], rate=True)
cs(["wiredTiger", "cursor", "next calls"], rate=True)
cs(["wiredTiger", "cursor", "prev calls"], rate=True)
cs(["wiredTiger", "cursor", "remove calls"], rate=True)
cs(["wiredTiger", "cursor", "reset calls"], rate=True)
cs(["wiredTiger", "cursor", "search calls"], rate=True)
cs(["wiredTiger", "cursor", "search near calls"], rate=True)
cs(["wiredTiger", "cursor", "update calls"], rate=True)
cs(["wiredTiger", "metadata", "formatVersion"], level=99)
cs(["wiredTiger", "metadata", "oplogKeyExtractionVersion"], level=99)
cs(["wiredTiger", "reconciliation", "dictionary matches"], rate=True)
cs(["wiredTiger", "reconciliation", "internal page key bytes discarded using suffix compression"], rate=True)
cs(["wiredTiger", "reconciliation", "internal page multi-block writes"], rate=True)
cs(["wiredTiger", "reconciliation", "internal-page overflow keys"])
cs(["wiredTiger", "reconciliation", "leaf page key bytes discarded using prefix compression"], rate=True)
cs(["wiredTiger", "reconciliation", "leaf page multi-block writes"], rate=True)
cs(["wiredTiger", "reconciliation", "leaf-page overflow keys"])
cs(["wiredTiger", "reconciliation", "maximum blocks required for a page"])
cs(["wiredTiger", "reconciliation", "overflow values written"], rate=True)
cs(["wiredTiger", "reconciliation", "page checksum matches"], rate=True)
cs(["wiredTiger", "reconciliation", "page reconciliation calls"], rate=True)
cs(["wiredTiger", "reconciliation", "page reconciliation calls for eviction"], rate=True)
cs(["wiredTiger", "reconciliation", "pages deleted"], rate=True)
cs(["wiredTiger", "session", "object compaction"])
cs(["wiredTiger", "session", "open cursor count"])
cs(["wiredTiger", "transaction", "update conflicts"], rate=True)
cs(["wiredTiger", "type"], level=99)
cs(["wiredTiger", "uri"], level=99)
cs(["errmsg"], level=99)

#
# ftdc repl set stuff
#

def rs(name, **kwargs):

    descriptor(
        file_type = 'metrics',
        parser = process.parse_ftdc,
        name = 'ftdc rs: member {member} ' + name,
        split_on_key_match = util.join('replSetGetStatus', 'members', '(?P<member>[0-9])+', name),
        time_key = 'replSetGetStatus/start',
        time_scale = 1000.0,
        **kwargs
    )

def compute_lag(metrics):

    # only do this once per chunk
    if hasattr(metrics, 'has_lag'):
        return
    metrics.has_lag = True
    
    # compute list of members
    members = set()
    for key in metrics:
        m  = re.match(util.join('replSetGetStatus', 'members', '([0-9])+'), key)
        if m:
            member = m.group(1)
            members.add(member)
            metrics[util.join('replSetGetStatus', 'members', member, 'lag')] = []
    members = list(sorted(members))
            
    # xxx pretty inefficient to be doing this every time, consider lifting out of loop below
    # but otoh we don't do this very often, only once per chunk, and timing shows little or no diff
    def get(member, key):
        return metrics[util.join('replSetGetStatus', 'members', member, key)]

    # no repl set status in this chunk?
    if not members:
        return

    # compute lag
    for i in range(len(get(members[0], 'state'))):
        pri_optimeDate = None
        for member in members:
            if get(member, 'state')[i]==1:
                pri_optimeDate = get(member, 'optimeDate')[i]
        for member in members:
            lag = None
            if pri_optimeDate:
                try:
                    sec_optimeDate = get(member, 'optimeDate')[i]
                    if sec_optimeDate:
                        lag = (pri_optimeDate - sec_optimeDate) / 1000.0
                except KeyError:
                    pass
            get(member, 'lag').append(lag)

            
rs('state', level=1)
rs('health', level=1)
rs('uptime', level=3)
rs('lag', level=1, special=compute_lag)


#
# sysmon.py
#

def sysmon_cpu(which, **kwargs):
    descriptor(
        name = 'sysmon cpu: %s (%%)' % which,
        file_type = 'text',
        parser = process.parse_csv,
        time_key = 'time',
        data_key = 'cpu_%s' % which,
        scale_field = 'cpus',
        ymax = 100,
        rate = True,
        **kwargs
    )
    
sysmon_cpu('user', merge = 'sysmon_cpu')
sysmon_cpu('system', merge = 'sysmon_cpu')
sysmon_cpu('iowait', merge = 'sysmon_cpu')
sysmon_cpu('nice', merge = 'sysmon_cpu')
sysmon_cpu('steal', merge = 'sysmon_cpu')

sysmon_cpu('idle', level = 3)
sysmon_cpu('irq', level = 3)
sysmon_cpu('softirq', level = 3)
sysmon_cpu('guest', level = 3)
sysmon_cpu('guest_nice', level = 3)

# xxx use catch-all w/ split instead of listing explicitly?
# xxx or at least csv should produce message on unrecognized field?

def stat(which, name=None, **kwargs):
    name = 'sysmon: %s' % (name if name else which)
    descriptor(
        name = name,
        file_type = 'text',
        parser = process.parse_csv,
        time_key = 'time',
        data_key = '%s' % which,
        **kwargs
    )

stat('ctxt', name='context switches (/s)', rate=True)
#stat('btime')
stat('processes')
stat('running')
stat('procs_blocked')

stat('memtotal', scale=1024)
stat('memfree', scale=1024)
stat('buffers', scale=1024)
stat('cached', scale=1024)
stat('swapcached', scale=1024)
stat('active', scale=1024)
stat('inactive', scale=1024)
stat('active anon', scale=1024)
stat('inactive anon', scale=1024)
stat('active file', scale=1024)
stat('inactive file', scale=1024)
stat('dirty', scale=1024)


def sysmon_disk(which, desc, **kwargs):
    if not 'rate' in kwargs: kwargs['rate'] = True
    descriptor(
        name = 'sysmon disk: {disk} %s' % desc,
        file_type = 'text',
        parser = process.parse_csv,
        time_key = 'time',
        split_on_key_match = '(?P<disk>.*)\.%s' % which,
        **kwargs
    )
    
sysmon_disk('reads_merged',   'read requests merged (/s)',  merge='sysmon_disk_req_merged {disk}', ygroup='sysmon_disk_req')
sysmon_disk('writes_merged',  'write requests merged (/s)', merge='sysmon_disk_req_merged {disk}', ygroup='sysmon_disk_req')
sysmon_disk('reads',          'read requests issued (/s)',  merge='sysmon_disk_req_issued {disk}', ygroup='sysmon_disk_req')
sysmon_disk('writes',         'write requests issued (/s)', merge='sysmon_disk_req_issued {disk}', ygroup='sysmon_disk_req')
sysmon_disk('read_sectors',   'bytes read (MB/s)',          merge='sysmon_disk_MBs {disk}',        scale=1024*1024/512)
sysmon_disk('write_sectors',  'bytes written (MB/s)',       merge='sysmon_disk_MBs {disk}',        scale=1024*1024/512)
sysmon_disk('read_time_ms',   'busy reading (%)',           merge='sysmon_busy',                   scale=10, ymax=100)
sysmon_disk('write_time_ms',  'busy writing (%)',           merge='sysmon_busy',                   scale=10, ymax=100)
sysmon_disk('io_in_progress', 'in progress', rate=False)
sysmon_disk('io_time_ms',     'io_time_ms')
sysmon_disk('io_queued_ms',   'io_queued_ms')
sysmon_disk('io_queued_ms',   'average queue length', scale_field='{disk}.io_time_ms')

#
# iostat output, e.g.
# iostat -t -x $delay
#

parse_iostat = process.parse_re(
    time_key = 'time',
    regexp = process.alt(
        '(?P<time>^../../..(?:..)? ..:..:..(?: ..)?)',
        '(?:^ *(?P<user>[0-9\.]+) +(?P<nice>[0-9\.]+) +(?P<system>[0-9\.]+) +(?P<iowait>[0-9\.]+) +(?P<steal>[0-9\.]+) +(?P<idle>[0-9\.]+))',
        '(?:^(?P<iostat_disk>[a-z]+) +(?P<rrqms>[0-9\.]+) +(?P<wrqms>[0-9\.]+) +(?P<rs>[0-9\.]+) +(?P<ws>[0-9\.]+) +(?P<rkBs>[0-9\.]+) +(?P<wkBs>[0-9\.]+) +(?P<avgrqsz>[0-9\.]+) +(?P<avgqusz>[0-9\.]+) +(?P<await>[0-9\.]+) +(?P<r_await>[0-9\.]+)? +(?P<w_await>[0-9\.]+)? +(?P<svctime>[0-9\.]+) +(?P<util>[0-9\.]+))',
    )
)

def iostat(**kwargs):
    descriptor(
        file_type = 'text',
        parser = parse_iostat,
        time_key = 'time',
        **kwargs
    )

def iostat_cpu(data_key, **kwargs):
    iostat(
        data_key = data_key,
        name = 'iostat cpu: {data_key} (%)',
        ymax = 100,
        **kwargs
    )

iostat_cpu('user', merge = 'iostat_cpu')
iostat_cpu('system', merge = 'iostat_cpu')
iostat_cpu('iowait', merge = 'iostat_cpu')
iostat_cpu('nice', merge = 'iostat_cpu')
iostat_cpu('steal', merge = 'iostat_cpu')
iostat_cpu('idle', level = 3)

def iostat_disk(data_key, name, level=3, **kwargs):
    iostat(
        data_key = data_key,
        split_key = 'iostat_disk',
        name = 'iostat disk: {iostat_disk} ' + name,
        level = level,
        **kwargs
    )

iostat_disk('rrqms',   'read requests merged (/s)',  merge='iostat_disk_req_merged {iostat_disk}',  ygroup='iostat_disk_req')
iostat_disk('wrqms',   'write requests merged (/s)', merge='iostat_disk_req_merged {iostat_disk}',  ygroup='iostat_disk_req')
iostat_disk('rs',      'read requests issued (/s)',  merge='iostat_disk_req_issued {iostat_disk}',  ygroup='iostat_disk_req')
iostat_disk('ws',      'write requests issued (/s)', merge='iostat_disk_req_issued {iostat_disk}',  ygroup='iostat_disk_req')
iostat_disk('rkBs',    'bytes read (MB/s)',          merge='iostat_disk_MBs {iostat_disk}',         scale=1024, level=1)
iostat_disk('wkBs',    'bytes written (MB/s)',       merge='iostat_disk_MBs {iostat_disk}',         scale=1024, level=1)
iostat_disk('avgrqsz', 'average request size (sectors)')
iostat_disk('avgqusz', 'average queue length')
iostat_disk('await',   'average wait time (ms)')
iostat_disk('util',    'average utilization (%)', ymax=100, level=1)


#
# mongod log
#

#2014-11-28T06:04:22.610-0800 I QUERY    [conn3] command test.$cmd command: insert { $msg: "query not recording (too large)" } keyUpdates:0  reslen:40 195ms

parse_mongod = process.parse_re(
    time_key = 'time',
    regexp = process.seq(
        '^(?P<time>....-..-..T..:..:..\....(?:[+-]....|Z)) ',
        process.alt(
            '.* (?P<close>end connection)',
            '.* connection (?P<open>accepted from)',
            #'.* (?:query:|command:|getmore) .* (?P<ms>[0-9]+)ms$',
            process.seq(
                r'I (?P<cat>[A-Z]+) +\[conn[0-9]+\] ',
                process.alt(
                    process.seq(
                        r'command (?P<db>[^ ]+) ', # db
                        r'command: (?P<cmd>[^ ]+) ', # cmd
                    ),
                    process.seq(
                        r'(?P<op>[^ ]+) ', # op
                        r'(?P<ns>[^ ]+) ', # ns
                    )
                ),
                r'.* (?P<ms>[0-9]+)ms$'
            )
        )
    )
)

def mongod(**kwargs):
    kwargs['file_type'] = 'text'
    kwargs['parser'] = parse_mongod
    kwargs['time_key'] = 'time'
    descriptor(**kwargs)

mongod(
    name = 'mongod connections opened per {bucket_size}s',
    data_key = 'open',
    bucket_op = 'count',
    bucket_size = 1,    # size of buckets in seconds
    level = 1
)

mongod(
    name = 'mongod connections closed per {bucket_size}s',
    data_key = 'close',
    bucket_op = 'count',
    bucket_size = 1,    # size of buckets in seconds
    level = 1
)

def mongod_split(split_key, split_name):

    mongod(
        name = 'mongod: %s: max logged op (ms) per {bucket_size}s ' % split_name,
        data_key = 'ms',
        split_key = split_key,
        bucket_op = 'max',
        bucket_size = 1, # size of buckets in seconds
        ygroup = 'mongod_long_max',
        level = 1
    )
    
    mongod(
        name = 'mongod: %s: ops longer than {count_min}ms per {bucket_size}s ' % split_name,
        data_key = 'ms',
        split_key = split_key,
        bucket_op = 'count',
        bucket_size = 1,    # size of buckets in seconds
        count_min = 0,      # minimum query duration to count',
        ygroup = 'mongod_long_count',
        level = 1
    )

mongod_split(None, 'total')
mongod_split(('ns','op'), 'ns={ns}, op={op}')
mongod_split(('db','cmd'), 'ns={db}, cmd={cmd}')
#mongod_split(('cat','db'), '{cat} db={db}')
#mongod_split(('cat','ns'), '{cat} ns={ns}')
#mongod_split(('cat','op'), '{cat} op={op}')
#mongod_split(('cat','cmd'), '{cat} cmd={cmd}')

#cat=WRITE db=test cmd=insert


# not working right it seems?
#mongod(
#    name = 'mongod queued queries longer than {queue_min_ms}ms',
#    re = '.* query: .* ([0-9]+)ms$',
#    queue = True,
#    queue_min_ms = 0,  # minimum op duration to count for queue',
#    level = 3
#)

#mongod(
#    name = 'mongod: waiting to acquire lock per {bucket_size}s',
#    re = '.* has been waiting to acquire lock for more than (30) seconds',
#    bucket_op = 'count',
#    bucket_size = 1,  # size of buckets in seconds
#    level = 1
#)

#
# oplog, e.g.
# mongo --eval 'db.oplog.rs.find({...}, {ts:1, op:1, ns:1}).forEach(function(d) {print(JSON.stringify(d))})
#

descriptor(
    name = 'oplog: {op} {ns}',
    file_type = 'json',
    parser = process.parse_json,
    time_key = util.join('ts', 't'),
    data_key = util.join('op'),
    bucket_op = 'count',
    bucket_size = 1,
    split_key = ('op', 'ns'),
    level = 1
)


#
# wt
#

# regexp parsing for wtstats files
parse_wt_alts = process.alt()
parse_wt = process.parse_re(
    time_key = 'time',
    regexp = process.seq('^(?P<time>... .. ..:..:..) ', parse_wt_alts)
)

def wt(wt_cat, wt_name, rate=False, scale=1.0, level=3, **kwargs):

    kwargs['scale'] = scale
    kwargs['rate'] = rate
    kwargs['level'] = level

    units = desc_units(scale, rate)
    if units: units = ' (' + units + ')'
    if 'name' in kwargs:
        name = 'wt {}: {}'.format(wt_cat, kwargs['name'])
        del kwargs['name']
    else:
        name = 'wt {}: {}{}'.format(wt_cat, wt_name, units)

    # for parsing wt metrics as part of serverStatus output
    ss(['wiredTiger', wt_cat, wt_name], 'ss ' + name, **kwargs)

    # for parsing wt data in wtstats files
    # broken for now: >100 groups
    # data_key = 'key%d' % len(parse_wt_alts)
    # parse_wt_alts.append('(?P<%s>[0-9]+) .* %s: %s' % (data_key, wt_cat, wt_name))
    # descriptor(
    #     file_type = 'text',
    #     parser = parse_wt,
    #     name = name,
    #     time_key = 'time',
    #     data_key = data_key,
    #     **kwargs
    # )


ss(['wiredTiger', 'concurrentTransactions', 'read', 'available'], level=4)
ss(['wiredTiger', 'concurrentTransactions', 'read', 'out'], level=2)
ss(['wiredTiger', 'concurrentTransactions', 'read', 'totalTickets'], level=4)
ss(['wiredTiger', 'concurrentTransactions', 'write', 'available'], level=4)
ss(['wiredTiger', 'concurrentTransactions', 'write', 'out'], level=2)
ss(['wiredTiger', 'concurrentTransactions', 'write', 'totalTickets'], level=4)

wt('LSM', 'application work units currently queued')
wt('LSM', 'bloom filter false positives', rate=True)
wt('LSM', 'bloom filter hits', rate=True)
wt('LSM', 'bloom filter misses', rate=True)
wt('LSM', 'bloom filter pages evicted from cache', rate=True)
wt('LSM', 'bloom filter pages read into cache', rate=True)
wt('LSM', 'bloom filters in the LSM tree')
wt('LSM', 'chunks in the LSM tree')
wt('LSM', 'highest merge generation in the LSM tree')
wt('LSM', 'merge work units currently queued')
wt('LSM', 'queries that could have benefited from a Bloom filter that did not ex', rate=True)
wt('LSM', 'rows merged in an LSM tree', rate=True)
wt('LSM', 'sleep for LSM checkpoint throttle', rate=True)
wt('LSM', 'sleep for LSM merge throttle', rate=True)
wt('LSM', 'switch work units currently queued')
wt('LSM', 'total size of bloom filters')
wt('LSM', 'tree maintenance operations discarded', rate=True)
wt('LSM', 'tree maintenance operations executed', rate=True)
wt('LSM', 'tree maintenance operations scheduled', rate=True)
wt('LSM', 'tree queue hit maximum')
wt('async', 'current work queue length', level=2)
wt('async', 'maximum work queue length')
wt('async', 'number of allocation state races', rate=True)
wt('async', 'number of flush calls', rate=True)
wt('async', 'number of operation slots viewed for allocation', rate=True)
wt('async', 'number of times operation allocation failed', rate=True)
wt('async', 'number of times worker found no work', rate=True)
wt('async', 'total allocations', rate=True)
wt('async', 'total compact calls', rate=True)
wt('async', 'total insert calls', rate=True)
wt('async', 'total remove calls', rate=True)
wt('async', 'total search calls', rate=True)
wt('async', 'total update calls', rate=True)
wt('block-manager', 'allocations requiring file extension', rate=True)
wt('block-manager', 'blocks allocated', rate=True)
wt('block-manager', 'blocks freed', rate=True)
wt('block-manager', 'blocks pre-loaded', rate=True)
wt('block-manager', 'blocks read', merge='wt_block-manager_blocks', rate=True)
wt('block-manager', 'blocks written', merge='wt_block-manager_blocks', rate=True)
wt('block-manager', 'bytes read', merge='wt_block-manager_bytes', scale=MB, rate=True, level=2)
wt('block-manager', 'bytes written', merge='wt_block-manager_bytes', scale=MB, rate=True, level=2)
wt('block-manager', 'checkpoint size')
wt('block-manager', 'file allocation unit size')
wt('block-manager', 'file bytes available for reuse', scale=MB)
wt('block-manager', 'file magic number', level=99)
wt('block-manager', 'file major version number', level=99)
wt('block-manager', 'file size in bytes', scale=MB)
wt('block-manager', 'mapped blocks read', rate=True)
wt('block-manager', 'mapped bytes read', rate=True, scale=MB)
wt('block-manager', 'minor version number', level=99)
wt('btree', 'column-store fixed-size leaf pages')
wt('btree', 'column-store internal pages')
wt('btree', 'column-store variable-size deleted values')
wt('btree', 'column-store variable-size leaf pages')
wt('btree', 'cursor create calls', rate=True, level=2)
wt('btree', 'cursor insert calls', rate=True, level=2)
wt('btree', 'cursor next calls', rate=True)
wt('btree', 'cursor prev calls', rate=True)
wt('btree', 'cursor remove calls', rate=True, level=2)
wt('btree', 'cursor reset calls', rate=True)
wt('btree', 'cursor search calls', rate=True, level=2)
wt('btree', 'cursor search near calls', rate=True, level=3)
wt('btree', 'cursor update calls', rate=True, level=2)
wt('btree', 'fixed-record size')
wt('btree', 'maximum internal page item size')
wt('btree', 'maximum internal page size')
wt('btree', 'maximum leaf page item size')
wt('btree', 'maximum leaf page size')
wt('btree', 'maximum tree depth')
wt('btree', 'number of key/value pairs')
wt('btree', 'overflow pages')
wt('btree', 'pages rewritten by compaction', rate=True)
wt('btree', 'row-store internal pages')
wt('btree', 'row-store leaf pages')
wt('cache', 'bytes currently in the cache', scale=MB, level=2)
wt('cache', 'bytes read into cache', merge='wt_cache_bytes_cache', scale=MB, rate=True, level=2)
wt('cache', 'bytes written from cache', merge='wt_cache_bytes_cache', scale=MB, rate=True, level=2)
wt('cache', 'checkpoint blocked page eviction', rate=True)
wt('cache', 'data source pages selected for eviction unable to be evicted')
wt('cache', 'eviction server candidate queue empty when topping up', rate=True)
wt('cache', 'eviction server candidate queue not empty when topping up', rate=True)
wt('cache', 'eviction server evicting pages', rate=True, level=2)
wt('cache', 'eviction server populating queue, but not evicting pages', rate=True)
wt('cache', 'eviction server unable to reach eviction goal', rate='delta')
wt('cache', 'eviction worker thread evicting pages', rate=True)
wt('cache', 'failed eviction of pages that exceeded the in-memory maximum', rate=True)
wt('cache', 'hazard pointer blocked page eviction', rate=True)
wt('cache', 'in-memory page passed criteria to be split', rate=True)
wt('cache', 'in-memory page splits', rate=True) # CHECK
wt('cache', 'internal pages evicted', rate=True)
wt('cache', 'lookaside table insert calls', rate=True)
wt('cache', 'lookaside table remove calls', rate=True)
wt('cache', 'maximum bytes configured', scale=MB)
wt('cache', 'maximum page size at eviction', scale=MB) # CHECK rc5
wt('cache', 'modified pages evicted', rate=True)
wt('cache', 'overflow pages read into cache', rate=True)
wt('cache', 'overflow values cached in memory')
wt('cache', 'page split during eviction deepened the tree', rate=True)
wt('cache', 'page written requiring lookaside records', rate=True)
wt('cache', 'pages currently held in the cache')
wt('cache', 'pages evicted because they exceeded the in-memory maximum', rate=True)
wt('cache', 'pages evicted because they had chains of deleted items', rate=True) # CHECK rc5
wt('cache', 'pages evicted by application threads', rate=True) # CHECK
wt('cache', 'pages read into cache requiring lookaside entries', rate=True)
wt('cache', 'pages read into cache', merge = 'wt_cache_pages_cache', rate=True)
wt('cache', 'pages selected for eviction unable to be evicted', rate=True)
wt('cache', 'pages split during eviction', rate=True)
wt('cache', 'pages walked for eviction', rate=True)
wt('cache', 'pages written from cache', merge = 'wt_cache_pages_cache', rate=True)
wt('cache', 'pages written requiring in-memory restoration', rate=True)
wt('cache', 'percentage overhead')
wt('cache', 'tracked bytes belonging to internal pages in the cache', scale=MB)
wt('cache', 'tracked bytes belonging to leaf pages in the cache', scale=MB)
wt('cache', 'tracked bytes belonging to overflow pages in the cache', scale=MB)
wt('cache', 'tracked dirty bytes in the cache', scale=MB)
wt('cache', 'tracked dirty pages in the cache')
wt('cache', 'unmodified pages evicted', rate=True)
wt('compression', 'compressed pages read', merge = 'wt_compression_compressed_pages', rate=True)
wt('compression', 'compressed pages written', merge = 'wt_compression_compressed_pages', rate=True)
wt('compression', 'page written failed to compress', rate=True)
wt('compression', 'page written was too small to compress', rate=True)
wt('compression', 'raw compression call failed, additional data available', rate=True)
wt('compression', 'raw compression call failed, no additional data available', rate=True)
wt('compression', 'raw compression call succeeded', rate=True)
wt('connection', 'files currently open')
wt('connection', 'memory allocations', rate=True)
wt('connection', 'memory frees', rate=True)
wt('connection', 'memory re-allocations', rate=True)
wt('connection', 'pthread mutex condition wait calls', rate=True)
wt('connection', 'pthread mutex shared lock read-lock calls', rate=True)
wt('connection', 'pthread mutex shared lock write-lock calls', rate=True)
wt('connection', 'total read I/Os', merge = 'wt_connection_total_I/Os', rate=True)
wt('connection', 'total write I/Os', merge = 'wt_connection_total_I/Os', rate=True)
wt('cursor', 'bulk-loaded cursor-insert calls', rate=True)
wt('cursor', 'create calls', rate=True, level=2)
wt('cursor', 'cursor create calls', rate=True, level=2)
wt('cursor', 'cursor insert calls', rate=True, level=2)
wt('cursor', 'cursor next calls', rate=True)
wt('cursor', 'cursor prev calls', rate=True)
wt('cursor', 'cursor remove calls', rate=True, level=2)
wt('cursor', 'cursor reset calls', rate=True)
wt('cursor', 'cursor restarted searches', rate=True)
wt('cursor', 'cursor search calls', rate=True, level=2)
wt('cursor', 'cursor search near calls', rate=True, level=3)
wt('cursor', 'cursor update calls', rate=True, level=2)
wt('cursor', 'cursor-insert key and value bytes inserted', scale=MB)
wt('cursor', 'cursor-remove key bytes removed', scale=MB)
wt('cursor', 'cursor-update value bytes updated', scale=MB)
wt('cursor', 'insert calls', rate=True, level=2)
wt('cursor', 'next calls', rate=True)
wt('cursor', 'prev calls', rate=True)
wt('cursor', 'remove calls', rate=True, level=2)
wt('cursor', 'reset calls', rate=True)
wt('cursor', 'search calls', rate=True, level=2)
wt('cursor', 'search near calls', rate=True, level=3)
wt('cursor', 'update calls', rate=True, level=2)
wt('data-handle', 'connection candidate referenced', rate=True) # CHECK
wt('data-handle', 'connection data handles currently active')
wt('data-handle', 'connection dhandles swept', rate=True) # CHECK
wt('data-handle', 'connection sweep candidate became referenced')
wt('data-handle', 'connection sweep dhandles closed', rate=True)
wt('data-handle', 'connection sweep dhandles removed from hash list', rate=True)
wt('data-handle', 'connection sweep time-of-death sets',rate=True)
wt('data-handle', 'connection sweeps', rate=True) # CHECK
wt('data-handle', 'connection time-of-death sets', rate=True) # CHECK
wt('data-handle', 'session dhandles swept', rate=True)
wt('data-handle', 'session sweep attempts', rate=True)
wt('log', 'busy returns attempting to switch slots', rate=True)
wt('log', 'consolidated slot closures', rate=True, set_field='slot_closure_rate')
wt('log', 'consolidated slot join races', rate=True)
wt('log', 'consolidated slot join transitions', rate=True)
wt('log', 'consolidated slot joins', rate=True)
wt('log', 'consolidated slot joins', rate=True, name='joins per closure', scale_field='slot_closure_rate')
wt('log', 'consolidated slot unbuffered writes', rate=True)
wt('log', 'failed to find a slot large enough for record', rate=True)
wt('log', 'log buffer size increases', rate=True)
wt('log', 'log bytes of payload data', scale=MB, rate=True)
wt('log', 'log bytes written', scale=MB, rate=True, level=2)
wt('log', 'log flush operations', rate=True)
wt('log', 'log read operations', rate=True)
wt('log', 'log records compressed', rate=True) # CHECK
wt('log', 'log records not compressed', rate=True) # CHECK
wt('log', 'log records too small to compress', rate=True) # CHECK
wt('log', 'log release advances write LSN', rate=True)
wt('log', 'log scan operations', rate=True)
wt('log', 'log scan records requiring two reads', rate=True)
wt('log', 'log server thread advances write LSN', rate=True)
wt('log', 'log sync operations', rate=True)
wt('log', 'log sync_dir operations', rate=True)
wt('log', 'log write operations', rate=True)
wt('log', 'logging bytes consolidated', scale=MB, rate=True)
wt('log', 'maximum log file size', scale=MB)
wt('log', 'number of pre-allocated log files to create') # CHECK
wt('log', 'pre-allocated log files not ready and missed', rate=True)
wt('log', 'pre-allocated log files prepared', rate=True) # CHECK
wt('log', 'pre-allocated log files used', rate=True) # CHECK
wt('log', 'record size exceeded maximum', rate=True)
wt('log', 'records processed by log scan', rate=True)
wt('log', 'slots selected for switching that were unavailable', rate=True)
wt('log', 'total in-memory size of compressed records', scale=MB) # CHECK
wt('log', 'total log buffer size', scale=MB)
wt('log', 'total size of compressed records', scale=MB) # CHECK
wt('log', 'written slots coalesced', rate=True)
wt('log', 'yields waiting for previous log file close', rate=True)
wt('reconciliation', 'dictionary matches', rate=True)
wt('reconciliation', 'internal page key bytes discarded using suffix compression', scale=MB)
wt('reconciliation', 'internal page multi-block writes', rate=True)
wt('reconciliation', 'internal-page overflow keys', rate=True)
wt('reconciliation', 'leaf page key bytes discarded using prefix compression', scale=MB)
wt('reconciliation', 'leaf page multi-block writes', rate=True)
wt('reconciliation', 'leaf-page overflow keys', rate=True)
wt('reconciliation', 'maximum blocks required for a page')
wt('reconciliation', 'overflow values written', rate=True)
wt('reconciliation', 'page checksum matches', rate=True)
wt('reconciliation', 'page reconciliation calls for eviction', rate=True, level=3)
wt('reconciliation', 'page reconciliation calls', rate=True, level=2)
wt('reconciliation', 'pages deleted', rate=True)
wt('reconciliation', 'split bytes currently awaiting free', scale=MB)
wt('reconciliation', 'split objects currently awaiting free')
wt('session', 'object compaction')
wt('session', 'open cursor count')
wt('session', 'open session count')
wt('thread-yield', 'page acquire busy blocked', rate=True) # CHECK
wt('thread-yield', 'page acquire eviction blocked', rate=True) # CHECK
wt('thread-yield', 'page acquire locked blocked', rate=True) # CHECK
wt('thread-yield', 'page acquire read blocked', rate=True) # CHECK
wt('thread-yield', 'page acquire time sleeping (usecs)', rate=True) # CHECK
wt('transaction', 'transaction begins', rate=True, level=3)
wt('transaction', 'transaction checkpoint currently running', level=2)
wt('transaction', 'transaction checkpoint generation')
wt('transaction', 'transaction checkpoint max time (msecs)') # CHECK
wt('transaction', 'transaction checkpoint min time (msecs)') # CHECK
wt('transaction', 'transaction checkpoint most recent time (msecs)') # CHECK
wt('transaction', 'transaction checkpoint total time (msecs)') # CHECK
wt('transaction', 'transaction checkpoints', rate='delta')
wt('transaction', 'transaction failures due to cache overflow', rate=True)
wt('transaction', 'transaction range of IDs currently pinned by a checkpoint')
wt('transaction', 'transaction range of IDs currently pinned')
wt('transaction', 'transaction sync calls', rate=True)
wt('transaction', 'transactions committed', rate=True, level=2)
wt('transaction', 'transactions rolled back', rate=True, level=2)
wt('transaction', 'update conflicts', rate=True, level=2)

ss(['wiredTiger', 'uri'], level=99)

