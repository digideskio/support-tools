import argparse
import collections
import dateutil.parser
import dateutil.tz
from datetime import datetime, timedelta
import importlib
import itertools
import json
import math
import os
import pytz
import re
import sys
import time
import string

def elt(name, attrs={}):
    sys.stdout.write('<%s' % name)
    for a in sorted(attrs):
        sys.stdout.write(' %s="%s"' % (a, attrs[a]))
    sys.stdout.write('>')

def eltend(name, attrs={}, *content):
    elt(name, attrs)
    put(*content)
    end(name)

def end(name):
    sys.stdout.write('</' + name + '>')

def put(*content):
    for s in content:
        sys.stdout.write(s)

#
#
#

def dbg(*ss):
    if __name__=='__main__' and opt.dbg:
        sys.stderr.write(' '.join(str(s) for s in ss) + '\n')

def msg(*ss):
    sys.stderr.write(' '.join(str(s) for s in ss) + '\n')

#
#
#

graph_style = '''
    table, tr, td {
        padding: 0;
        margin: 0;
        border-spacing:0;
    }
    .curve {
        fill: none;
        stroke: black;
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
    .shaded {
        fill: rgb(230,230,230);
        stroke: rgb(230,230,230);
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
    .shaded-hot {
        fill: rgb(250,220,220);
        stroke: rgb(240,220,220);
    }
    .shaded-cold {
        fill: rgb(200,220,240);
        stroke: rgb(230,230,230);
    }
    .tick {
        stroke: rgba(0,0,0,0.08);
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
'''

xpad = 1.5
ypad = 0.1

def html_graph(
    data=[],
    tmin=None, tmax=None, width=None,
    ymin=None, ymax=None, height=None,
    ticks=None, line_width=0.1, shaded=True,
    bins=0
):

    elt('svg', {
        'width':'%gem' % width,
        'height':'%gem' % height,
        'viewBox':'%g %g %g %g' % (0, 0, width, height)
    })

    for ts, ys, color in data:

        if not ts:
            continue

        tspan = float((tmax-tmin).total_seconds())
        yspan = float(ymax - ymin)
        if yspan==0:
            if ymin==0:
                yspan = 1
            else:
                ymin -= 1
                yspan = 1

        dt = lambda t: (t-tmin).total_seconds()  # dt relative to global tmin
        gx = lambda dt: dt / tspan * (width-2*xpad) + xpad # gx for a given dt
        gy = lambda y: ((1 - (y-ymin) / yspan) * (1-2*ypad) + ypad) * height

        dtmin = dt(ts[0])             # first time relative to global tmin
        dtmax = dt(ts[-1])            # last time relative to global tmin
        xmin = gx(dtmin)              # leftmost x
        xmax = gx(dtmax)              # rightmost x

        nbins = int(bins * math.ceil(xmax-xmin)) if bins else float('inf') # max graph complexity

        if len(ts)<nbins or nbins==0:

            # draw individual points
            line = ' '.join('%g,%g' % (gx(dt(t)), gy(ys[t])) for t in ts)
            if shaded:
                left = '%g,%g' % (xmin, gy(0))
                right = '%g,%g' % (xmax, gy(0))
                points = left + ' ' + line + ' ' + right
                cls = 'shaded'
                if type(shaded)==str: cls += ' ' + shaded
                eltend('polygon', {'points':points, 'class':cls})
            eltend('polyline', {'points':line, 'class':'curve', 'style':'stroke:%s'%color})

        else:

            # bin the data for graphing to bound graph complexity
            tbin = (dtmax-dtmin+1e-9) / nbins # time per bin
            ymins = [float('inf')] * nbins    # upper y for each bin
            ymaxs = [-float('inf')] * nbins   # lower y for each bin
            for t in ts:
                bi = int((dt(t) - dtmin) / tbin)
                ymins[bi] = min(ymins[bi], ys[t])
                ymaxs[bi] = max(ymaxs[bi], ys[t])
            bis = [i for i in range(nbins) if ymins[i]!=float('inf')]
            bt = lambda i: dtmin + (i+0.5)*tbin
            line = ' '.join(r'%g,%g' % (gx(bt(i)), gy(ymins[i])) for i in reversed(bis))
            if shaded:
                left = '%g,%g' % (xmin, gy(0))
                right = '%g,%g' % (xmax, gy(0))
                points = right + ' ' + line + ' ' + left
                eltend('polygon', {'points':points, 'class':'shaded'})
            line += ' ' + ' '.join(r'%g,%g' % (gx(bt(i)), gy(ymaxs[i])) for i in bis)
            style = 'stroke:%s; fill:%s; stroke-width:0.7' % (color, color)
            eltend('polyline', {'points':line, 'class':'curve', 'style':style})


    if data and ticks:
        if type(ticks)==int:
            ticks = [tmin + (tmax-tmin)*i/ticks for i in range(ticks+1)]
        for t in ticks:
            x = gx(dt(t))
            eltend('line', {'x1':x, 'x2':x, 'y1':0, 'y2':height, 'class':'tick'})

    end('svg')

def labels(tmin, tmax, width, ts, labels):
    elt('div', {'style':'height: 1.1em; position:relative; width:%gem' % width})
    tspan = float((tmax-tmin).total_seconds())
    gx = lambda t: (t-tmin).total_seconds() / tspan * (width-2*xpad) + xpad
    for t, label in zip(ts, labels):
        style = 'left:{x}em; position:absolute; width:100em'.format(x=gx(t)-50)
        elt('span', {'align':'center', 'style':style})
        eltend('span', {'align':'center', 'style':'font-size:80%'}, label)
        end('span')
    end('div')


#
#
#

t0 = dateutil.parser.parse('2000-01-01T00:00:00Z')

REQUIRED = []
fmtr = string.Formatter()

def get(descriptor, n, default=REQUIRED):
    v = descriptor.get(n, default)
    if v is REQUIRED:
        raise Exception('missing required parameter '+repr(n)+' in '+descriptor['name'])
    try:
        if (type(v)==str or type(v)==unicode):
            v = fmtr.vformat(str(v), (), descriptor)
        elif type(v)==list:
            v = [fmtr.vformat(str(s), (), descriptor) for s in v] # xxx recursive? dict?
    except KeyError as e:
        raise Exception('missing required parameter '+repr(e.message)+' in '+descriptor['name'])
    return v

