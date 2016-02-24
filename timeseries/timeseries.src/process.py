import collections
import datetime as dt
import json
import re
import traceback

import ftdc
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

class Chunk(collections.defaultdict):
    pass

class Chunker:

    def chunk_init(self):
        self.chunk_len = 0
        self.chunk = Chunk(lambda: [None for _ in range(self.chunk_len)])
        self.last_time = None

    def chunk_extend(self):
        for l in self.chunk.values():
            l.append(None)
        self.chunk_len += 1
    
    def chunk_emit(self, flush=False):
        if flush or self.chunk_len >= 100:
            yield self.chunk
            self.chunk_init()


#
# manage a cache of chunks
# each instance represents the chunks for a single file
# files are cached by the class per the policy provided by the util.FileCach class
# subclass must supply _parse instance method that is called to compute the chunks for the file
# provides a parse class method that yields chunks by either
#     calling _parse to initially compute the chunks, or
#     returning chunks cached from a prior call to _parse
#

class ChunkCache(util.FileCache):

    @classmethod
    def parse(cls, ses, fn, opt, time_key):
        file = cls.get(fn)
        file.time_key = time_key
        if hasattr(file, 'chunks'):
            for chunk in util.item_progress(ses, file.fn, 'chunks', file.chunks, len(file.chunks)):
                yield chunk
        else:
            file.chunks = []
            for chunk in file._parse(ses, opt):
                file.chunks.append(chunk)
                yield chunk

    @classmethod
    def info(cls, ses, fn, t):
        def putln(*s):
            ses.put(' '.join(str(ss) for ss in s) + '\n')
        file = cls.get(fn)
        for chunk in file.chunks:
            if t >= chunk[file.time_key][0]:
                for sample, sample_time in enumerate(chunk[file.time_key]):
                    if sample_time >= t:
                        putln('%s at t=%.3f (%s)' % (fn, t, util.f2s(t)))
                        util.print_sample(chunk, sample, putln)
                        return

    def _parse(self, ses, opt, sniff):
        assert(False) # must be overriden

    @classmethod
    def sniff(cls, ses, fn, sniff):
        file = cls(fn) # bypass cache
        for chunk in file._parse(ses, ses.opt, sniff):
            yield chunk


################################################################################
#
# each parse_*.parse() generator reads and parses files of a given type,
# yielding a sequence of chunks
#

#
# read and parse csv files
# maintains a chunk cache
# xxx fragile, consider using Python cvs module; check performance...
#

class parse_csv(Chunker, ChunkCache):

    def _parse(self, ses, opt, sniff=0):
        self.chunk_init()
        keys = None
        for line in util.file_progress(ses, self.fn, sniff):
            line = line.strip()
            fields = line.split(',')
            if fields and fields[0] and fields[0][0]=='"':
                fields = [f.strip('"') for f in fields]
            if not keys:
                keys = fields
            else:
                self.chunk_extend()
                values = fields
                for k, v in zip(keys, values):
                    self.chunk[k][-1] = v
            for chunk in self.chunk_emit():
                yield chunk
        for chunk in self.chunk_emit(True):
            yield chunk

class parse_win_csv(parse_csv):
    def _parse(self, ses, opt, sniff=0):
        for chunk in parse_csv._parse(self, ses, opt, sniff):
            for key in chunk.keys():
                if 'PDH-CSV 4.0' in key:
                    tz = key.split('(')[3].strip(')')
                    chunk.tz = dt.timedelta(hours = -float(tz)/60)
                    new_key = 'time'
                else:
                    new_key = ': '.join(key.split('\\')[3:])
                chunk[new_key] = chunk[key]
                del chunk[key]
            yield chunk


#
# read and parse json files
# maintains a chunk cache
#

class parse_json(ChunkCache):

    def _parse(self, ses, opt, sniff=0):

        ignore = set(['floatApprox', '$date', '$numberLong', '$timestamp'])
        chunk_size = 100
    
        def flatten(result, j, key=None):
            if type(j)==dict:
                for k, v in j.items():
                    if k in ignore:
                        flatten(result, v, key)
                    else:
                        flatten(result, v, key + util.SEP + k if key else k)
            else:
                result[key] = [j]
            return result
    
        chunk = {}
        for line in util.file_progress(ses, self.fn, sniff):
            try:
                j = flatten({}, json.loads(line))
                if j.keys() != chunk.keys() or len(chunk.values()[0]) >= chunk_size:
                    if chunk:
                        yield chunk
                    chunk = j
                else:
                    for k, v in j.items():
                        chunk[k].extend(v)
            except ValueError:
                # ignore bad json
                pass
            except:
                traceback.print_exc()
                break
        yield chunk


