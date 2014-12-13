from timeseries import format

#
# generic grep format
# usage: timeseries 'grep(pat=pat):fn
#     pat - re to locate data; must include one re group identifying data
#     fn - file to be searched
# this format supplies a generic re to identify a timestamp
# assumes the timestamp precedes the data
#

format(
    name = 'grep',
    description = '{pat}',
    re = '^.*(....-..-..T..:..:..(?:\....)?Z?|(?:... )?... .. .... ..:..:..).*{pat}',
)


#
# serverStatus json output, for example:
# mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep($delay*1000)}"
#

def ss(json_data, name=None, description=None, **kwargs):
    if not name:
        name = 'ss_' + '_'.join(json_data)
    if not description:
        description = 'ss: ' + ' '.join(json_data)
    format(
        type = 'json',
        name = name,
        description = description,
        json_data = json_data,
        json_time = ['localTime'],        
        **kwargs
    )

def ss_opcounter(opcounter, **kwargs):
    ss(
        name = 'ss_opcounters_' + opcounter,
        json_data = ['opcounters', opcounter],
        merge = 'ss_opcounters',
        description = 'ss opcounters: {} (/s)'.format(opcounter),
        delta = True,
        **kwargs
    )

ss_opcounter('insert')
ss_opcounter('update')
ss_opcounter('delete')
ss_opcounter('query')
ss_opcounter('getmore')
ss_opcounter('command')

ss(
    name = 'ss_read_queue',
    json_data = ['globalLock', 'activeClients', 'readers'],
    description = 'ss global: read queue',
    merge = '_ss_queue',
)

ss(
    name = 'ss_write queue',
    json_data = ['globalLock', 'activeClients', 'writers'],
    description = 'ss global: write queue',
    merge = '_ss_queue',
)

ss(['connections', 'current'])
ss(['globalLock', 'activeClients', 'total'])
ss(['globalLock', 'currentQueue', 'readers'])
ss(['globalLock', 'currentQueue', 'writers'])
ss(['globalLock', 'currentQueue', 'total'])
ss(['globalLock', 'totalTime', 'floatApprox'])

#
# iostat output, e.g.
# iostat -t -x $delay
#

iostat_time_re = '(?P<time>^../../.... ..:..:.. ..)'
iostat_cpu_re = '(?:^ *(?P<user>[0-9\.]+) *(?P<nice>[0-9\.]+) *(?P<system>[0-9\.]+) *(?P<iowait>[0-9\.]+) *(?P<steal>[0-9\.]+) *(?P<idle>[0-9\.]+))'
iostat_disk_re = '(?:^(?P<iostat_disk>[a-z]+) *(?P<rrqms>[0-9\.]+) *(?P<wrqms>[0-9\.]+) *(?P<rs>[0-9\.]+) *(?P<ws>[0-9\.]+) *(?P<rkBs>[0-9\.]+) *(?P<wkBs>[0-9\.]+) *(?P<avgrqsz>[0-9\.]+) *(?P<avgqusz>[0-9\.]+) *(?P<await>[0-9\.]+) *(?P<r_await>[0-9\.]+)? *(?P<w_await>[0-9\.]+)? *(?P<svctime>[0-9\.]+) *(?P<util>[0-9\.]+))'

def iostat(**kwargs):
    format(
        type = 're',
        re = '|'.join([iostat_time_re, iostat_cpu_re, iostat_disk_re]),
        re_time = 'time',
        **kwargs
    )

def iostat_cpu(re_data, **kwargs):
    iostat(
        name = 'iostat_cpu_' + re_data,
        re_data = re_data,
        description = 'iostat cpu: {re_data} (%)',
        ymax = 100,
        **kwargs
    )

iostat_cpu('user', merge = 'iostat_cpu')
iostat_cpu('system', merge = 'iostat_cpu')
iostat_cpu('iowait', merge = 'iostat_cpu')
iostat_cpu('nice', merge = 'iostat_cpu')
iostat_cpu('steal', merge = 'iostat_cpu')
iostat_cpu('idle')

def iostat_disk(re_data, description, **kwargs):
    iostat(
        name = 'iostat_disk_' + re_data,
        re_data = re_data,
        split = 'iostat_disk',
        description = 'iostat disk: {iostat_disk} ' + description,
        **kwargs
    )

