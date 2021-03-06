import collections
import os
import re
import process

import ftdc
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

    # descriptor_ord is used for sorting series using the order they are defined
    global descriptor_ord
    desc['_ord'] = descriptor_ord

    # split_ords is used for sorting split series into the right place
    if 'split_key' in desc:
        split_key = desc['split_key']
        if not split_key in split_ords:
            split_ords[split_key] = desc['_ord']
    if 'split_on_key_match' in desc:
        split_on_key_match = desc['split_on_key_match']
        if not split_on_key_match in split_ords:
            split_ords[split_on_key_match] = desc['_ord']

    # remember it
    descriptors.append(desc)
    descriptor_ord += 1

def list_descriptors():
    for desc in sorted(descriptors, key=lambda desc: desc['name'].lower()):
        d = collections.defaultdict(lambda: '...')
        d.update(desc)
        util.msg(graphing.get(d, 'name'))

#
# compare current list of wt metrics against list maintained in wt at
# https://raw.githubusercontent.com/wiredtiger/wiredtiger/develop/dist/stat_data.py
# print out additional descriptors that need to be added to this file
# this process is semi-automated: you must provide values for scale and level parameters
#

def check_wt_stat_data():

    import stat_data

    def check0(src, src_name, fun):
        actual = set(x['wt_desc'] for x in descriptors if 'wt_src' in x and x['wt_src']==src_name)
        reference = set(x.desc for x in src)
        flags = dict((x.desc, x.flags) for x in src)
        for desc in sorted(reference - actual):
            wt_cat, wt_desc = desc.split(': ', 1)
            rate = 'no_scale' not in flags[desc]
            util.msg('%s(\'%s\', \'%s\', rate=%s, scale=..., level=...)' %
                     (fun, wt_cat, wt_desc, rate))

    def check(src, src_name, fun, match):
        act = dict((x['wt_desc'],x) for x in descriptors if 'wt_src' in x and x['wt_src']==src_name)
        ref = dict((x.desc,x) for x in src)
        what = set(ref.keys()) & set(act.keys()) if match else set(ref.keys()) - set(act.keys())
        for desc in sorted(what):
            wt_cat, wt_desc = desc.split(': ', 1)
            flags = ref[desc].flags.split(',')
            ref_rate = 'no_scale' not in flags
            ref_scale = 'MB' if 'size' in flags else 1
            if match:
                act_rate = act[desc]['rate'] != False # rate=='delta' counts as a "rate"
                act_scale = act[desc]['scale']
                mismatch = ''
                if ref_rate != act_rate:
                    mismatch += ' RATE'
                if ref_scale=='MB' and not (act_scale==kB or act_scale==MB):
                    mismatch += ' SCALE'
                if mismatch:
                    util.msg('%s(\'%s\', \'%s\', rate=%s, scale=%s, level=...) # %s' %
                             (fun, wt_cat, wt_desc, ref_rate, ref_scale, mismatch))
            else:
                util.msg('%s(\'%s\', \'%s\', rate=%s, scale=%s, level=...)' %
                         (fun, wt_cat, wt_desc, ref_rate, ref_scale))

    util.msg('=== following metrics are in stat_data.py but not in descriptors.py:')
    check(stat_data.connection_stats, 'ss', 'wt', match=False) # serverStatus metrics
    check(stat_data.dsrc_stats, 'cs', 'cs_wt', match=False) # collStats metrics

    util.msg('=== following metrics in descriptors.py do not match stat_data.py')
    check(stat_data.connection_stats, 'ss', 'wt', match=True) # serverStatus metrics
    check(stat_data.dsrc_stats, 'cs', 'cs_wt', match=True) # collStats metrics


#
# generic grep descriptor
# usage: timeseries 'grep(pat=pat):fn
#     pat - re to locate data; must include one re group identifying data
#     fn - file to be searched
# this descriptor supplies a generic re to identify a timestamp
# assumes the timestamp precedes the data
#

#descriptor(
#    name = 'grep {pat}',
#    re = '^.*(....-..-..T..:..:..(?:\....)?Z?|(?:... )?... .. .... ..:..:..).*{pat}',
#    file_type = 'text',
#    parser = 're'
#)


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

descriptor(
    name = 'win {fn}: {key}',
    file_type = 'text',
    parser = process.parse_win_csv,
    time_key = 'time',
    split_on_key_match = '(?P<key>.*)',
)

#
# show sample rate so we know when samples are missed
#

descriptor(
    file_type = 'ftdc',
    parser = process.parse_ftdc,
    name = 'ftdc samples/s',
    data_key = 'sample_number',
    time_key = 'start',
    rate = True,
    level = 2,
    time_scale = 1000.0, # times are in ms
)

#
# generic support for computed metrics via the "special" mechanism
# these routines are called once per chunk in process.process
# each specifies a result key, a function, and a list of arg keys
# the function is called on each data point in the arg keys to produce a list of result data points
#

