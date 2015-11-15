import collections
import re
import traceback

import ftdc
import jsonx
import util

#
# a common internal format is used for representing parsed data
# each data source is represented as a stream of chunks, which are dictionaries where
#     the dictionary keys are data keys (e.g. "serverStatus/commands/insert")
#     each dictionary value is a list of data values (e.g. [1000, 2000, ...]
# timestamps are particular keys (e.g. "serverStatus/localTime") which are processed specially
#

#
# helper to manage accumulation of values into chunks
#

class Chunker:

    def chunk_init(self):
        self.chunk_len = 0
        self.chunk = collections.defaultdict(lambda: [None for _ in range(self.chunk_len)])
        self.last_time = None

    def chunk_extend(self):
        for l in self.chunk.values():
            l.append(None)
        self.chunk_len += 1
    
    def chunk_emit(self, flush=False):
        if flush or self.chunk_len >= 100:
            yield self.chunk
            self.chunk_init()


################################################################################
#
# each parse_*.parse() generator reads and parses files of a given type,
# yielding a sequence of chunks
#

#
# read and parse csv files
#

class ParseCsv(Chunker):

    def parse(self, ses, fn, opt):
        self.chunk_init()
        keys = None
        for line in util.file_progress(ses, fn):
            line = line.strip()
            if not keys:
                keys = line.split(',')
            else:
                self.chunk_extend()
                for k, v in zip(keys, line.split(',')):
                    self.chunk[k][-1] = v
            for chunk in self.chunk_emit():
                yield chunk
        for chunk in self.chunk_emit(True):
            yield chunk

    def info(self, ses, fn, t):
        ses.put('NOT IMPLEMENTED')

parse_csv = ParseCsv()


#
# read and parse json files
#

class parse_json:

    @staticmethod
    def parse(ses, fn, opt):
        return jsonx.read(ses, fn, opt)

    @staticmethod
    def info(ses, fn, t):
        ses.put('NOT IMPLEMENTED')


#
# read and parse ftdc metrics files
#

class parse_metrics:

    @staticmethod
    def parse(ses, fn, opt):
        return ftdc.read(ses, fn, opt)

    @staticmethod
    def info(ses, fn, t):
        def prt(*stuff):
            ses.put(' '.join(str(s) for s in stuff) + '\n')
        ftdc.info(ses, fn, t, prt)


################################################################################
#
# process() yields a generator which accepts a stream of chunks
# and computes graphs from the chunk data, under the direction of
#     series - list of graphing.Series objects each specifying a view on the data
#     opt - global options that control the generation of the graphs
# 
def process(series, opt):

    # to track metrics present in the data but not processed by any series
    unrecognized = set()

    # xxx does time parsing belong here or in the parse routines?
    pt = util.parse_time()

    # process all metrics that we are sent
    while True:

        try:

            # get our next input
            metrics = yield
                    
            def process_series(s, data_key):
                time_key = s.time_key # e.g. 'serverStatus.localTime'
                if data_key in metrics and time_key in metrics:
                    ts = metrics[time_key]
                    if type(ts[0])==str or type(ts[0])==unicode:
                        for i, t in enumerate(ts):
                            ts[i] = pt.parse_time(t, opt, series[0]) # xxx tz
                    if ts[0]/s.time_scale > opt.before or ts[-1]/s.time_scale < opt.after:
                        return
                    for i, (t, d) in enumerate(zip(ts, metrics[data_key])):
                        t = t / s.time_scale
                        if t>=opt.after and t<=opt.before:
                            get_field = lambda key: metrics[key][i]
                            if d != None:
                                s.data_point(t, d, get_field, None, opt)

            # send each series our data points
            for s in series:
                if s.special:
                    s.special(metrics)
                if s.split_on_key_match:
                    for data_key in metrics:
                        if data_key==s.time_key:
                            continue
                        m = s.split_on_key_match_re.match(data_key)
                        if m:
                            description = m.groupdict()
                            ss = s.get_split(data_key, description)
                            process_series(ss, data_key)
                else:
                    process_series(s, s.data_key)

            # track what we have used
            unrecognized.update(metrics.keys())

        except GeneratorExit:
            break

        except:
            traceback.print_exc()
            break

    # compute and print unrecognized metrics
    ignore = re.compile(
        '^serverStatus.(repl|start|end)|'
        '^local.oplog.rs|'
        '^replSetGetStatus|slot_closure_rate'
    )
    for s in series:
        unrecognized.discard(s.data_key)
        unrecognized.discard(s.time_key)
    unrecognized = filter(lambda x: not ignore.match(str(x)), unrecognized)
    is_str = lambda x: type(x)==str or type(x)==unicode
    unrecognized = filter(lambda x: x in metrics and not is_str(metrics[x][0]), unrecognized)
    if unrecognized:
        util.msg('unrecognized metrics:')
        for u in sorted(unrecognized):
            util.msg('   ', u)