class Series:

    def __init__(self, spec, descriptor, params, fn, spec_ord, tag):

        self.spec = spec
        self.descriptor = dict(descriptor)
        self.descriptor.update(params)
        self.spec_ord = spec_ord
        self.tag = tag
        self.key = (tag, descriptor['_ord'], spec_ord)

        # make fn avaialbe for formatting
        self.fn = fn
        self.descriptor['fn'], _ = os.path.splitext(os.path.basename(fn))

        # compute rate (/s) 
        self.rate = self.get('rate', False)
        if self.rate:
            self.last_t = None
    
        # request to bucketize the data
        self.buckets = float(self.get('bucket_size', 0))
        if self.buckets:
            op = self.get('bucket_op', 'max')
            if op=='max':
                self.op = lambda ys, t, d: max(ys[t], d)
            elif op=='count':
                self.op = lambda ys, t, d: ys[t]+1 if d>=self.count_min else ys[t]
        self.count_min = float(self.get('count_min', 0))

        # compute queued ops from op execution time
        self.queue = self.get('queue', False)
        if self.queue:
            self.queue_times = []
            self.queue_min_ms = float(self.get('queue_min_ms', 0))
    
        # scale the data (divide by this)
        self.scale = self.get('scale', 1) # scale by this constant
        self.scale_field = self.descriptor['scale_field'] if 'scale_field' in self.descriptor else None # xxx self.get?
    
        # allows other fields to use this field value
        self.set_field =  self.get('set_field', None)

        # requested ymax
        self.spec_ymax = float(self.get('ymax', '-inf'))

        # initially empty timeseries data
        self.ys = collections.defaultdict(int)
    
        # text, json, ...: used to select from multiple possible descriptors
        self.file_type = self.get('file_type')

        # re, json, ...: used to route to proper parse routine
        self.parse_type = self.get('parse_type')

        # info for re-format files
        if self.parse_type=='re':
            self.re = self.get('re', None)
            if self.re and re.compile(self.re).groups==0:
                raise Exception('re ' + self.re + ' does not have any groups')
            self.re_time = self.get('re_time', 0)
            self.re_data = self.get('re_data', 1)

        # info for json-based files
        self.json_fields = self.get('json_fields', None)

        # info for field-based file formats, like csv and rs
        self.field_name = self.get('field_name', None)

        # special csv header processing
        self.process_headers = self.get('process_headers', lambda series, headers: headers)

        # timezone offset
        tz = self.get('tz', None)
        if tz==None:
            self.tz = datetime(*time.gmtime()[:6]) - datetime(*time.localtime()[:6])
        else:
            self.tz = timedelta(hours=float(tz))

        # default datetime instance for incomplete timestamps
        default_date = self.get('default_date', None)
        self.default_date = dateutil.parser.parse(default_date) if default_date else None

        # all graphs in a ygroup will be plotted with a common display_ymax
        self.ygroup = self.get('ygroup', id(self))

        # which output graph this series will be plotted on
        self.graph = id(self) # will update with desc['merge'] later so can use split key

        # split into multiple series based on a data value
        self.split_field = self.get('split_field', None)
        self.split_series = {}

        # hack to account for wrapping data
        self.wrap = self.get('wrap', None)
        self.wrap_offset = 0
        self.last_d = 0

        # level
        self.level = self.get('level', 0)

        # reference point for computing relative times
        self.t0 = None

    def get(self, *args):
        return get(self.descriptor, *args)

    def get_graphs(self, graphs, ygroups, opt):
        if not self.split_field: # xxx and not self.split_all: ?
            if opt.merges:
                merge = self.get('merge', None)
                if merge: self.graph = merge
            self.name = self.get('name')
            if self.tag: self.name = self.tag + ': ' + self.name
            graphs[self.graph].append(self)
            ygroups[self.ygroup].append(self)
        for s in self.split_series.values():
            s.get_graphs(graphs, ygroups, opt)

    def _data_point(self, t, d, get_field, set_field):

        # may not have data in case of a count, so just use 0
        try:
            d = float(d)
        except:
            d = 0

        # wrapping 32-bit counter hack
        if self.wrap:
            if self.last_d > self.wrap/2 and d < -self.wrap/2:
                self.wrap_offset += 2 * self.wrap
                dbg('wrap', d, self.last_d, self.wrap_offset)
            elif self.last_d < -self.wrap/2 and d > self.wrap/2:
                self.wrap_offset -= 2 * self.wrap
                dbg('wrap', d, self.last_d, self.wrap_offset)
            self.last_d = d
            d += self.wrap_offset

        # compute a rate
        if self.rate:
            if self.last_t==t:
                return
            if self.last_t:
                dd = d - self.last_d
                if self.rate != 'delta':
                    dd /= (t-self.last_t).total_seconds()
                self.last_t = t
                self.last_d = d
                d = dd
            else:
                self.last_t = t
                self.last_d = d
                return

        # scale - xxx need general computation mechanism here instead
        if self.scale_field:
            scale_field = self.scale_field.format(**self.descriptor)
            try:
                div = float(get_field(scale_field))
            except:
                return
            if div:
                d /= div
        d /= self.scale

        # record the data
        if self.buckets:
            s0 = (t - t0).total_seconds()
            s1 = s0 // self.buckets * self.buckets
            t = t + timedelta(0, s1-s0)
            self.ys[t] = self.op(self.ys, t, d)
        elif self.queue:
            if d>self.queue_min_ms:
                ms = timedelta(0, d/1000.0)
                self.queue_times.append((t-ms,+1))
                self.queue_times.append((t,-1))
        else:
            self.ys[t] = d

        # make data available for computation
        if self.set_field and set_field:
            set_field(self.set_field, d)

        # tell our caller what we recorded
        return d

    def get_split(self, split_key):
        if split_key not in self.split_series:
            new = Series(self.spec, self.descriptor, {}, self.fn, self.spec_ord, self.tag)
            if self.split_field: # this is getting a little creaky - generalize? move up into data_point?
                if type(self.split_field)==str:
                    new.descriptor[self.split_field] = split_key
                else:
                    for name, value in zip(self.split_field, split_key):
                        new.descriptor[name] = value
                new.key = (self.tag, split_ords[self.split_field], split_key, new.key)
            else:
                new.descriptor['field'] = split_key # xxx - ?
            new.split_field = None
            new.split_all = None
            self.split_series[split_key] = new
        return self.split_series[split_key]


    def data_point(self, t, d, get_field, set_field, opt):
        if opt.relative:
            if self.t0 is None:
                self.t0 = t
            t = t0 + (t - self.t0)
        if self.split_field:
            if type(self.split_field)==str:
                split_key = get_field(self.split_field)
            else:
                split_key = tuple(get_field(s) for s in self.split_field)
            s = self.get_split(split_key)
        else:
            s = self
        return s._data_point(t, d, get_field, set_field)


    def finish(self):

        if self.buckets:
            if self.ys.keys():
                tmin = min(self.ys.keys())
                tmax = max(self.ys.keys())
                n = int(math.ceil(float((tmax-tmin).total_seconds()) / self.buckets))
                dt = timedelta(0, self.buckets)
                self.ts = [tmin + dt*i for i in range(n+1)]
            else:
                self.ts = []
        elif self.queue:
            q = 0
            for t, d in sorted(self.queue_times):
                q += d
                self.ys[t] = q
                self.ts.append(t)
        else:
            self.ts = sorted(self.ys.keys())
    
        self.tmin = self.ts[0] if self.ts else None
        self.tmax = self.ts[-1] if self.ts else None
        self.ymin = min(self.ys.values()) if self.ys else float('inf')
        self.ymax = max(self.ys.values()) if self.ys else float('-inf')
        self.ysum = sum(self.ys.values()) if self.ys else 0
    
        for s in self.split_series.values():
            s.finish()