class metrics_special:
    def __init__(self, result, fun, *args):
        self.result = result
        self.fun = fun
        self.args = args
    def __call__(self, metrics):
        try:
            if not self.result in metrics:
                metrics[self.result] = map(self.fun, *(metrics[arg] for arg in self.args))
        except KeyError:
            # missing required args, so do nothing
            pass

compute_tcmalloc_allocated_minus_wt_cache = metrics_special(
    ['tcmalloc', 'tcmalloc', 'allocated minus wt cache'],
    lambda allocated, cache: allocated - cache,
    ['tcmalloc', 'generic', 'current_allocated_bytes'],
    ['wiredTiger', 'cache', 'bytes currently in the cache'],
)

compute_tcmalloc_total_free = metrics_special(
    ['tcmalloc', 'tcmalloc', 'total free'],
    lambda pageheap, central: pageheap + central,
    ['tcmalloc', 'tcmalloc', 'pageheap_free_bytes'],
    ['tcmalloc', 'tcmalloc', 'central_cache_free_bytes'],
)

compute_tcmalloc_utilization = metrics_special(
    ['tcmalloc', 'generic', 'heap utilization (current_allocated_bytes / heap_size)'],
    lambda allocated_bytes, heap_size: float(allocated_bytes) / float(heap_size),
    ['tcmalloc', 'generic', 'current_allocated_bytes'],
    ['tcmalloc', 'generic', 'heap_size'],
)

# XXX not right - need to differentiate first
#compute_compression_ratio = metrics_special(
#    ['wiredTiger', 'block-manager', 'compression ratio'],
#    lambda block, cache: cache / block if block and cache else None,
#    ['wiredTiger', 'block-manager', 'bytes written'],
#    ['wiredTiger', 'cache', 'bytes written from cache'],
#)

#
# serverStatus json output, for example:
# mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep($delay*1000)}"
#

MB = 1024*1024
kB = 1024

def desc_units(scale, rate):
    units = ''
    if scale==MB: units = 'MB'
    elif scale==kB: units = 'kB'
    if rate=='delta': units += 'delta'
    elif rate: units += '/s'
    return units

def ss(json_data, name=None, scale=1, rate=False, units=None, level=3, special=None, split_on_key_match=None, **kwargs):

    if not name:
        name = ' '.join(s for s in json_data[1:] if s!='floatApprox')
        name = 'ss ' + json_data[0] +  ': ' + name
        if rate=='increase':
            name += ' increase'
        elif rate=='decrease':
            name += ' decrease'
        if not units: units = desc_units(scale, rate)
        if units: units = ' (' + units + ')'
        name = name + units

    # special must specify result and args as a key string (e.g. serverStatus/tcmalloc/...)
    # but we supply it to the ss routine as a path list (e.g. ['tcmalloc', ...])
    # here we join the list, optionally prepending a wrapper (ie 'serverStatus')
    # depending on context, ie whether this ss data is wrapped in a 'serverStatus' section for ftdc
    def join_special(pfx, special):
        if special:
            special = metrics_special(
                util.join(*(pfx + special.result)),
                special.fun,
                *(util.join(*(pfx + arg)) for arg in special.args)
            )
        return special
        
    # add a prefix if needed
    def join_if(pfx, other):
        return util.join(*(pfx + other)) if other else None

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
        special = join_special([], special),
        split_on_key_match = join_if([], split_on_key_match),
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
        special = join_special(['serverStatus'], special),
        split_on_key_match = join_if(['serverStatus'], split_on_key_match),
        **kwargs
    )

    # for parsing serverStatus section of ftdc represented as metrics dictionaries
    descriptor(
        file_type = 'ftdc',
        parser = process.parse_ftdc,
        name = 'ftdc ' + name,
        data_key = util.join('serverStatus', *json_data),
        time_key = util.join('serverStatus', 'localTime'),
        scale = scale,
        rate = rate,
        level = level,
        time_scale = 1000.0, # times are in ms
        special = join_special(['serverStatus'], special),
        split_on_key_match = join_if(['serverStatus'], split_on_key_match),
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
    name = 'ss global: active readers',
    merge = '_ss_active_queue',
    level = 1
)

ss(
    json_data = ['globalLock', 'activeClients', 'writers'],
    name = 'ss global: active writers',
    merge = '_ss_active_queue',
    level = 1
)

ss(
    json_data = ['globalLock', 'currentQueue', 'readers'],
    name = 'ss global: queued readers',
    merge = '_ss_queue',
    level = 1
)

ss(
    json_data = ['globalLock', 'currentQueue', 'writers'],
    name = 'ss global: queued writers',
    merge = '_ss_queue',
    level = 1
)

ss(['globalLock', 'activeClients', 'total'], level=99)
ss(['globalLock', 'currentQueue', 'total'], level=99)
ss(['globalLock', 'totalTime'], level=99)