iostat_disk('wrqms',   'write requests merged (/s)', merge='iostat_disk_req_merged {iostat_disk}',  ygroup='iostat_disk_req')
iostat_disk('rrqms',   'read requests merged (/s)',  merge='iostat_disk_req_merged {iostat_disk}',  ygroup='iostat_disk_req')
iostat_disk('ws',      'write requests issued (/s)', merge='iostat_disk_req_issued {iostat_disk}',  ygroup='iostat_disk_req')
iostat_disk('rs',      'read requests issued (/s)',  merge='iostat_disk_req_issued {iostat_disk}',  ygroup='iostat_disk_req')
iostat_disk('wkBs',    'bytes written (MB/s)',       merge='iostat_disk_MBs {iostat_disk}',         scale=1024)
iostat_disk('rkBs',    'bytes read (MB/s)',          merge='iostat_disk_MBs {iostat_disk}',         scale = 1024)
iostat_disk('avgrqsz', 'average request size (sectors)')
iostat_disk('avgqusz', 'average queue length')
iostat_disk('await',   'average wait time (ms)')
iostat_disk('util',    'average utilization (%)', ymax = 100)


#
# mongod log
#

def mongod(**kwargs):
    kwargs['re'] = '^(....-..-..T..:..:..\....[+-]....)' + kwargs['re']
    format(**kwargs)

mongod(
    name = 'mongod_query_ms',
    description = 'mongod max logged query (ms) per {bucket_size}s',
    re = '.* query: .* ([0-9]+)ms$',
    bucket_op = 'max',
    bucket_size = 1, # size of buckets in seconds
)

mongod(
    name = 'mongod_query_count',
    description = 'mongod logged queries longer than {count_min_ms}ms per {bucket_size}s',
    re = '.* query: .* ([0-9]+)ms$',
    bucket_op = 'count',
    bucket_size = 1,       # size of buckets in seconds
    count_min_ms = 0,      # minimum query duration to count',
)

mongod(
    name = 'mongod_query_queue',
    description = 'mongod queued queries longer than {queue_min_ms}ms',
    re = '.* query: .* ([0-9]+)ms$',
    queue = True,
    queue_min_ms = 0,  # minimum op duration to count for queue',
)

mongod(
    name = 'mongod_waiting_for_lock',
    description = 'mongod: waiting to acquire lock per {bucket_size}s',
    re = '.* has been waiting to acquire lock for more than (30) seconds',
    bucket_op = 'count',
    bucket_size = 1,  # size of buckets in seconds
)

#
# wt
#

MB = 1024*1024

def wt(wt_cat, wt_name, delta=False, scale=1.0, **kwargs):
    units = ''
    if scale==MB: units = 'MB'
    if delta: units += '/s'
    if units: units = ' (' + units + ')'
    format(
        name = 'wt_' + wt_cat + '_' + wt_name.replace(' ', '_'),
        re = '^(... .. ..:..:..) ([0-9]+) .* {}: {}'.format(wt_cat, wt_name),
        json_time = ['localTime'],
        json_data = ['wiredTiger', wt_cat, wt_name],
        scale = scale,
        delta = delta,
        description = 'wt {}: {}{}'.format(wt_cat, wt_name, units),
        **kwargs
    )