def get_series(spec, spec_ord, opt):

    # parse helper
    def split(s, expect, err, full):
        m = re.split('([' + expect + err + '])', s, 1)
        s1, d, s2 = m if len(m)==3 else (m[0], '$', '')
        if d in err:
            msg = 'expected %s at pos %d in %s, found %s' % (expect, len(full)-len(s)+1, full, d)
            raise Exception(msg)
        return s1, d, s2

    # parse the spec
    left, d, s = split(spec, '(:=', ')', spec)
    if d=='=': # has tag
        tag = left
        spec_name, d, s = split(s, '(:', ')=', spec)        
    else: # no tag
        tag = None
        spec_name = left
    params = {}
    if d == '(': # has args
        while d != ')': # consume args
            name, d, s = split(s, '=)', '(', spec) # get arg name
            value, d, s = split(s, '(),', '', spec) # bare value
            p = 0
            while d=='(' or p>0: # plus balanced parens
                value += d
                if d=='(': p += 1
                elif d==')': p -= 1
                v, d, s = split(s, '(),', '', spec)
                value += v
            params[name] = value
    fn = s.lstrip(':') # xxx canonicalize fn
    dbg(spec_name, params, fn)

    # ignore punctuation, 
    def words(s):
        #return re.split('\W+', s.lower())
        return re.sub('[^a-zA-Z0-9]', ' ', s).lower().split()

    def detect(fn):
        with open(fn) as f:
            for i in range(10):
                try:
                    json.loads(f.next())
                    return 'json'
                except Exception as e:
                    dbg(e)
                    pass
        return 'text'

    file_type = detect(fn)
    msg('detected type of', fn, 'as', file_type)

    # find matching descriptors
    scored = collections.defaultdict(list)
    spec_name_words = words(spec_name)
    for desc in descriptors:
        if get(desc,'file_type') != file_type:
            continue
        desc_name_words = words(desc['name'])
        last_i = -1
        beginning = matched = in_order = adjacent = 0
        for w, word in enumerate(spec_name_words):
            try:
                i = desc_name_words.index(word)
                if i==0 and w==0: beginning = 1
                matched += 1
                if i==last_i+1: adjacent += 1
                elif i>last_i: in_order += 1
                last_i = i
            except ValueError:
                pass
        score = (beginning, matched, adjacent, in_order)
        scored[score].append(desc)
    best_score = sorted(scored.keys())[-1]
    best_descs = scored[best_score] if best_score != (0,0,0,0) else []
    series = [Series(spec, desc, params, fn, spec_ord, tag) for desc in best_descs]

    # no match?
    if not series:
        msg('no descriptors match', spec_name)

    return series


#
# flexible date parser
#

def get_time(time, opt, s):

    # dateutil first, then unix timestamp
    try:
        if s and s.default_date:
            time = dateutil.parser.parse(time, default=s.default_date)
        else:
            time = dateutil.parser.parse(time)
    except Exception as e:
        dbg(e)
        time = datetime.fromtimestamp(int(time), pytz.utc)

    # supply tz if missing
    if not time.tzinfo:
        if s:
            time = pytz.utc.localize(time-s.tz)
        else:
            raise Exception('require non-naive timestamps')

    # subset or range of times
    if time < opt.after or time >= opt.before:
        return None
    elif opt.every:
        if time - opt.last_time < opt.every:
            return None
        else:
            opt.last_time = time

    return time


#
# read lines from file, printing progress messages
#

def progress(fn, opt):

    # start time
    t = time.time()

    # enumerate lines
    with open(fn) as f:

        # file size for % msgs
        try:
            f.seek(0, 2)
            size = f.tell()
            f.seek(0)
        except Exception as e:
            dbg('no size:', e)
            size = None

        # enumerate lines
        msg('reading', fn)
        for n, line in enumerate(f):
            yield line
            if n>0 and n%opt.progress_every==0:
                s = '%s: processed %d lines' % (fn, n)
                if size:
                    s += ' (%d%%)' % (100*f.tell()/size)
                msg(s)

    # final stats
    t = time.time() - t
    dbg('%s: %d lines, %.3f s, %d lines/s' % (fn, n, t, n/t))


#
# handle special names inserted by javascript JSON.stringify()
#

def fixup(j):
    if type(j)==dict:
        for k, v in j.items():
            if type(v)==dict:
                if len(v)==1:
                    if '$date' in v:
                        j[k] = v['$date']
                    elif '$numberLong' in v:
                        j[k] = int(v['$numberLong'])
                    elif '$timestamp' in v:
                        j[k] = v['$timestamp']
                    elif 'floatApprox' in v:
                        j[k] = v['floatApprox']
                fixup(v)
            elif type(v)==list:
                fixup(v)
    elif type(j)==list:
        for jj in j:
            fixup(jj)



#
# each read_* generator reads files of a given type
# and yields a sequence of parsed data structures
# useable as a src for transfer(src, *dst)
#

def read_csv(fn, opt):
    for line in progress(fn, opt):
        yield [s.strip(' \n"') for s in line.split(',')]


def read_json(fn, opt):
    for line in progress(fn, opt):
        if line.startswith('{'):
            try:
                jnode = json.loads(line)
                fixup(jnode)
                yield jnode
            except Exception as e:
                msg('ignoring bad line', e)


def read_lines(fn, opt):
    return progress(fn, opt)


#
# each series_process_* generator accepts data of a given type
# and generates graphs from the data as determined by the series arg
# useable as a dst for transfer(src, *dst)
# 

def series_process_json(fn, series, opt):

    # interior nodes
    interior = dict

    # leaf nodes - map each field name to list of series that specifies
    # the path terminating at that node by that field name
    class leaf(collections.defaultdict):
        def __init__(self):
            collections.defaultdict.__init__(self, list)

    # add a path to the path tree
    def add_path(pnode, path, fname, s):
        head = str(path[0])
        if len(path)==1:
            if not head in pnode:
                pnode[head] = leaf()
            pnode[head][fname].append(s)
        else:
            if not head in pnode:
                pnode[head] = interior()
            add_path(pnode[head], path[1:], fname, s)

    # construct combined path tree for all paths in all series
    ptree = interior()
    for s in series:
        if s.json_fields:
            for fname, path in s.json_fields.items():
                add_path(ptree, path, fname, s)

    # for reporting unmatched json paths
    unmatched = set()

    # match a path tree with a json doc
    def match(pnode, jnode, result, path=()):
        if type(pnode)==interior or type(jnode)==dict:
            for jname in jnode:
                pp = path + (jname,)
                try:
                    pnode_child = pnode[jname]
                    jnode_child = jnode[jname]
                    match(pnode_child, jnode_child, result, pp)
                except (KeyError, TypeError):
                    unmatched.add(pp)
        elif type(pnode)==list:
            unmatched.add(path)
        else:
            for fname in pnode:
                # convert time here so we don't do it multiple times for each series that uses it
                value = get_time(jnode, opt, None) if fname=='time' else jnode
                if value is not None:
                    for s in pnode[fname]:
                        result[s][fname] = value

    # process lines
    while True:
        try: jnode = yield
        except StopIteration: break
        time = None
        result = collections.defaultdict(dict)
        match(ptree, jnode, result)
        set_fields = {}
        for s in sorted(result.keys(), key=lambda s: s.key):
            fields = result[s]
            fields.update(set_fields)
            try:
                getitem = fields.__getitem__
                setitem = set_fields.__setitem__
                s.data_point(fields['time'], fields['data'], getitem, setitem, opt)
            except KeyError as e:
                pass

    # report on unmatched json paths
    if unmatched:
        msg('unmatched in', fn)
        for t in sorted(unmatched):
            msg('  ', [str(tt) for tt in t])


