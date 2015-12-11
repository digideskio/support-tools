import collections
import datetime as dt
import dateutil.parser
import os
import pytz
import re
import sys
import time

import util

#
# messages
#

do_dbg = False

def dbg(*ss):
    if __name__=='__main__' and do_dbg:
        sys.stderr.write(' '.join(str(s) for s in ss) + '\n')
        sys.stderr.flush()

def msg(*ss):
    sys.stderr.write(' '.join(str(s) for s in ss) + '\n')
    sys.stderr.flush()


#
# date parsing
#

def datetime_parse(t):
    t = dateutil.parser.parse(t)
    # xxx default timezone?
    #if not t.tzinfo:
    #    t = t.replace(tzinfo=dateutil.tz.tzlocal())
    return t

# our t0 - internally times are represented as seconds since this time
# we use the unix epoch time so that times that come to use in that format
# are already in our internal format
t0 = dateutil.parser.parse('1970-01-01T00:00:00Z')

def f2s(f):
    return f2t(f).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + 'Z'

def f2t(f):
    return t0 + dt.timedelta(seconds=f)

def t2f(t):
    return (t-t0).total_seconds()

class parse_time:

    patterns = [
        ('(....)-(..)-(..)T(..):(..):(..)(?:\.(...))?(Z|[+-]....)', (1, 2, 3, 4, 5, 6, 7, 8)),
    ]

    def __init__(self):
        self._parse_time = None
        self.gs = None
        self.pat = None
        self.tzo = None

    def _find_time(self, time):
        for pat, gs in parse_time.patterns:
            try:
                self.pat = re.compile(pat)
                self.gs = gs
                tz = self.pat.match(time).group(self.gs[7])
                if tz=='Z':
                    self.tzo = dateutil.tz.tzoffset(None, 0)
                else:
                    tzo = 60 * (60*int(tz[1:3]) + int(tz[3:5]))
                    if tz[0]=='-': tzo = -tzo
                    self.tzo = dateutil.tz.tzoffset(None, tzo)
                self._parse_time = self._parse_time_fast
            except:
                pass
        if not self._parse_time:
            #util.msg('using slow timestamp parsing')
            self._parse_time = self._parse_time_slow

    def parse_time(self, time, opt, tz):
        if not self._parse_time:
            self._find_time(time)
            time = self._parse_time(time, opt, tz)
            # xxx default timezone?
            #global t0
            #t0 = t0.astimezone(time.tzinfo)
        else:
            time = self._parse_time(time, opt, tz)

        # convert to internal fp repr
        if time.tzinfo==None:
            if tz==None:
                msg = "no timezone for %s; specify input timezone, e.g., --itz=-5" % time
                raise Exception(msg)
            else:
                tzinfo = dateutil.tz.tzoffset('xxx', tz.total_seconds())
                time = time.replace(tzinfo=tzinfo)
        time = util.t2f(time)
    
        # done
        return time
    
    def _parse_time_fast(self, time, opt, tz):
        group = self.pat.match(time).group
        ms = group(self.gs[6])
        us = 1000*int(ms) if ms else 0
        g = lambda i: int(group(self.gs[i]))
        return dt.datetime(g(0), g(1), g(2), g(3), g(4), g(5), us, self.tzo)

    def _parse_time_slow(self, time, opt, tz):

        # dateutil first, then unix timestamp
        try:
            #if s and s.default_date:
            #    time = dateutil.parser.parse(time, default=s.default_date)
            #else:
            time = dateutil.parser.parse(time)
        except Exception as e:
            util.dbg(e)
            time = dt.datetime.fromtimestamp(int(time), pytz.utc)
    
        # xxx default timezone?
        # supply tz if missing
        #if not time.tzinfo:
        #    if s:
        #        time = pytz.utc.localize(time-s.tz)
        #    else:
        #        raise Exception('require non-naive timestamps')

        return time



#
# read lines from file, printing progress messages
#

def file_progress(ses, fn, sniff=0, every=2.0):

    # start time, initial progress message
    start_time = time.time()
    last_report = start_time
    if not sniff:
        ses.progress('reading %s' % fn)

    # enumerate lines
    with open(fn) as f:

        # file size for % msgs
        try:
            f.seek(0, 2)
            size = f.tell()
            f.seek(0)
        except Exception as e:
            util.dbg('no size:', e)
            size = None

        # enumerate lines
        for n, line in enumerate(f):
            yield line
            if sniff and n >= sniff:
                break
            if n>0 and n%100==0:
                t = time.time()
                if t-last_report >= every:
                    s = '%s: processed %d lines' % (fn, n)
                    if size:
                        s += ' (%d%%)' % (100.0*f.tell()/size)
                    ses.progress(s)
                    last_report = t

    # final stats
    t = time.time() - start_time
    util.dbg('%s: %d lines, %.3f s, %d lines/s' % (fn, n, t, n/t))


#
# yield a list of items, printing progress messages
#

def item_progress(ses, name, cat, items, count, every=2.0):

    start_time = time.time()
    last_report = start_time
    ses.progress('processing %s' % name)

    for n, item in enumerate(items):
        yield item
        if n>0 and n%10==0:
            t = time.time()
            if t-last_report >= every:
                pct = 100.0 * n / count
                ses.progress('%s: processed %d %s (%d%%)' % (name, n, cat, pct))
                last_report = t



#
# each subclass manages a file cache
# each instance represents a single file
# subclass must supply constructor that takes a single argument that is the filename
# entries are invalidated if file mod time changes
#

class FileCache:

    # cache of known files
    cache = {}

    @classmethod
    def get(cls, fn):
        if fn in cls.cache:
            f = cls.cache[fn]
            if f.valid():
                return f
        f = cls(fn)
        f.mtime = os.stat(fn).st_mtime
        cls.cache[fn] = f
        return f

    def valid(self):
        valid = os.stat(self.fn).st_mtime==self.mtime
        return valid

    def __init__(self, fn):
        self.fn = fn


#
# for efficient processing metric names are represented as a single string
# consisting of the BSON path elements joined by SEP
# use / instead of . because some metrics names include .
# xxx now used elsewhere, e.g. for ordinary json, so this should move...
#

SEP = '/'

def join(*s):
    return SEP.join(s)

BSON = collections.OrderedDict


#
# utilities for printing chunk info
#

def print_bson_doc(doc, prt, indent=''):
    for k, v in doc.items():
        if type(v)==BSON:
            prt(indent + k)
            print_bson_doc(v, prt, indent+'    ')
        else:
            prt(indent + k, v)
        
def print_sample(chunk, sample, prt):

    def put_bson(bson, n, v):
        if len(n)>1:
            if not n[0] in bson:
                bson[n[0]] = BSON()
            put_bson(bson[n[0]], n[1:], v)
        else:
            bson[n[0]] = v

    bson = BSON()
    for name, value in chunk.items():
        put_bson(bson, name.split(util.SEP), value[sample])
    print_bson_doc(bson, prt, '    ')

#
#
#

def words(s):
    #return re.split('\W+', s.lower())
    return re.sub('[^a-zA-Z0-9]', ' ', s).lower().split()

