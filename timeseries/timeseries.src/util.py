import sys
import dateutil.parser
import datetime as dt
import pytz
import re
import time

import util

#
# messages
#

do_dbg = False

def dbg(*ss):
    if __name__=='__main__' and do_dbg:
        sys.stderr.write(' '.join(str(s) for s in ss) + '\n')

def msg(*ss):
    sys.stderr.write(' '.join(str(s) for s in ss) + '\n')


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

    def parse_time(self, time, opt, s):
        if not self._parse_time:
            self._find_time(time)
            time = self._parse_time(time, opt, s)
            # xxx default timezone?
            #global t0
            #t0 = t0.astimezone(time.tzinfo)
        else:
            time = self._parse_time(time, opt, s)

        # convert to internal fp repr
        if time.tzinfo==None:
            if s.tz==None:
                msg = "no timezone for %s; specify timezone, e.g., iostat(tz=-5):iostat.log" % time
                raise Exception(msg)
            else:
                tzinfo = dateutil.tz.tzoffset('xxx', s.tz.total_seconds())
                time = time.replace(tzinfo=tzinfo)
        time = util.t2f(time)
    
        # subset or range of times
        if time < opt.after or time >= opt.before:
            return None
        elif s.every:
            if time - opt.last_time < s.every:
                return None
            else:
                opt.last_time = time
    
        # time is in range
        return time
    
    def _parse_time_fast(self, time, opt, s):
        group = self.pat.match(time).group
        ms = group(self.gs[6])
        us = 1000*int(ms) if ms else 0
        g = lambda i: int(group(self.gs[i]))
        return dt.datetime(g(0), g(1), g(2), g(3), g(4), g(5), us, self.tzo)

    def _parse_time_slow(self, time, opt, s):

        # dateutil first, then unix timestamp
        try:
            if s and s.default_date:
                time = dateutil.parser.parse(time, default=s.default_date)
            else:
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

def progress(ses, fn, every=2.0):

    # start time, initial progress message
    start_time = time.time()
    last_report = start_time
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