def series_process_fields(series, opt):
    field_names = None
    while True:
        line = yield
        if not field_names:
            field_names = series[0].process_headers(series, line)
            try:
                time_field = field_names.index('time')
            except:
                time_field = 0
        elif len(line)==len(field_names):
            field_values = line
            field_dict = dict(zip(field_names, field_values))
            for s in series:
                if not s.field_name:
                    continue
                t = get_time(field_values[time_field], opt, s)
                if not t:
                    break
                for i, (field_name, field_value) in enumerate(zip(field_names, field_values)):
                    if i != time_field:
                        m = re.match(s.field_name, field_name)
                        if m:
                            field_dict.update(m.groupdict())
                            getitem = field_dict.__getitem__
                            setitem = field_dict.__setitem__
                            field_value = s.data_point(t, field_value, getitem, setitem, opt)
                            field_dict[field_name] = field_value # xxx use set_field instead?


def series_process_re(series, opt):

    # group series by re
    series_by_re = collections.defaultdict(list)
    for s in series:
        series_by_re[s.re].append(s)

    # group res into chunks
    # Python re impl can only handle 100 groups
    # so we process the descriptors in chunks, constructing one chunk_re for each chunk
    # and match each line against the regex for each chunk
    chunk_size = 40
    chunks = []
    for i in range(0, len(series_by_re), chunk_size):
        chunk = series_by_re.keys()[i:i+chunk_size]
        chunk_re = ''
        chunk_groups = []
        chunk_group = 0
        for s_re in chunk:
            if chunk_re: chunk_re += '|'
            chunk_re += '(?:' + s_re + ')'
            chunk_groups.append(chunk_group)
            chunk_group += re.compile(s_re).groups
        #dbg(chunk_re)
        chunk_re = re.compile(chunk_re)
        chunks.append((chunk_re, chunk, chunk_groups))


    # process the file
    last_time = None
    while True:
        line = yield
        line = line.strip()
        for chunk_re, chunk, chunk_groups in chunks:
            m = chunk_re.match(line)
            if m:
                #dbg(m.groups())
                for chunk_group, s_re in zip(chunk_groups, chunk):
                    def get_field(g):
                        try: return m.group(chunk_group+g+1) if type(g)==int else m.group(g)
                        except Exception as e: raise Exception(g + ': ' + e.message)
                    for s in series_by_re[s_re]:
                        t = get_field(s.re_time)
                        if t:
                            t = get_time(t, opt, s)
                            if not t:
                                continue
                        else:
                            t = last_time                            
                        if t:
                            d = get_field(s.re_data)
                            if d != None:
                                s.data_point(t, d, get_field, None, opt)
                            last_time = t



#
# transfer(src, *dst) pulls data from src and pushes it to each *dst
# as a convenience we
#     init each dst with .next
#     wrap it in a genrator that catches StopIteration so dst does not need to
#

def init_dst(d):
    def wrap():
        d.next()
        while True:
            try:
                x = yield
                d.send(x)
            except StopIteration:
                pass
    w = wrap()
    w.next()
    return w

def transfer(src, *dst):
    ds = [init_dst(d) for d in dst]
    for x in src:
        for d in ds:
            d.send(x)

#
# each series_read_* routine processes and generates graphs from a file of a given type
# typically implemented by gluing a source and a destination together using transfer(src, *dst)
#

def series_read_re(fn, series, opt):
    transfer(read_lines(fn, opt), series_process_re(series, opt))

def series_read_json(fn, series, opt):
    transfer(read_json(fn, opt), series_process_json(fn, series, opt))

def series_read_fields(field_source, series, opt):
    transfer(field_source, series_process_fields(series, opt))


def series_read_csv(fn, series, opt):
    series_read_fields(read_csv(fn, opt), series, opt)


#
#
#

descriptors = []     # descriptors loaded from various def files
split_ords = {}      # sort order for each split_key - first occurrence of split_key in def file
descriptor_ord = 0

def descriptor(**desc):
    global descriptor_ord
    desc['_ord'] = descriptor_ord
    if 'split_field' in desc:
        split_field = desc['split_field']
        if not split_field in split_ords:
            split_ords[split_field] = desc['_ord']
    descriptors.append(desc)
    descriptor_ord += 1


def datetime_parse(t):
    t = dateutil.parser.parse(t)
    if not t.tzinfo:
        t = t.replace(tzinfo=dateutil.tz.tzlocal())
    return t


def get_graphs(specs, opt):

    if not hasattr(opt, 'after') or not opt.after: opt.after = pytz.utc.localize(datetime.min)
    if not hasattr(opt, 'before') or not opt.before: opt.before = pytz.utc.localize(datetime.max)
    if not hasattr(opt, 'every'): opt.every = None
    if type(opt.every)==float: opt.every = timedelta(seconds=opt.every)
    if type(opt.after)==str: opt.after = datetime_parse(opt.after)
    if type(opt.before)==str: opt.before = datetime_parse(opt.before)

    # parse specs, group them by file and parse type
    series = [] # all
    fns = collections.defaultdict(list) # grouped by fn
    for spec_ord, spec in enumerate(specs):
        try:
            for s in get_series(spec, spec_ord, opt):
                fns[(s.fn,s.parse_type)].append(s) # xxx canonicalize filename
                series.append(s)
        except Exception as e:
            msg(e)

    # process by file according to parse_type
    for fn, parse_type in sorted(fns):
        opt.last_time = pytz.utc.localize(datetime.min)
        read_func = globals()['series_read_' + parse_type]
        read_func(fn, fns[(fn,parse_type)], opt)
        
    # finish each series
    for s in series:
        s.finish()

    # get graphs taking into account splits and merges
    graphs = collections.defaultdict(list)
    ygroups = collections.defaultdict(list)
    for s in sorted(series, key=lambda s: s.key):
        s.get_graphs(graphs, ygroups, opt)

    # compute display_ymax taking into account spec_ymax and ygroup
    for g in graphs.values():
        for s in g:
            s.display_ymax = max(s.ymax, s.spec_ymax)
    for ygroup in ygroups.values():
        ygroup_ymax = max(s.ymax for s in ygroup)
        for s in ygroup:
            s.display_ymax = max(s.display_ymax, ygroup_ymax)

    # return the graphs
    return graphs.values()


#
# cursors
#

cursors_style = '''
    .cursor {
        stroke: rgba(0,0,255,.4);
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
    .deleter {
        fill: blue;
    }
    .letter {
        font-size: 85%
    }
    .data {
        padding-left: 0.5em
    }
'''