ss(['asserts', 'msg'], rate=True, level=1)
ss(['asserts', 'regular'], rate=True, level=1)
ss(['asserts', 'rollovers'], rate=True, level=1)
ss(['asserts', 'user'], rate=True, level=1)
ss(['asserts', 'warning'], rate=True, level=1)
ss(['backgroundFlushing', 'average_ms'], level=9)
ss(['backgroundFlushing', 'flushes'], level=9)
ss(['backgroundFlushing', 'last_finished'], level=9)
ss(['backgroundFlushing', 'last_ms'], level=9)
ss(['backgroundFlushing', 'total_ms'], level=9)
ss(['connections', 'available'], level=9)
ss(['connections', 'current'], level=1)
ss(['connections', 'totalCreated'], name='ss connections: created (/s)', level=3, rate=True)
ss(['cursors', 'clientCursors_size'], level=9)
ss(['cursors', 'note'], level=99)
ss(['cursors', 'pinned'], level=9)
ss(['cursors', 'timedOut'], level=9)
ss(['cursors', 'totalNoTimeout'], level=9)
ss(['cursors', 'totalOpen'], level=9)
ss(['dur', 'commits'], rate=True) # CHECK rc5
ss(['dur', 'commitsInWriteLock'], rate=True) # CHECK rc5
ss(['dur', 'compression']) # CHECK rc5
ss(['dur', 'earlyCommits'], rate=True) # CHECK rc5
ss(['dur', 'journaledMB'], rate=True) # CHECK rc5
ss(['dur', 'timeMs', 'commitsInWriteLockMicros'], rate=True) # CHECK rc5
ss(['dur', 'timeMs', 'dt']) # CHECK rc5
ss(['dur', 'timeMs', 'prepLogBuffer']) # CHECK rc5
ss(['dur', 'timeMs', 'remapPrivateView']) # CHECK rc5
ss(['dur', 'timeMs', 'writeToDataFiles']) # CHECK rc5
ss(['dur', 'timeMs', 'writeToJournal']) # CHECK rc5
ss(['dur', 'writeToDataFilesMB'], rate=True) # CHECK rc5
ss(['extra_info', 'heap_usage_bytes'], scale=MB, wrap=2.0**31, level=99)
ss(['extra_info', 'note'], level=99)
ss(['extra_info', 'page_faults'], rate=True, level=1)
ss(['extra_info', 'availPageFileMB'], units='MB', level=1)
ss(['extra_info', 'ramMB'], units='MB', level=1)
ss(['extra_info', 'totalPageFileMB'], units='MB', level=1)
ss(['extra_info', 'usagePageFileMB'], units='MB', level=1)
ss(['tcmalloc', 'generic', 'current_allocated_bytes'], scale=MB, level=1)
ss(['tcmalloc', 'generic', 'heap_size'], scale=MB, level=1)
ss(['tcmalloc', 'generic', 'heap utilization (current_allocated_bytes / heap_size)'], level=4,
   special=compute_tcmalloc_utilization)
ss(['tcmalloc', 'tcmalloc', 'pageheap_free_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'pageheap_unmapped_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'max_total_thread_cache_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'current_total_thread_cache_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'central_cache_free_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'transfer_cache_free_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'thread_cache_free_bytes'], scale=MB, level=4)
ss(['tcmalloc', 'tcmalloc', 'aggressive_memory_decommit'], scale=MB, level=4) # ???
ss(['tcmalloc', 'tcmalloc', 'allocated minus wt cache'], scale=MB, level=4,
   special=compute_tcmalloc_allocated_minus_wt_cache)
#ss(['tcmalloc', 'tcmalloc', 'allocated minus wt cache'], scale=MB, level=9, rate='increase',
#   special=compute_tcmalloc_allocated_minus_wt_cache)
#ss(['tcmalloc', 'tcmalloc', 'allocated minus wt cache'], scale=MB, level=9, rate='decrease',
#   special=compute_tcmalloc_allocated_minus_wt_cache)
ss(['tcmalloc', 'tcmalloc', 'total free'], scale=MB, level=4,
   special=compute_tcmalloc_total_free)

# tcmalloc per size-class statistics
def tcmalloc_size_class_metric(metric_name, **kwargs):
    data_key = ['tcmalloc', 'tcmalloc', 'size_classes']
    sokm = ['tcmalloc', 'tcmalloc', 'size_classes', '(?P<size_class>[0-9]+)', metric_name]
    name = 'ss tcmalloc: size_class {size_class} ' + metric_name
    if 'scale' in kwargs and kwargs['scale']==MB:
        name += ' (MB)'
    ss(data_key, name=name, split_on_key_match=sokm, level=4, **kwargs)
tcmalloc_size_class_metric('free_bytes', scale=MB, ygroup='tcmalloc_size_class_bytes')
tcmalloc_size_class_metric('allocated_bytes', scale=MB, ygroup='tcmalloc_size_class_bytes')

def tcmalloc_site_metric(metric_name, **kwargs):
    data_key = ['tcmalloc', 'tcmalloc', 'size_classes']
    sokm = ['tcmalloc', 'tcmalloc', 'size_classes', '(?P<size_class>[0-9]+)',
            'sites', '(?P<site>.*)', metric_name]
    name = 'ss tcmalloc: size_class {size_class} site {site} ' + metric_name
    if 'scale' in kwargs and kwargs['scale']==MB:
        name += ' (MB)'
    ss(data_key, name=name, split_on_key_match=sokm, level=4, **kwargs)