wt('async', 'maximum work queue length')
wt('async', 'number of allocation state races', delta=True)
wt('async', 'number of flush calls', delta=True)
wt('async', 'number of operation slots viewed for allocation', delta=True)
wt('async', 'number of times operation allocation failed', delta=True)
wt('async', 'number of times worker found no work', delta=True)
wt('async', 'total allocations', delta=True)
wt('async', 'total compact calls', delta=True)
wt('async', 'total insert calls', delta=True)
wt('async', 'total remove calls', delta=True)
wt('async', 'total search calls', delta=True)
wt('async', 'total update calls', delta=True)
wt('block-manager', 'allocations requiring file extension', delta=True)
wt('block-manager', 'blocks allocated', delta=True)
wt('block-manager', 'blocks freed', delta=True)
wt('block-manager', 'blocks pre-loaded', delta=True)
wt('block-manager', 'blocks written', merge='wt_block-manager_blocks', delta=True)
wt('block-manager', 'blocks read', merge='wt_block-manager_blocks', delta=True)
wt('block-manager', 'bytes written', merge='wt_block-manager_bytes', scale=MB, delta=True)
wt('block-manager', 'bytes read', merge='wt_block-manager_bytes', scale=MB, delta=True)
wt('block-manager', 'checkpoint size')
wt('block-manager', 'file allocation unit size')
wt('block-manager', 'file bytes available for reuse', scale=MB)
wt('block-manager', 'file magic number')
wt('block-manager', 'file major version number')
wt('block-manager', 'file size in bytes', scale=MB)
wt('block-manager', 'mapped blocks read', delta=True)
wt('block-manager', 'mapped bytes read', delta=True, scale=MB)
wt('block-manager', 'minor version number')
wt('btree', 'column-store fixed-size leaf pages')
wt('btree', 'column-store internal pages')
wt('btree', 'column-store variable-size deleted values')
wt('btree', 'column-store variable-size leaf pages')
wt('btree', 'cursor create calls', delta=True)
wt('btree', 'cursor insert calls', delta=True)
wt('btree', 'cursor next calls', delta=True)
wt('btree', 'cursor prev calls', delta=True)
wt('btree', 'cursor remove calls', delta=True)
wt('btree', 'cursor reset calls', delta=True)
wt('btree', 'cursor search calls', delta=True)
wt('btree', 'cursor search near calls', delta=True)
wt('btree', 'cursor update calls', delta=True)
wt('btree', 'fixed-record size')
wt('btree', 'maximum internal page item size')
wt('btree', 'maximum internal page size')
wt('btree', 'maximum leaf page item size')
wt('btree', 'maximum leaf page size')
wt('btree', 'maximum tree depth')
wt('btree', 'number of key/value pairs')
wt('btree', 'overflow pages')
wt('btree', 'pages rewritten by compaction', delta=True)
wt('btree', 'row-store internal pages')
wt('btree', 'row-store leaf pages')
wt('cache', 'bytes currently in the cache', scale=MB)
wt('cache', 'bytes written from cache', merge='wt_cache_bytes_cache', scale=MB, delta=True)
wt('cache', 'bytes read into cache', merge='wt_cache_bytes_cache', scale=MB, delta=True)
wt('cache', 'checkpoint blocked page eviction')
wt('cache', 'data source pages selected for eviction unable to be evicted')
wt('cache', 'eviction server candidate queue empty when topping up')
wt('cache', 'eviction server candidate queue not empty when topping up')
wt('cache', 'eviction server evicting pages')
wt('cache', 'eviction server populating queue, but not evicting pages')
wt('cache', 'eviction server unable to reach eviction goal')
wt('cache', 'failed eviction of pages that exceeded the in-memory maximum', delta=True)
wt('cache', 'hazard pointer blocked page eviction', delta=True)
wt('cache', 'internal pages evicted', delta=True)
wt('cache', 'maximum bytes configured', scale=MB)
wt('cache', 'modified pages evicted', delta=True)
wt('cache', 'overflow pages read into cache', delta=True)
wt('cache', 'overflow values cached in memory')
wt('cache', 'page split during eviction deepened the tree', delta=True)
wt('cache', 'pages currently held in the cache')
wt('cache', 'pages evicted because they exceeded the in-memory maximum', delta=True)
wt('cache', 'pages read into cache', merge = 'wt_cache_pages_cache', delta=True)
wt('cache', 'pages selected for eviction unable to be evicted', delta=True)
wt('cache', 'pages split during eviction', delta=True)
wt('cache', 'pages walked for eviction', delta=True)
wt('cache', 'pages written from cache', merge = 'wt_cache_pages_cache', delta=True)
wt('cache', 'tracked dirty bytes in the cache', scale=MB)
wt('cache', 'tracked dirty pages in the cache')
wt('cache', 'unmodified pages evicted', delta=True)
wt('compression', 'compressed pages written', merge = 'wt_compression_compressed_pages', delta=True)
wt('compression', 'compressed pages read', merge = 'wt_compression_compressed_pages', delta=True)
wt('compression', 'page written failed to compress', delta=True)
wt('compression', 'page written was too small to compress', delta=True)
wt('compression', 'raw compression call failed, additional data available', delta=True)
wt('compression', 'raw compression call failed, no additional data available', delta=True)
wt('compression', 'raw compression call succeeded', delta=True)
wt('connection', 'files currently open')
wt('connection', 'memory allocations', delta=True)
wt('connection', 'memory frees', delta=True)
wt('connection', 'memory re-allocations', delta=True)
wt('connection', 'pthread mutex condition wait calls', delta=True)
wt('connection', 'pthread mutex shared lock read-lock calls', delta=True)
wt('connection', 'pthread mutex shared lock write-lock calls', delta=True)
wt('connection', 'total write I/Os', merge = 'wt_connection_total_I/Os', delta=True)
wt('connection', 'total read I/Os', merge = 'wt_connection_total_I/Os', delta=True)
wt('cursor', 'bulk-loaded cursor-insert calls', delta=True)
wt('cursor', 'create calls', delta=True)
wt('cursor', 'cursor create calls', delta=True)
wt('cursor', 'cursor insert calls', delta=True)
wt('cursor', 'cursor next calls', delta=True)
wt('cursor', 'cursor prev calls', delta=True)
wt('cursor', 'cursor remove calls', delta=True)
wt('cursor', 'cursor reset calls', delta=True)
wt('cursor', 'cursor search calls', delta=True)
wt('cursor', 'cursor search near calls', delta=True)
wt('cursor', 'cursor update calls', delta=True)
wt('cursor', 'cursor-insert key and value bytes inserted', scale=MB)
wt('cursor', 'cursor-remove key bytes removed', scale=MB)
wt('cursor', 'cursor-update value bytes updated', scale=MB)
wt('cursor', 'insert calls', delta=True)
wt('cursor', 'next calls', delta=True)
wt('cursor', 'prev calls', delta=True)
wt('cursor', 'remove calls', delta=True)
wt('cursor', 'reset calls', delta=True)
wt('cursor', 'search calls', delta=True)
wt('cursor', 'search near calls', delta=True)
wt('cursor', 'update calls', delta=True)
wt('data-handle', 'session dhandles swept', delta=True)
wt('data-handle', 'session sweep attempts', delta=True)
wt('log', 'consolidated slot closures', delta=True)
wt('log', 'consolidated slot join races', delta=True)
wt('log', 'consolidated slot join transitions', delta=True)
wt('log', 'consolidated slot joins', delta=True)
wt('log', 'failed to find a slot large enough for record', delta=True)
wt('log', 'log buffer size increases', delta=True)
wt('log', 'log bytes of payload data', scale=MB, delta=True)
wt('log', 'log bytes written', scale=MB, delta=True)
wt('log', 'log read operations', delta=True)
wt('log', 'log scan operations', delta=True)
wt('log', 'log scan records requiring two reads', delta=True)
wt('log', 'log sync operations', delta=True)
wt('log', 'log write operations', delta=True)
wt('log', 'logging bytes consolidated', scale=MB)
wt('log', 'maximum log file size', scale=MB)
wt('log', 'record size exceeded maximum', delta=True)
wt('log', 'records processed by log scan', delta=True)
wt('log', 'slots selected for switching that were unavailable', delta=True)
wt('log', 'total log buffer size', scale=MB)
wt('log', 'yields waiting for previous log file close', delta=True)
wt('reconciliation', 'dictionary matches', delta=True)
wt('reconciliation', 'internal page key bytes discarded using suffix compression', scale=MB)
wt('reconciliation', 'internal page multi-block writes', delta=True)
wt('reconciliation', 'internal-page overflow keys', delta=True)
wt('reconciliation', 'leaf page key bytes discarded using prefix compression', scale=MB)
wt('reconciliation', 'leaf page multi-block writes', delta=True)
wt('reconciliation', 'leaf-page overflow keys', delta=True)
wt('reconciliation', 'maximum blocks required for a page')
wt('reconciliation', 'overflow values written', delta=True)
wt('reconciliation', 'page checksum matches', delta=True)
wt('reconciliation', 'page reconciliation calls for eviction', delta=True)
wt('reconciliation', 'page reconciliation calls', delta=True)
wt('reconciliation', 'pages deleted', delta=True)
wt('reconciliation', 'split bytes currently awaiting free', scale=MB)
wt('reconciliation', 'split objects currently awaiting free')
wt('session', 'object compaction')
wt('session', 'open cursor count')
wt('session', 'open session count')
wt('transaction', 'transaction begins', delta=True)
wt('transaction', 'transaction checkpoint currently running')
wt('transaction', 'transaction checkpoint max time .msecs.')
wt('transaction', 'transaction checkpoint min time .msecs.')
wt('transaction', 'transaction checkpoint most recent time .msecs.')
wt('transaction', 'transaction checkpoint total time .msecs.')
wt('transaction', 'transaction checkpoints', delta=True)
wt('transaction', 'transaction failures due to cache overflow', delta=True)
wt('transaction', 'transaction range of IDs currently pinned')
wt('transaction', 'transactions committed', delta=True)
wt('transaction', 'transactions rolled back', delta=True)
wt('transaction', 'update conflicts', delta=True)
wt('LSM', 'application work units currently queued')
wt('LSM', 'bloom filter false positives', delta=True)
wt('LSM', 'bloom filter hits', delta=True)
wt('LSM', 'bloom filter misses', delta=True)
wt('LSM', 'bloom filter pages evicted from cache', delta=True)
wt('LSM', 'bloom filter pages read into cache', delta=True)
wt('LSM', 'bloom filters in the LSM tree')
wt('LSM', 'chunks in the LSM tree')
wt('LSM', 'highest merge generation in the LSM tree')
wt('LSM', 'merge work units currently queued')
wt('LSM', 'queries that could have benefited from a Bloom filter that did not ex', delta=True)
wt('LSM', 'rows merged in an LSM tree', delta=True)
wt('LSM', 'sleep for LSM checkpoint throttle', delta=True)
wt('LSM', 'sleep for LSM merge throttle', delta=True)
wt('LSM', 'switch work units currently queued')
wt('LSM', 'total size of bloom filters')
wt('LSM', 'tree maintenance operations discarded', delta=True)
wt('LSM', 'tree maintenance operations executed', delta=True)
wt('LSM', 'tree maintenance operations scheduled', delta=True)
wt('LSM', 'tree queue hit maximum')