cursors_script = '''

    function event_x(e) {
        var evt = window.event
        return (evt.pageX - e.offsetLeft - e.offsetParent.offsetLeft) / e.offsetWidth
    }
  
    var svg_ns = "http://www.w3.org/2000/svg"
  
    function set_attrs(e, attrs) {
        for (a in attrs)
            e.setAttribute(a, attrs[a])
    }
  
    function elt(ns, name, attrs) {
        var e = document.createElementNS(ns, name)
        set_attrs(e, attrs)
        return e
    }
  
    function del_id(id) {
        var e = document.getElementById(id)
    }
  
    function move(e) {
        var x = event_x(e)
        set_attrs(document.getElementById('lll'), {x1:x, x2:x})
    }
  
    function out(e) {
        set_attrs(document.getElementById('lll'), {x1:-1, x2:-1})
    }
  
    var width = %d;
  
    function add(e) {
        var x = event_x(e)
        var cursor = elt(svg_ns, "line",
            {x1:x, x2:x, y1:0, y2:1, class:"cursor"})
        var deleter = elt(svg_ns, "circle",
            {cx:(x*100)+'%%', cy:'50%%', r:0.3, class:"deleter", onclick:"del(this)"})
        var letter = elt(svg_ns, "text",
            {x:(x*100)+'%%', y:'80%%', 'text-anchor':'middle', 'class':'letter'})
        document.getElementById("cursors").appendChild(cursor)
        document.getElementById("deleters").appendChild(deleter)
        document.getElementById("letters").appendChild(letter)
        deleter.related = [deleter, cursor, letter]
        re_letter()
    }
  
    function del(deleter) {
        for (var i in deleter.related) {
            e = deleter.related[i]
            e.parentNode.removeChild(e)
        }
        re_letter()
    }

    function pos(e) {
        return Number(e.getAttribute('x').replace('%%',''))
    }

    function re_letter() {
        console.log('re_letter')
        ls = []
        letters = document.getElementById("letters")
        for (var i=0; i<letters.children.length; i++) {
            child = letters.children[i]
            if (child.classList.contains('letter')) {
                console.log(child.getAttribute('x') + ' ' + child.innerHTML)
                ls.push(child)
            }
        }
        ls = ls.sort(function(a,b) {return pos(a)-pos(b)})
        for (var i in ls)
            ls[i].innerHTML = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijlkmnopqrstuvwxyz'[i]
    }
'''

def cursors_html(width, tmin, tmax, ticks):

    elt('svg', {
        'id':'cursors', 'width':'%dem'%width, 'height':'100%', 'viewBox':'0 0 1 1',
        'preserveAspectRatio':'none', 'style':'position:absolute; background:none',
        'onmousemove':'move(this)', 'onmouseout':'out(this)',  'onclick':'add(this)'
    })
    elt('line', {'id':'lll', 'class':'cursor', 'x1':-1, 'y1':0, 'x2':-1, 'y2':1})
    end('svg')

    elt('div', {'style':'position:relative; z-index:1000; background:white; margin-bottom:0.3em'})
    eltend('svg', {'id':'letters', 'width':'%dem'%width, 'height':'1em'})
    h = 0.8
    viewBox = '0 0 %g %g' % (width, h)
    put('<br/>')
    eltend('svg', {'id':'deleters', 'width':'%gem'%width, 'height':'%gem'%h, 'viewBox':viewBox}),
    end('div')

    labels(tmin, tmax, width, ticks, [t.strftime('%H:%M:%S') for t in ticks])



#
#
#

_style = '''
    body, table {
        font-family: sans-serif;
        font-size: 10pt;
    }
    .data {
        text-align: right;
    }
    .row-number {
        padding-right: 2em;
        text-align: right;
    }
    .name {
        text-align: left;
    }
    .graph {
        padding-left: 0em;
        padding-right: 0em;
    }
    .head {
        font-weight: bold;
    }
    .selected {
        background: rgb(240,245,255)
    }
'''
        
_script = '''

    var selected = undefined
    var last_selected = undefined

    function _desel() {
        if (selected)
            selected.classList.remove('selected')
    }

    function _sel(s) {
        if (selected) {
            last_selected = selected
            selected.classList.add('selected')
            for (var p=selected, y=0; p && p.tagName!='BODY'; p=p.offsetParent)
                y += p.offsetTop
            var h = selected.offsetHeight
            if (window.pageYOffset + window.innerHeight < y + h)
                selected.scrollIntoView(false)
            else if (y < window.pageYOffset)
                selected.scrollIntoView(true)
        }
    }

    function sel(e) {
        _desel()
        if (selected!=e) {
            selected = e
            _sel()
        } else {
            selected = undefined
        }
    }

    function re_number() {
        n = 0
        row = document.getElementById("table").firstChild.firstChild    
        while (row) {
            td = row.firstChild
            while (td && !td.classList.contains("row-number"))
                td = td.nextSibling            
            if (!td)
                return
            if (!td.classList.contains("head")) {
                td.innerHTML = n
                n += 1
            }
            row = row.nextSibling
        }
    }

    function set_level(c) {
        _desel()
        c = String(c)
        row = document.getElementById("table").firstChild.firstChild    
        while (row) {
            row_level = row.getAttribute('_level')
            if (row_level <= c) {
                row.style.display = ''
            } else {
                row.style.display = 'none'
            }
            row = row.nextSibling
        }
        document.getElementById("current_level").innerHTML = c
        selected = next_visible(selected)
        
    }

    function initial_level(c) {
        if (!document.getElementById("current_level").innerHTML)
            set_level(c)
    }

    function next_visible(row) {
        while (row && row.style.display=='none')
            row = row.nextSibling
        return row            
    }

    function prev_visible(row) {
        while (row!=first_row && row.style.display=='none')
            row = row.previousSibling
        return row            
    }

    function key() {
        var evt = window.event
        var c = String.fromCharCode(evt.charCode)
        first_row = document.getElementById("table").firstChild.firstChild
        while (first_row && !first_row.classList.contains('row'))
            first_row = first_row.nextSibling
        first_row = next_visible(first_row)
        if (!last_selected) {
            for (var r = first_row; r && !selected; r = r.nextSibling) {
                if (r.classList.contains('selected'))
                   selected = r
            }
            last_selected = selected
        }
        if (!last_selected)       
            last_selected = first_row
        if (c=='s') {
            if (confirm('Save?')) {
                req = new XMLHttpRequest()
                req.open('PUT', '')
                req.send(document)
                alert('Saved')
            }
        } else if (c=='') {
            if (!selected)
                selected = last_selected
            else {
                var s = next_visible(selected.nextSibling)
                if (s) {
                    _desel()
                    selected = s
                }
            }
        } else if (c=='') {
            if (!selected)
                selected = last_selected
            else if (selected != first_row) {
                selected.classList.remove('selected')
                selected = prev_visible(selected.previousSibling)
            }
        } else if (c=='n') {
            if (selected) {
                next = next_visible(selected.nextSibling)
                if (next) {
                    parent = selected.parentNode
                    parent.removeChild(selected)
                    parent.insertBefore(selected, next.nextSibling)
                    re_number()
                }
            }
        } else if (c=='p') {
            if (selected) {
                if (selected!=first_row) {
                    prev = prev_visible(selected.previousSibling)
                    parent = selected.parentNode
                    parent.removeChild(selected)
                    parent.insertBefore(selected, prev)
                    re_number()
                }
            }
        } else if (c=='N') {
            if (selected) {
                s = next_visible(selected.nextSibling)
                if (s) {
                    parent = selected.parentNode
                    parent.removeChild(selected)
                    parent.insertBefore(selected, null)
                    sel(s)
                    re_number()
                }
            }
        } else if (c=='P') {
            if (selected && selected != first_row) {
                s = prev_visible(selected.previousSibling)
                parent = selected.parentNode
                parent.removeChild(selected)
                parent.insertBefore(selected, first_row)
                sel(s)
                re_number()
            }
        } else if ('1'<=c && c<='9') {
            set_level(c)
        }
        _sel(selected)
    }    

    function toggle_help() {
        e = document.getElementById('help')
        if (e.style.display == 'none') {
            e.style.display = 'block'
        } else {
            e.style.display = 'none'
        }
    }

'''