tcmalloc_site_metric('allocated_bytes', scale=MB, ygroup='tcmalloc_size_class_bytes')
tcmalloc_site_metric('heap_bytes', scale=MB, ygroup='tcmalloc_size_class_bytes')

# built-in heap profiler
ss(
    ['heapProfile', 'stacks', 'stack186', 'activeBytes'],
    split_on_key_match = ['heapProfile', 'stacks', '(?P<stack>stack[0-9]+)', 'activeBytes'],
    name = 'ss heap profile: {stack} active bytes (MB)',
    ygroup='heap_profile_active_bytes', level=4, scale=MB
)

ss(['host'], level=99)

def ss_lock(name):
    for a in ['acquireCount', 'acquireWaitCount', 'deadlockCount', 'timeAcquiringMicros']:
        for b in ['r', 'w', 'R', 'W']:
            ss(['locks', name, a, b], rate=True, level=9)

ss_lock('Collection') # CHECK rc5
ss_lock('Database') # CHECK rc5
ss_lock('Global') # CHECK rc5
ss_lock('MMAPV1Journal') # CHECK rc5
ss_lock('Metadata') # CHECK rc5
ss_lock('oplog') # CHECK rc5

ss(['mem', 'bits'], level=99)
ss(['mem', 'mapped'], scale=MB)
ss(['mem', 'mappedWithJournal'], scale=MB)
ss(['mem', 'resident'], units='MB')
ss(['mem', 'supported'], level=99)
ss(['mem', 'virtual'], units='MB', level=1)

# don't know what this is
ss(['metrics', 'commands', '<UNKNOWN>'], rate=True, level=4)

# XXX make these auto-split instead of listing explicitly
def ss_command(command, level=4):
    ss(['metrics', 'commands', command, 'total'], rate=True, level=level)
    ss(['metrics', 'commands', command, 'failed'], rate=True, level=level)

ss_command('collStats')
ss_command('count')
ss_command('createIndexes')
ss_command('currentOp')
ss_command('drop')
ss_command('fsyncUnlock')
ss_command('getMore')
ss_command('getnonce')
ss_command('insert')
ss_command('isMaster')
ss_command('killCursors')
ss_command('killOp')
ss_command('ping')
ss_command('replSetDeclareElectionWinner')
ss_command('replSetRequestVotes')
ss_command('serverStatus')
ss_command('update')
ss_command('whatsmyuri')
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
ss_command(util.join('mapreduce', 'shardedfinish'))
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