#
# process a series of lines using regexps
#

class ParseRe(Chunker):

    def __init__(self, time_key, regexp):
        self.time_key = time_key
        self.regexp = regexp

    class seq(list):
        def __init__(self, *args):
            self.extend(args)
        def __str__(self):
            return '(?:' + ''.join(str(x) for x in self) + ')'

    class alt(list):
        def __init__(self, *args):
            self.extend(args)
        def __str__(self):
            return '(?:' + '|'.join(str(x) for x in self) + ')'

    def parse(self, ses, fn, opt):

        # init
        self.re = re.compile(str(self.regexp))
        self.chunk_init()
        pt = util.parse_time()

        # process the file
        for line in util.file_progress(ses, fn):

            # match line
            line = line.strip()
            m = self.re.match(line)
            if m:

                # process time_key
                time = m.group(self.time_key)
                if time:
                    for chunk in self.chunk_emit(flush=False):
                        yield chunk
                    self.chunk_extend()
                    self.chunk[self.time_key][-1] = time
                    self.last_time = time

                # process each data_key
                for data_key in self.re.groupindex:
                    if data_key != self.time_key:
                        data = m.group(data_key)
                        if data != None:
                            if self.chunk[data_key][-1] != None:
                                self.chunk_extend()
                                self.chunk[self.time_key][-1] = self.last_time
                            self.chunk[data_key][-1] = data

        # finish up
        for chunk in self.chunk_emit(flush=True):
            yield chunk

    def info(self, ses, fn, t):
        ses.put('NOT IMPLEMENTED')


####
#### replica set status
#### do special-case computation of repl set lag here to produce a sequence of samples
#### then delegate to the generic series_process_fields
####
###def series_process_rs(series, opt):
###
###    # delegate to generic field processor
###    p = init_dst(series_process_fields(series, opt))
###
###    # wait for a config with members
###    jnode = yield
###    while not 'members' in jnode:
###        jnode = yield
###
###    # compute and send headers
###    jnode = yield
###    headers = ['time']
###    if 'members' in jnode:
###        for m in jnode['members']:
###            name = m['name']
###            for s in ['state', 'lag']:
###                headers.append(name + ' ' + s)
###    p.send(headers)
###
###    while True:
###
###        # next json doc
###        jnode = yield
###        
###        # still a valid config?
###        if 'members' in jnode:
###
###            # compute primary_optime
###            primary_optime = None
###            for m in jnode['members']:
###                if m['stateStr'] == 'PRIMARY':
###                    primary_optime = m['optime']['t']
###                    break
###
###            # compute result fields
###            result = [jnode['date']]
###            for m in jnode['members']:
###                result.append(m['state'])
###                secondary_optime = m['optime']['t']
###                if primary_optime and secondary_optime > 1:
###                    result.append(primary_optime - secondary_optime)
###                else:
###                    result.append('')
###
###        # send result to field processor
###        p.send(result)
###

#
# transfer(src, *dst) pulls data from src and pushes it to each *dst
# as a convenience we init each dst with .next
#

def init_dst(d):
    d.next()
    return d

def transfer(src, *dst):
    ds = [init_dst(d) for d in dst]
    for x in src:
        for d in ds:
            d.send(x)
    for d in ds:
        d.close()

#
# parse the source specified by fn using the specified parser, and
# transfer the resulting stream of dictionaries to process()
#

def parse_and_process(ses, fn, series, opt, parser):
    src = parser.parse(ses, fn, opt)
    dst = process(series, opt)    
    transfer(src, dst)