_help = '''
click on a graph to put down a cursor line
click on a blue disk to delete a cursor
click on a name to select a row
^N select the next row 
^P select the previous row 
n move the selected row down 
p move the selected row up 
N move the selected row to the bottom 
P move the selected row to the top 
'''.strip().replace('\n', '<br/>')


#
#
#

def td(cls, *content):
    elt('td', {'class':cls})
    if content:
        put(*content)
        end('td')

def main():

    p = argparse.ArgumentParser()
    p.add_argument('--dbg', '-d', action='store_true')
    p.add_argument(dest='specs', nargs='*')
    #p.add_argument('--descriptor-file', '-f', default=None)
    p.add_argument('--width', type=float, default=30)
    p.add_argument('--height', type=float, default=1.8)
    p.add_argument('--show-empty', action='store_true')
    p.add_argument('--show-zero', action='store_true')
    #p.add_argument('--no-shade', action='store_true')
    p.add_argument('--no-merges', action='store_false', dest='merges')
    p.add_argument('--number-rows', action='store_true')
    p.add_argument('--duration', type=float, default=None)
    p.add_argument('--after')
    p.add_argument('--before')
    p.add_argument('--every', type=float)
    p.add_argument('--relative', action='store_true')
    p.add_argument('--list', action='store_true')
    p.add_argument('--level', type=int, default=1)
    p.add_argument('--bins', type=int, default=25)
    p.add_argument('--progress-every', type=int, default=10000)

    global opt
    opt = p.parse_args()

    # just list?
    if opt.list:
        for desc in sorted(descriptors, key=lambda desc: desc['name'].lower()):
            d = collections.defaultdict(lambda: '...')
            d.update(desc)
            msg(get(d, 'name'))
        return

    # get our graphs
    graphs = get_graphs(opt.specs, opt)
    if not graphs:
        msg('no series specified')
        return
    try:
        tmin = min(s.tmin for g in graphs for s in g if s.tmin)
        tmax = max(s.tmax for g in graphs for s in g if s.tmax)
        tspan = float((tmax-tmin).total_seconds())
    except ValueError:
        msg('no data found')
        return

    # stats
    spec_matches = collections.defaultdict(int)
    for graph in graphs:
        for series in graph:
            spec_matches[series.spec] += 1
    spec_empty = collections.defaultdict(int)
    spec_zero = collections.defaultdict(int)

    msg('start:', tmin)
    msg('finish:', tmax)
    msg('duration:', tmax - tmin)
    if opt.duration: # in seconds
        tmax = tmin + timedelta(0, opt.duration)

    # compute ticks
    ranges = [1, 2.5, 5, 10, 15, 20, 30, 60] # seconds
    ranges += [r*60 for r in ranges] # minutes
    ranges += [r*3600 for r in 1, 2, 3, 4, 6, 8, 12, 24] # hours
    nticks = int(opt.width / 5)
    if nticks<1: nticks = 1
    tickdelta = tspan / nticks
    for r in ranges:
        if tickdelta<r:
            tickdelta = r
            break
    tickmin = t0 + timedelta(0, math.ceil((tmin-t0).total_seconds()/tickdelta)*tickdelta)
    tickdelta = timedelta(0, tickdelta)
    ticks = []
    for i in range(nticks+1):
        t = tickmin + i * tickdelta
        if t > tmax: break
        ticks.append(t)

    def _graph(data=[], ymax=None):
        html_graph(data=data,
              tmin=tmin, tmax=tmax, width=opt.width,
              ymin=0, ymax=ymax, height=opt.height,
              #ticks=ticks, shaded=not opt.no_shade and len(data)==1)
              ticks=ticks, shaded=len(data)==1, bins=opt.bins)

    elt('html')
    elt('head')
    elt('meta', {'charset':'utf-8'})
    elt('style')
    put(graph_style)
    put(cursors_style)
    put(_style)
    end('style')
    elt('script')
    put(cursors_script % opt.width)
    put(_script)
    end('script')
    end('head')
    elt('body', {'onkeypress':'key()', 'onload':'initial_level(%d)'%opt.level})

    elt('div', {'onclick':'toggle_help()'})
    put('1-9 to choose detail level; current level: <span id="current_level"></span><br/>')
    put('click to toggle more help')
    eltend('div', {'id':'help', 'style':'display:none'}, _help)
    end('div')
    put('</br>')

    elt('table', {'id':'table', 'style':'position:relative;'})
    elt('tr')
    td('head data', 'avg')
    td('head data', 'max')
    elt('td')
    cursors_html(opt.width, tmin, tmax, ticks)
    end('td')
    if opt.number_rows:
        td('head row-number', 'row')
    td('head desc', 'name')
    end('tr')

    colors = ['rgb(50,102,204)','rgb(220,57,24)','rgb(253,153,39)','rgb(20,150,24)',
              'rgb(153,20,153)', 'rgb(200,200,200)']

    def color(i):
        return colors[i] if i <len(colors) else 'black'

    def name_td(g):
        td('name')
        pfx = os.path.commonprefix([s.name for s in g])
        sfx = os.path.commonprefix([s.name[::-1] for s in g])[::-1]
        put(pfx)
        if sfx != pfx:
            for i,s in enumerate(g):
                mid = ' ' + s.name[len(pfx):len(s.name)-len(sfx)]
                eltend('span', {'style':'color:%s' % color(i)}, mid)
            put(sfx)
        end('td')

    row = 0
    for graph in sorted(graphs, key=lambda g: g[0].key):
        graph.sort(key=lambda s: s.key)
        ymin = min(s.ymin for s in graph)
        ymax = max(s.ymax for s in graph)
        ysum = sum(s.ysum for s in graph)
        ylen = sum(len(s.ys) for s in graph)
        display_ymax = max(s.display_ymax for s in graph)
        if ylen:
            if ymax!=0 or ymin!=0 or opt.show_zero:
                elt('tr', {'onclick':'sel(this)', 'class':'row', '_level':graph[0].level})
                td('data', '{:,.3f}'.format(float(ysum)/ylen))
                td('data', '{:,.3f}'.format(ymax))
                td('graph')
                graph_color = lambda graph, i: color(i) if len(graph)>1 else 'black'
                data = [(s.ts, s.ys, graph_color(graph,i)) for i,s in enumerate(graph)]
                _graph(data, display_ymax)
                end('td')
                if opt.number_rows:
                    td('row-number', str(row))
                    row += 1
                name_td(graph)
                end('tr')
            else:
                dbg('skipping uniformly zero data for', graph[0].get('name'), 'in', graph[0].fn)
                for s in graph:
                    spec_zero[s.spec] += 1
        elif opt.show_empty:
            elt('tr', {'onclick':'sel(this)', 'class':'row', '_level':graph[0].level})
            td('data', 'n/a')
            td('data', 'n/a')
            td('graph')
            _graph()
            end('td')
            if opt.number_rows:
                td('row-number', str(row))
                row += 1
            name_td(graph)
            end('tr')
        else:
            dbg('no data for', graph[0].get('name'), 'in', graph[0].fn)
            for s in graph:
                spec_empty[s.spec] += 1

    end('table')
    end('body')
    end('html')

    for spec in opt.specs:
        msg('spec', repr(spec), 'matched:', spec_matches[spec],
            'zero:', spec_zero[spec], 'empty:', spec_empty[spec])


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
    parse_type = 're'
)