ss(['metrics', 'cursor', 'open', 'noTimeout'])
ss(['metrics', 'cursor', 'open', 'pinned'])
ss(['metrics', 'cursor', 'open', 'total'])
ss(['metrics', 'cursor', 'timedOut'], rate=True)
ss(['metrics', 'document', 'deleted'], rate=True)
ss(['metrics', 'document', 'inserted'], rate=True)
ss(['metrics', 'document', 'returned'], rate=True)
ss(['metrics', 'document', 'updated'], rate=True)
ss(['metrics', 'getLastError', 'wtime', 'num'], rate=True)
ss(['metrics', 'getLastError', 'wtime', 'totalMillis'], rate=True)
ss(['metrics', 'getLastError', 'wtimeouts'], rate=True)
ss(['metrics', 'operation', 'fastmod'], rate=True)
ss(['metrics', 'operation', 'idhack'], rate=True)
ss(['metrics', 'operation', 'scanAndOrder'], rate=True)
ss(['metrics', 'operation', 'writeConflicts'], rate=True) # CHECK
ss(['metrics', 'queryExecutor', 'scanned'], rate=True)
ss(['metrics', 'queryExecutor', 'scannedObjects'], rate=True)
ss(['metrics', 'record', 'moves'], rate=True)
ss(['metrics', 'repl', 'apply', 'batches', 'num'], rate=True)
ss(['metrics', 'repl', 'apply', 'batches', 'totalMillis'], rate=True)
ss(['metrics', 'repl', 'apply', 'ops'], rate=True)
ss(['metrics', 'repl', 'buffer', 'count'])
ss(['metrics', 'repl', 'buffer', 'maxSizeBytes'], scale=MB, level=4)
ss(['metrics', 'repl', 'buffer', 'sizeBytes'], scale=MB)
ss(['metrics', 'repl', 'executor', 'counters', 'cancels'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'eventCreated'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'eventWait'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'scheduledDBWork'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'scheduledNetCmd'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'scheduledWork'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'scheduledWorkAt'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'scheduledXclWork'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'schedulingFailures'], rate=True)
ss(['metrics', 'repl', 'executor', 'counters', 'waits'], rate=True)
ss(['metrics', 'repl', 'executor', 'eventWaiters'])
ss(['metrics', 'repl', 'executor', 'queues', 'dbWorkInProgress'])
ss(['metrics', 'repl', 'executor', 'queues', 'exclusiveInProgress'])
ss(['metrics', 'repl', 'executor', 'queues', 'free'])
ss(['metrics', 'repl', 'executor', 'queues', 'networkInProgress'])
ss(['metrics', 'repl', 'executor', 'queues', 'ready'])
ss(['metrics', 'repl', 'executor', 'queues', 'sleepers'])
ss(['metrics', 'repl', 'executor', 'shuttingDown'])
ss(['metrics', 'repl', 'executor', 'unsignaledEvents'])
ss(['metrics', 'repl', 'network', 'bytes'], rate=True, scale=MB)
ss(['metrics', 'repl', 'network', 'getmores', 'num'], rate=True)
ss(['metrics', 'repl', 'network', 'getmores', 'totalMillis'], rate=True)
ss(['metrics', 'repl', 'network', 'ops'], rate=True)
ss(['metrics', 'repl', 'network', 'readersCreated'], rate=True)
ss(['metrics', 'repl', 'preload', 'docs', 'num'], rate=True)
ss(['metrics', 'repl', 'preload', 'docs', 'totalMillis'], rate=True)
ss(['metrics', 'repl', 'preload', 'indexes', 'num'], rate=True)
ss(['metrics', 'repl', 'preload', 'indexes', 'totalMillis'], rate=True)
ss(['metrics', 'storage', 'freelist', 'search', 'bucketExhausted'], rate=True)
ss(['metrics', 'storage', 'freelist', 'search', 'requests'], rate=True)
ss(['metrics', 'storage', 'freelist', 'search', 'scanned'], rate=True)
ss(['metrics', 'ttl', 'deletedDocuments'])
ss(['metrics', 'ttl', 'deletedDocuments'], rate=True)
ss(['metrics', 'ttl', 'passes'], rate=True)
ss(['network', 'bytesIn'], rate=True, scale=MB, merge='network bytes', level=1)
ss(['network', 'bytesOut'], rate=True, scale=MB, merge='network bytes', level=1)
ss(['network', 'numRequests'], rate=True)
ss(['ok'], level=99) # CHECK
ss(['pid'], level=99) # CHECK
ss(['process'], level=99) # CHECK
ss(['storageEngine'], level=99) # CHECK
ss(['uptime'], level=3)
ss(['uptimeEstimate'], level=99) # CHECK
ss(['uptimeMillis'], level=99) # CHECK
ss(['version'], level=99) # CHECK
ss(['writeBacksQueued'], level=9) # CHECK


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
        file_type = 'ftdc',
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



cs(['capped'], level=99)
cs(['count'], level=1)
cs(['nindexes'], level=9)
cs(['ns'], level=99)
cs(['ok'], level=99)
cs(['size'], scale=MB, level=1)
cs(['maxSize'], scale=MB, level=1)
cs(['storageSize'], scale=MB, level=1)
cs(['totalIndexSize'], scale=MB, level=1)
cs(['avgObjSize'], level=1)
cs(['sleepCount'], rate=True)
cs(['sleepMS'], rate=True)

def cs_wt(wt_cat, wt_name, **kwargs):
    kwargs['wt_src'] = 'cs' # for check_stat_data
    kwargs['wt_desc'] = wt_cat + ': ' + wt_name # for check_stat_data
    cs(['wiredTiger', wt_cat, wt_name], **kwargs)