#
# read and parse ftdc metrics files
# manages its own chunk cache in order to do lazy evaluation
#

class parse_ftdc:

    @staticmethod
    def parse(ses, fn, opt, time_key):
        return ftdc.read(ses, fn, opt)

    @staticmethod
    def info(ses, fn, t, kind):
        def prt(*stuff):
            ses.put(' '.join(str(s) for s in stuff) + '\n')
        ftdc.info(ses, fn, t, prt, kind)


#
# process a series of lines using regexps
#

# helper class for constructing regexp that is a sequence of items
class seq(list):
    def __init__(self, *args):
        self.extend(args)
    def __str__(self):
        return '(?:' + ''.join(str(x) for x in self) + ')'

# helper class for constructing regexp that is a set of alternative items
class alt(list):
    def __init__(self, *args):
        self.extend(args)
    def __str__(self):
        return '(?:' + '|'.join(str(x) for x in self) + ')'

# create a class for parsing the specified regexp
def parse_re(time_key, regexp):

    # compile regexp up front
    rec = re.compile(str(regexp))

    # create a class for parsing the specified regexp
    # maintains a separate chunk cache per regexp
    class ParseRe(Chunker, ChunkCache):

        def _parse(self, ses, opt, sniff=0):
    
            # init
            self.chunk_init()
            pt = util.parse_time()
    
            # process the file
            for line in util.file_progress(ses, self.fn, sniff):
    
                # match line
                line = line.strip()
                m = rec.match(line)
                if m:
    
                    # process time_key
                    time = m.group(time_key)
                    if time:
                        for chunk in self.chunk_emit(flush=False):
                            yield chunk
                        self.chunk_extend()
                        self.chunk[time_key][-1] = time
                        self.last_time = time
    
                    # process each data_key
                    for data_key in rec.groupindex:
                        if data_key != time_key:
                            data = m.group(data_key)
                            if data != None:
                                if self.chunk[data_key][-1] != None:
                                    self.chunk_extend()
                                    self.chunk[time_key][-1] = self.last_time
                                self.chunk[data_key][-1] = data
    
            # finish up
            for chunk in self.chunk_emit(flush=True):
                yield chunk

    # return our constructed class
    return ParseRe


################################################################################
#
# process() yields a generator which accepts a stream of chunks
# and computes graphs from the chunk data, under the direction of
#     series - list of graphing.Series objects each specifying a view on the data
#     opt - global options that control the generation of the graphs
# 
def process(series, fn, opt):

    # to track metrics present in the data but not processed by any series
    unrecognized = set()

    # xxx does time parsing belong here or in the parse routines?
    pt = util.parse_time()

    # process all chunk that we are sent
    while True:

        try:

            # get our next input
            chunk = yield
                    
            def process_series(s, data_key):
                tz = chunk.tz if hasattr(chunk, 'tz') else s.tz
                time_key = s.time_key # e.g. 'serverStatus.localTime'
                if data_key in chunk and time_key in chunk:
                    ts = chunk[time_key]
                    if type(ts[0])==str or type(ts[0])==unicode:
                        for i, t in enumerate(ts):
                            ts[i] = pt.parse_time(t, opt, tz)
                    if ts[0]/s.time_scale > opt.before or ts[-1]/s.time_scale < opt.after:
                        return
                    for i, (t, d) in enumerate(zip(ts, chunk[data_key])):
                        t = t / s.time_scale
                        if t>=opt.after and t<=opt.before:
                            def get_field(key):
                                try: return chunk[key][i]
                                except IndexError: return None
                            if d != None:
                                s.data_point(t, d, get_field, None, opt)

            # send each series our data points
            for s in series:
                if s.special:
                    s.special(chunk)
                if s.split_on_key_match:
                    for data_key in chunk:
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
            unrecognized.update(chunk.keys())

        except GeneratorExit:
            break

        except Exception as e:
            traceback.print_exc()
            raise Exception('error while processing ' + fn + ': ' + str(e))

    # compute and print unrecognized metrics
    ignore = re.compile(
        '^serverStatus.(repl|start|end)|'
        '^replSetGetStatus|slot_closure_rate'
    )
    for s in series:
        unrecognized.discard(s.data_key)
        unrecognized.discard(s.time_key)
    unrecognized = filter(lambda x: not ignore.match(str(x)), unrecognized)
    is_str = lambda x: type(x)==str or type(x)==unicode
    unrecognized = filter(lambda x: x in chunk and not is_str(chunk[x][0]), unrecognized)
    if unrecognized:
        util.msg('unrecognized metrics:')
        for u in sorted(unrecognized):
            util.msg('   ', u)




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
    src = parser.parse(ses, fn, opt, series[0].time_key)
    dst = process(series, fn, opt)
    transfer(src, dst)