#
# generic csv
#

descriptor(
    name = 'csv {fn}: {field_name}',
    parse_type = 'csv',
    file_type = 'text',
    field_name = '(?P<field_name>.*)',
    split_field = 'field_name'
)

#
# windows csv - special header processing
#

def win_headers(series, headers):
    tz = headers[0].split('(')[3].strip(')')
    tz = timedelta(hours = -float(tz)/60)
    for s in series:
        s.tz = tz
    return [' '.join(h.split('\\')[3:]) for h in headers]

descriptor(
    name = 'win {fn}: {field_name}',
    parse_type = 'csv',
    file_type = 'text',
    field_name = '(?P<field_name>.*)',
    split_field = 'field_name',
    process_headers = win_headers
)

#
# json test
#

descriptor(
    file_type = 'json',
    parse_type = 'json',
    name = 'test1',
    json_fields = {
        'data': ['foo', 'bar1'],
        'time': ['jtime'],
    },
)

descriptor(
    file_type = 'json',
    parse_type = 'json',
    name = 'test2',
    json_fields = {
        'data': ['foo', 'bar2'],
        'time': ['jtime'],
    },
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
        parse_type = 'json',
        name = name,
        json_fields = {
            'data': json_data,
            'time': ['localTime'],
        },
        scale = scale,
        rate = rate,
        level = level,
        **kwargs
    )

    # for parsing serverStatus section of ftdc
    descriptor(
        file_type = 'json',
        parse_type = 'ftdc',
        name = 'ftdc ' + name,
        json_fields = {
            'data': json_data,
            'time': ['localTime'],
        },
        scale = scale,
        rate = rate,
        level = level,
        **kwargs
    )