cs_wt('LSM', 'bloom filter false positives', rate=True, level=99)
cs_wt('LSM', 'bloom filter hits', rate=True, level=99)
cs_wt('LSM', 'bloom filter misses', rate=True, level=99)
cs_wt('LSM', 'bloom filter pages evicted from cache', rate=True, level=99)
cs_wt('LSM', 'bloom filter pages read into cache', rate=True, level=99)
cs_wt('LSM', 'bloom filters in the LSM tree', level=99)
cs_wt('LSM', 'chunks in the LSM tree', level=99)
cs_wt('LSM', 'highest merge generation in the LSM tree', level=99)
cs_wt('LSM', 'queries that could have benefited from a Bloom filter that did not exist', rate=True, level=99)
cs_wt('LSM', 'sleep for LSM checkpoint throttle', rate=True, level=99)
cs_wt('LSM', 'sleep for LSM merge throttle', rate=True, level=99)
cs_wt('LSM', 'total size of bloom filters', scale=MB, level=99)
cs_wt('block-manager', 'allocations requiring file extension', rate=True)
cs_wt('block-manager', 'blocks allocated', rate=True)
cs_wt('block-manager', 'blocks freed', rate=True)
cs_wt('block-manager', 'checkpoint size', scale=MB)
cs_wt('block-manager', 'file allocation unit size', scale=kB, level=99)
cs_wt('block-manager', 'file bytes available for reuse', scale=MB)
cs_wt('block-manager', 'file magic number', level=99)
cs_wt('block-manager', 'file major version number', level=99)
cs_wt('block-manager', 'file size in bytes', scale=MB)
cs_wt('block-manager', 'minor version number', level=99)
cs_wt('btree', 'btree checkpoint generation')
cs_wt('btree', 'column-store fixed-size leaf pages', level=99)
cs_wt('btree', 'column-store internal pages', level=99)
cs_wt('btree', 'column-store variable-size deleted values', level=99)
cs_wt('btree', 'column-store variable-size leaf pages', level=99)
cs_wt('btree', 'column-store variable-size RLE encoded values')
cs_wt('btree', 'fixed-record size', scale=kB)
cs_wt('btree', 'maximum internal page key size', scale=kB)
cs_wt('btree', 'maximum internal page size', scale=kB)
cs_wt('btree', 'maximum leaf page key size', scale=kB)
cs_wt('btree', 'maximum leaf page size', scale=kB)
cs_wt('btree', 'maximum leaf page value size', scale=kB)
cs_wt('btree', 'maximum tree depth')
cs_wt('btree', 'number of key/value pairs')
cs_wt('btree', 'overflow pages')
cs_wt('btree', 'pages rewritten by compaction', rate=True)
cs_wt('btree', 'row-store internal pages')
cs_wt('btree', 'row-store leaf pages')
cs_wt('cache', 'bytes read into cache', rate=True, scale=MB)
cs_wt('cache', 'bytes written from cache', rate=True, scale=MB)
cs_wt('cache', 'checkpoint blocked page eviction', rate=True)
cs_wt('cache', 'data source pages selected for eviction unable to be evicted', rate=True)
cs_wt('cache', 'hazard pointer blocked page eviction', rate=True)
cs_wt('cache', 'in-memory page passed criteria to be split', rate=True)
cs_wt('cache', 'in-memory page splits', rate=True)
cs_wt('cache', 'internal pages evicted', rate=True)
cs_wt('cache', 'internal pages split during eviction', rate=True)
cs_wt('cache', 'leaf pages split during eviction', rate=True)
cs_wt('cache', 'modified pages evicted', rate=True)
cs_wt('cache', 'overflow pages read into cache', rate=True)
cs_wt('cache', 'overflow values cached in memory')
cs_wt('cache', 'page split during eviction deepened the tree', rate=True)
cs_wt('cache', 'page written requiring lookaside records', rate=True)
cs_wt('cache', 'pages read into cache requiring lookaside entries', rate=True)
cs_wt('cache', 'pages read into cache', rate=True)
cs_wt('cache', 'pages split during eviction', rate=True)
cs_wt('cache', 'pages written from cache', rate=True)
cs_wt('cache', 'unmodified pages evicted', rate=True)
cs_wt('cache', 'pages requested from the cache', rate=True)
cs_wt('cache', 'pages written requiring in-memory restoration', rate=True)
cs_wt('cursor', 'restarted searches', rate=True)
cs_wt('cursor', 'restarted searches', rate=True)
cs_wt('cursor', 'truncate calls', rate=True)
cs_wt('cursor', 'truncate calls', rate=True)
cs_wt('compression', 'compressed pages read', rate=True)
cs_wt('compression', 'compressed pages written', rate=True)
cs_wt('compression', 'page written failed to compress', rate=True)
cs_wt('compression', 'page written was too small to compress', rate=True)
cs_wt('compression', 'raw compression call failed, additional data available', rate=True)
cs_wt('compression', 'raw compression call failed, no additional data available', rate=True)
cs_wt('compression', 'raw compression call succeeded', rate=True)
#cs_wt('creationString', level=99)
cs_wt('cursor', 'bulk-loaded cursor-insert calls', rate=True)
cs_wt('cursor', 'create calls', rate=True)
cs_wt('cursor', 'cursor-insert key and value bytes inserted', rate=True, scale=MB)
cs_wt('cursor', 'cursor-remove key bytes removed', rate=True, scale=MB)
cs_wt('cursor', 'cursor-update value bytes updated', rate=True, scale=MB)
cs_wt('cursor', 'insert calls', rate=True)
cs_wt('cursor', 'next calls', rate=True)
cs_wt('cursor', 'prev calls', rate=True)
cs_wt('cursor', 'remove calls', rate=True)
cs_wt('cursor', 'reset calls', rate=True)
cs_wt('cursor', 'search calls', rate=True)
cs_wt('cursor', 'search near calls', rate=True)
cs_wt('cursor', 'update calls', rate=True)
cs_wt('metadata', 'formatVersion', level=99)
cs_wt('metadata', 'oplogKeyExtractionVersion', level=99)
cs_wt('reconciliation', 'dictionary matches', rate=True)
cs_wt('reconciliation', 'fast-path pages deleted', rate=True)
cs_wt('reconciliation', 'internal page key bytes discarded using suffix compression', scale=MB, rate=True)
cs_wt('reconciliation', 'internal page multi-block writes', rate=True)
cs_wt('reconciliation', 'internal-page overflow keys', rate=True)
cs_wt('reconciliation', 'leaf page key bytes discarded using prefix compression', scale=MB, rate=True)
cs_wt('reconciliation', 'leaf page multi-block writes', rate=True)
cs_wt('reconciliation', 'leaf-page overflow keys', rate=True)
cs_wt('reconciliation', 'maximum blocks required for a page')
cs_wt('reconciliation', 'overflow values written', rate=True)
cs_wt('reconciliation', 'page checksum matches', rate=True)
cs_wt('reconciliation', 'page reconciliation calls', rate=True)
cs_wt('reconciliation', 'page reconciliation calls for eviction', rate=True)
cs_wt('reconciliation', 'pages deleted', rate=True)
cs_wt('session', 'object compaction', rate=True)
cs_wt('session', 'open cursor count')
cs_wt('transaction', 'update conflicts', rate=True)
#cs_wt('type', level=99)
#cs_wt('uri', level=99)

cs(['errmsg'], level=99)

#
# ftdc repl set stuff
#

def rs(name, **kwargs):

    descriptor(
        file_type = 'ftdc',
        parser = process.parse_ftdc,
        name = 'ftdc rs: member {member} ' + name,
        split_on_key_match = util.join('replSetGetStatus', 'members', '(?P<member>[0-9])+', name),
        time_key = util.join('replSetGetStatus', 'start'),
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
        '(?:^(?P<iostat_disk>[-a-z0-9]+) +(?P<rrqms>[0-9\.]+) +(?P<wrqms>[0-9\.]+) +(?P<rs>[0-9\.]+) +(?P<ws>[0-9\.]+) +(?P<rkBs>[0-9\.]+) +(?P<wkBs>[0-9\.]+) +(?P<avgrqsz>[0-9\.]+) +(?P<avgqusz>[0-9\.]+) +(?P<await>[0-9\.]+) +(?P<r_await>[0-9\.]+ +)?(?P<w_await>[0-9\.]+ +)?(?P<svctime>[0-9\.]+) +(?P<util>[0-9\.]+))',
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
            process.seq(
                process.alt(
                    '.* (?P<close>end connection)',
                    '.* connection (?P<open>accepted from)',
                ),
                '.*\((?P<connections>[0-9]+) connections now open\)',
            ),
            '.*(?P<send_error>SEND_ERROR)',
            '.*(?P<recv_error>RECV_ERROR)',
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
    kwargs['name'] = 'mongod: ' + kwargs['name']
    descriptor(**kwargs)

mongod(
    name = 'connections opened per {bucket_size}s',
    data_key = 'open',
    bucket_op = 'count',
    bucket_size = 1,    # size of buckets in seconds
    level = 1
)

mongod(
    name = 'connections closed per {bucket_size}s',
    data_key = 'close',
    bucket_op = 'count',
    bucket_size = 1,    # size of buckets in seconds
    level = 1
)

mongod(
    name = 'current connections',
    data_key = 'connections',
    sparse = True,
    #bucket_op = 'max',
    #bucket_size = 1,    # size of buckets in seconds
    level = 1
)

mongod(
    name = 'send errors per {bucket_size}s',
    data_key = 'send_error',
    bucket_op = 'count',
    bucket_size = 1,    # size of buckets in seconds
    level = 1
)

mongod(
    name = 'recv errors per {bucket_size}s',
    data_key = 'recv_error',
    bucket_op = 'count',
    bucket_size = 1,    # size of buckets in seconds
    level = 1
)

def mongod_split(split_key, split_name):

    mongod(
        name = '%s: max logged op (ms) per {bucket_size}s ' % split_name,
        data_key = 'ms',
        split_key = split_key,
        bucket_op = 'max',
        bucket_size = 1, # size of buckets in seconds
        ygroup = 'mongod_long_max',
        level = 1
    )
    
    mongod(
        name = '%s: ops longer than {count_min}ms per {bucket_size}s ' % split_name,
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
#    name = 'queued queries longer than {queue_min_ms}ms',
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
    kwargs['wt_src'] = 'ss' # for check_stat_data
    kwargs['wt_desc'] = wt_cat + ': ' + wt_name # for check_stat_data

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
wt('LSM', 'tree queue hit maximum', rate=True)
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
#wt('block-manager', 'compression ratio', level=9, special=compute_compression_ratio)
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
wt('cache', 'eviction calls to get a page', rate=True)
wt('cache', 'eviction calls to get a page found queue empty', rate=True)
wt('cache', 'eviction calls to get a page found queue empty after locking', rate=True)
wt('cache', 'eviction currently operating in aggressive mode', rate=False)
wt('cache', 'eviction server candidate queue empty when topping up', rate=True)
wt('cache', 'eviction server candidate queue not empty when topping up', rate=True)
wt('cache', 'eviction server evicting pages', rate=True, level=2)
wt('cache', 'eviction server populating queue, but not evicting pages', rate=True)
wt('cache', 'eviction server skipped very large page', rate=True)
wt('cache', 'eviction server slept, because we did not make progress with eviction', rate=True)
wt('cache', 'eviction server unable to reach eviction goal', rate='delta')
wt('cache', 'eviction worker thread evicting pages', rate=True)
wt('cache', 'failed eviction of pages that exceeded the in-memory maximum', rate=True)
wt('cache', 'hazard pointer blocked page eviction', rate=True)
wt('cache', 'in-memory page passed criteria to be split', rate=True)
wt('cache', 'in-memory page splits', rate=True) # CHECK
wt('cache', 'internal pages evicted', rate=True)
wt('cache', 'internal pages split during eviction', rate=True)
wt('cache', 'leaf pages split during eviction', rate=True)
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
wt('cache', 'pages requested from the cache', rate=True)
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
wt('connection', 'auto adjusting condition resets', rate=True)
wt('connection', 'auto adjusting condition wait calls', rate=True)
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
wt('cursor', 'search near calls', rate=True, level=2)
wt('cursor', 'truncate calls', rate=True, level=2)
wt('cursor', 'update calls', rate=True, level=2)
wt('data-handle', 'connection candidate referenced', rate=True) # CHECK
wt('data-handle', 'connection data handles currently active')
wt('data-handle', 'connection dhandles swept', rate=True) # CHECK
wt('data-handle', 'connection sweep candidate became referenced', rate=True)
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
wt('log', 'log files manually zero-filled', rate=True)
wt('log', 'log flush operations', rate=True)
wt('log', 'log force write operations', rate=True)
wt('log', 'log force write operations skipped', rate=True)
wt('log', 'log read operations', rate=True)
wt('log', 'log records compressed', rate=True) # CHECK
wt('log', 'log records not compressed', rate=True) # CHECK
wt('log', 'log records too small to compress', rate=True) # CHECK
wt('log', 'log release advances write LSN', rate=True)
wt('log', 'log scan operations', rate=True)
wt('log', 'log scan records requiring two reads', rate=True)
wt('log', 'log server thread advances write LSN', rate=True)
wt('log', 'log server thread write LSN walk skipped', rate=True)
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
wt('log', 'total in-memory size of compressed records', scale=MB, rate=True) # CHECK
wt('log', 'total log buffer size', scale=MB)
wt('log', 'total size of compressed records', scale=MB, rate=True) # CHECK
wt('log', 'written slots coalesced', rate=True)
wt('log', 'yields waiting for previous log file close', rate=True)
wt('reconciliation', 'dictionary matches', rate=True)
wt('reconciliation', 'fast-path pages deleted', rate=True)
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
wt('transaction', 'number of named snapshots created', rate=True)
wt('transaction', 'number of named snapshots dropped', rate=True)
wt('transaction', 'transaction begins', rate=True, level=3)
wt('transaction', 'transaction checkpoint currently running', level=2)
wt('transaction', 'transaction checkpoint generation')
wt('transaction', 'transaction checkpoint max time (msecs)') # CHECK
wt('transaction', 'transaction checkpoint min time (msecs)') # CHECK
wt('transaction', 'transaction checkpoint most recent time (msecs)') # CHECK
wt('transaction', 'transaction checkpoint total time (msecs)') # CHECK
wt('transaction', 'transaction checkpoints', rate='delta')
wt('transaction', 'transaction failures due to cache overflow', rate=True)
wt('transaction', 'transaction range of IDs currently pinned')
wt('transaction', 'transaction range of IDs currently pinned by a checkpoint')
wt('transaction', 'transaction range of IDs currently pinned by named snapshots')
wt('transaction', 'transaction sync calls', rate=True)
wt('transaction', 'transactions committed', rate=True, level=2)
wt('transaction', 'transactions rolled back', rate=True, level=2)
wt('transaction', 'update conflicts', rate=True, level=2)

ss(['wiredTiger', 'uri'], level=99)

#
# automatically detect correct content type for a file
# attempts to read up to 100 lines of the file,
# then makes sure resulting chunks contain an expected key for that file type
#

sniffers = [
    ('ss', process.parse_json, util.join('localTime')),
    ('mongod', parse_mongod, util.join('time')),
    ('sysmon', process.parse_csv, util.join('cpu_user')),
    ('iostat', parse_iostat, util.join('user')),
    ('cs', process.parse_json, util.join('storageSize')),
    ('csv', process.parse_csv, 'time'),
    ('win', process.parse_win_csv, 'time')
]

def _sniff(ses, fn, want_ftdc, result):
    if want_ftdc and ftdc.is_ftdc_file_or_dir(fn):
        util.msg('detected content of', fn, 'as ftdc')
        result.append('ftdc:' + fn)
        want_ftdc = False # don't also include subdirs since ftdc recursively traverses dirs
    if os.path.isdir(fn):
        for f in sorted(os.listdir(fn)):
            if not f.startswith('.'):
                _sniff(ses, os.path.join(fn,f), want_ftdc, result)
    elif not ftdc.is_ftdc_file(fn):
        for clsname, parser, key in sniffers:
            if any(key in chunk for chunk in parser.sniff(ses, fn, 100)):
                util.msg('detected content of', fn, 'as', clsname)
                result.append(clsname + ':' + fn)
                break

def sniff(ses, *fns):
    result = []
    for fn in fns:
        if ':' in fn:
            result.append(fn) # it's already a spec
        else:
            _sniff(ses, fn, True, result)
    return result

        