def ss_opcounter(opcounter, **kwargs):
    ss(
        json_data = ['opcounters', opcounter],
        merge = 'ss_opcounters',
        name = 'ss opcounters: ' + opcounter,
        level = 1,
        rate = True,
        **kwargs
    )
    ss(
        json_data = ['opcountersRepl', opcounter],
        merge = 'ss_opcounters_repl',
        name = 'ss opcounters repl: ' + opcounter,
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
ss(["connections", "totalCreated"], name="ss connections: created", level=3, rate=True)
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

# XXX make these auto-split instead of listing explicitly
def ss_command(command, level=4):
    ss(["metrics", "commands", command, "total"], rate=True, level=level)
    ss(["metrics", "commands", command, "failed"], rate=True, level=level)

ss_command("collStats")
ss_command("count")
ss_command("createIndexes")
ss_command("drop")
ss_command("getnonce")
ss_command("insert")
ss_command("isMaster")
ss_command("ping")
ss_command("serverStatus")
ss_command("update")
ss_command("whatsmyuri")
ss_command('<UNKNOWN>')
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


#
# replica set status
# do special-case computation of repl set lag here to produce a sequence of samples
# then delegate to the generic series_process_fields
#

def series_process_rs(series, opt):

    # delegate to generic field processor
    p = init_dst(series_process_fields(series, opt))

    # compute and send headers
    jnode = yield
    headers = ['time']
    for m in jnode['members']:
        name = m['name']
        for s in ['state', 'lag']:
            headers.append(name + ' ' + s)
    p.send(headers)

    while True:

        # next json doc
        jnode = yield

        # compute primary_optime
        primary_optime = None
        for m in jnode['members']:
            if m['stateStr'] == 'PRIMARY':
                primary_optime = m['optime']['t']
                break

        # compute result fields
        result = [jnode['date']]
        for m in jnode['members']:
            result.append(m['state'])
            result.append(primary_optime - m['optime']['t'])

        # send result to field processor
        p.send(result)

def series_read_rs(fn, series, opt):
    transfer(read_json(fn, opt), series_process_rs(series, opt))

descriptor(
    name = 'rs: {field_name}',
    parse_type = 'rs',
    file_type = 'json',
    field_name = '(?P<field_name>.*)',
    split_field = 'field_name'
)

descriptor(
    name = 'ftdc rs: {field_name}',
    parse_type = 'ftdc',
    file_type = 'json',
    field_name = '(?P<field_name>.*)',
    split_field = 'field_name'
)


#
# ftdc processing
# demultiplex the embedded streams:
#     series_process_json processes serverStatus
#     series_process_rs does special-case processing (e.g. replica lag) for replSetGetStatus
#

def series_read_ftdc(fn, series, opt):
    ss = init_dst(series_process_json(fn, series, opt))
    rs = init_dst(series_process_rs(series, opt))
    for jnode in read_json(fn, opt):
        ss.send(jnode['serverStatus'])
        rs.send(jnode['replSetGetStatus'])

    #dst = [series_process_json(fn, series, opt), series_process_rs(series, opt)]
    #transfer(read_json(fn, opt), *dst)


#
#
#


def cs(json_data, name=None, scale=1, rate=False, units=None, level=3, **kwargs):
    if not name:
        if json_data[0]=='wiredTiger':
            name = 'cs wt: ' + ' '.join(json_data[1:])
        else:
            name = 'cs: ' + ' '.join(json_data)
    if not units: units = desc_units(scale, rate)
    if units: units = ' (' + units + ')'
    name = name + units
    descriptor(
        file_type = 'json',
        parse_type = 'json',
        name = name,
        json_fields = {
            'data': json_data,
            'time': ['time'],
        },
        scale = scale,
        rate = rate,
        level = level,
        **kwargs
    )

cs(["capped"], level=99)
cs(["count"], level=1)
cs(["nindexes"], level=9)
cs(["ns"], level=99)
cs(["ok"], level=99)
cs(["size"], scale=MB, level=1)
cs(["storageSize"], scale=MB, level=1)
cs(["totalIndexSize"], scale=MB, level=1)
cs(["avgObjSize"], level=1)
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
# sysmon.py
#

def sysmon_cpu(which, **kwargs):
    descriptor(
        name = 'sysmon cpu: %s (%%)' % which,
        parse_type = 'csv',
        file_type = 'text',
        field_name = 'cpu_%s' % which,
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
        parse_type = 'csv',
        file_type = 'text',
        field_name = '%s' % which,
        **kwargs
    )

stat('ctxt', name='context switches (/s)', rate=True)
#stat('btime')
stat('processes')
stat('running')
stat('procs_blocked')

def sysmon_disk(which, desc, **kwargs):
    if not 'rate' in kwargs: kwargs['rate'] = True
    descriptor(
        name = 'sysmon disk: {disk} %s' % desc,
        parse_type = 'csv',
        file_type = 'text',
        field_name = '(?P<disk>.*)\.%s' % which,
        split_field = 'disk',
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

iostat_time_re = '(?P<time>^../../..(?:..)? ..:..:..(?: ..)?)'
iostat_cpu_re = '(?:^ *(?P<user>[0-9\.]+) +(?P<nice>[0-9\.]+) +(?P<system>[0-9\.]+) +(?P<iowait>[0-9\.]+) +(?P<steal>[0-9\.]+) +(?P<idle>[0-9\.]+))'
iostat_disk_re = '(?:^(?P<iostat_disk>[a-z]+) +(?P<rrqms>[0-9\.]+) +(?P<wrqms>[0-9\.]+) +(?P<rs>[0-9\.]+) +(?P<ws>[0-9\.]+) +(?P<rkBs>[0-9\.]+) +(?P<wkBs>[0-9\.]+) +(?P<avgrqsz>[0-9\.]+) +(?P<avgqusz>[0-9\.]+) +(?P<await>[0-9\.]+) +(?P<r_await>[0-9\.]+)? +(?P<w_await>[0-9\.]+)? +(?P<svctime>[0-9\.]+) +(?P<util>[0-9\.]+))'

def iostat(**kwargs):
    descriptor(
        file_type = 'text',
        parse_type = 're',
        re = '|'.join([iostat_time_re, iostat_cpu_re, iostat_disk_re]),
        re_time = 'time',
        **kwargs
    )

def iostat_cpu(re_data, **kwargs):
    iostat(
        re_data = re_data,
        name = 'iostat cpu: {re_data} (%)',
        ymax = 100,
        **kwargs
    )

iostat_cpu('user', merge = 'iostat_cpu')
iostat_cpu('system', merge = 'iostat_cpu')
iostat_cpu('iowait', merge = 'iostat_cpu')
iostat_cpu('nice', merge = 'iostat_cpu')
iostat_cpu('steal', merge = 'iostat_cpu')
iostat_cpu('idle', level = 3)

def iostat_disk(re_data, name, level=3, **kwargs):
    iostat(
        re_data = re_data,
        split_field = 'iostat_disk',
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
#
#




#
# mongod log
#

def mongod(**kwargs):
    kwargs['re'] = '^(....-..-..T..:..:..\....(?:[+-]....|Z))' + kwargs['re']
    kwargs['file_type'] = 'text'
    kwargs['parse_type'] = 're'
    descriptor(**kwargs)

mongod(
    name = 'mongod max logged op (ms) per {bucket_size}s',
    re = '.* (?:query:|command:) .* ([0-9]+)ms$',
    bucket_op = 'max',
    bucket_size = 1, # size of buckets in seconds
    level = 1
)

mongod(
    name = 'mongod logged ops longer than {count_min}ms per {bucket_size}s',
    re = '.* (?:query:|command:) .* ([0-9]+)ms$',
    bucket_op = 'count',
    bucket_size = 1,    # size of buckets in seconds
    count_min = 0,      # minimum query duration to count',
    level = 1
)

# not working right it seems?
#mongod(
#    name = 'mongod queued queries longer than {queue_min_ms}ms',
#    re = '.* query: .* ([0-9]+)ms$',
#    queue = True,
#    queue_min_ms = 0,  # minimum op duration to count for queue',
#    level = 3
#)

mongod(
    name = 'mongod: waiting to acquire lock per {bucket_size}s',
    re = '.* has been waiting to acquire lock for more than (30) seconds',
    bucket_op = 'count',
    bucket_size = 1,  # size of buckets in seconds
    level = 1
)

#
# oplog, e.g.
# mongo --eval 'db.oplog.rs.find({...}, {ts:1, op:1, ns:1}).forEach(function(d) {print(JSON.stringify(d))})
#

descriptor(
    name = 'oplog: {op} {ns}',
    file_type = 'json',
    parse_type = 'json',
    json_fields = {
        'time': ['ts', 't'],
        'data': ['op'],
        'op': ['op'],
        'ns': ['ns'],
    },
    bucket_op = 'count',
    bucket_size = 1,
    split_field = ('op', 'ns'),
    level = 1
)


#
# wt
#

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

    # for parsing wt data in json format ss files
    descriptor(
        file_type = 'json',
        parse_type = 'json',
        json_fields = {
            'time': ['localTime'],
            'data': ['wiredTiger', wt_cat, wt_name],
        },
        name = 'ss ' + name,
        **kwargs
    )

    # for parsing wt data in serverStatus section of ftdc output
    descriptor(
        file_type = 'json',
        parse_type = 'ftdc',
        json_fields = {
            'time': ['localTime'],
            'data': ['wiredTiger', wt_cat, wt_name],
        },
        name = 'ftdc ss ' + name,
        **kwargs
    )

    # for parsing wt data in json re format wtstats files
    descriptor(
        file_type = 'text',
        parse_type = 're',
        re = '^(... .. ..:..:..) ([0-9]+) .* {}: {}'.format(wt_cat, wt_name),
        name = name,
        **kwargs
    )


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
wt('cache', 'in-memory page splits', rate=True) # CHECK
wt('cache', 'internal pages evicted', rate=True)
wt('cache', 'maximum bytes configured', scale=MB)
wt('cache', 'maximum page size at eviction', scale=MB) # CHECK rc5
wt('cache', 'modified pages evicted', rate=True)
wt('cache', 'overflow pages read into cache', rate=True)
wt('cache', 'overflow values cached in memory')
wt('cache', 'page split during eviction deepened the tree', rate=True)
wt('cache', 'pages currently held in the cache')
wt('cache', 'pages evicted because they exceeded the in-memory maximum', rate=True)
wt('cache', 'pages evicted because they had chains of deleted items', rate=True) # CHECK rc5
wt('cache', 'pages evicted by application threads', rate=True) # CHECK
wt('cache', 'pages read into cache', merge = 'wt_cache_pages_cache', rate=True)
wt('cache', 'pages selected for eviction unable to be evicted', rate=True)
wt('cache', 'pages split during eviction', rate=True)
wt('cache', 'pages walked for eviction', rate=True)
wt('cache', 'pages written from cache', merge = 'wt_cache_pages_cache', rate=True)
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
wt('data-handle', 'connection dhandles swept', rate=True) # CHECK
wt('data-handle', 'connection sweeps', rate=True) # CHECK
wt('data-handle', 'connection time-of-death sets', rate=True) # CHECK
wt('data-handle', 'session dhandles swept', rate=True)
wt('data-handle', 'session sweep attempts', rate=True)
wt('log', 'consolidated slot closures', rate=True, set_field='slot_closure_rate')
wt('log', 'consolidated slot join races', rate=True)
wt('log', 'consolidated slot join transitions', rate=True)
wt('log', 'consolidated slot joins', rate=True)
wt('log', 'consolidated slot joins', rate=True, name='joins per closure', scale_field='slot_closure_rate')
wt('log', 'failed to find a slot large enough for record', rate=True)
wt('log', 'log buffer size increases', rate=True)
wt('log', 'log bytes of payload data', scale=MB, rate=True)
wt('log', 'log bytes written', scale=MB, rate=True, level=2)
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
wt('log', 'pre-allocated log files prepared', rate=True) # CHECK
wt('log', 'pre-allocated log files used', rate=True) # CHECK
wt('log', 'record size exceeded maximum', rate=True)
wt('log', 'records processed by log scan', rate=True)
wt('log', 'slots selected for switching that were unavailable', rate=True)
wt('log', 'total in-memory size of compressed records', scale=MB) # CHECK
wt('log', 'total log buffer size', scale=MB)
wt('log', 'total size of compressed records', scale=MB) # CHECK
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
wt('transaction', 'transactions committed', rate=True, level=2)
wt('transaction', 'transactions rolled back', rate=True, level=2)
wt('transaction', 'update conflicts', rate=True, level=2)

ss(['wiredTiger', 'uri'], level=99)





#
#
#

if __name__ == '__main__':
    main()
