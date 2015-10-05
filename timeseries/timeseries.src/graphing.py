import collections
import datetime as dt
import dateutil
import json
import math
import os
import re
import string
import time

import descriptors
import flow
import util


#
#
#

xpad = 1.5
ypad = 0.1

def html_graph(
    data=[],
    tmin=None, tmax=None, width=None,
    ymin=None, ymax=None, height=None,
    ticks=None, line_width=0.1, shaded=True,
    bins=0
):

    flow.elt('svg', {
        'width':'%gem' % width,
        'height':'%gem' % height,
        'viewBox':'%g %g %g %g' % (0, 0, width, height)
    })

    for ts, ys, color in data:

        if not ts:
            continue

        tspan = tmax - tmin
        yspan = float(ymax - ymin)
        if yspan==0:
            if ymin==0:
                yspan = 1
            else:
                ymin -= 1
                yspan = 1

        dt = lambda t: t - tmin
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
                flow.eltend('polygon', {'points':points, 'class':cls})
            flow.eltend('polyline', {'points':line, 'class':'curve', 'style':'stroke:%s'%color})

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
                flow.eltend('polygon', {'points':points, 'class':'shaded'})
            line += ' ' + ' '.join(r'%g,%g' % (gx(bt(i)), gy(ymaxs[i])) for i in bis)
            style = 'stroke:%s; fill:%s; stroke-width:0.7' % (color, color)
            flow.eltend('polyline', {'points':line, 'class':'curve', 'style':style})


    if data and ticks:
        if type(ticks)==int:
            ticks = [tmin + (tmax-tmin)*i/ticks for i in range(ticks+1)]
        for t in ticks:
            x = gx(dt(t))
            flow.eltend('line', {'x1':x, 'x2':x, 'y1':0, 'y2':height, 'class':'tick'})

    flow.end('svg')

def labels(tmin, tmax, width, height, ts, labels):
    flow.elt('div', {'style':'height: %fem; position:relative; width:%gem' % (height,width)})
    tspan = tmax - tmin
    gx = lambda t: (t-tmin) / tspan * (width-2*xpad) + xpad
    for t, label in zip(ts, labels):
        style = 'left:{x}em; position:absolute; width:100em'.format(x=gx(t)-50)
        flow.elt('span', {'align':'center', 'style':style})
        flow.eltend('div', {'align':'center', 'style':'font-size:80%'}, label)
        flow.end('span')
    flow.end('div')

# x is a relative position (0-1) within the graphing area, which includes xpad on either side
# compute the corresponding time on the graph, given tmin and tmax for the graph itself
def time_for(x, width, tmin, tmax):
    return tmin + ((x * (width + 2*xpad) - xpad) / width) * (tmax - tmin)

#
#
#

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

    def __init__(self, spec, descriptor, params, fn, spec_ord, tag, opt=None):

        self.spec = spec
        self.descriptor = dict(descriptor)
        self.descriptor.update(params)
        self.spec_ord = spec_ord
        self.tag = tag
        self.opt = opt
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

        # info for dict-based file formats, like ftdc metrics
        self.dict_fields = self.get('dict_fields', None)

        # special csv header processing
        self.process_headers = self.get('process_headers', lambda series, headers: headers)

        # timezone offset
        tz = self.get('tz', None)
        if tz==None:
            self.tz = dt.datetime(*time.gmtime()[:6]) - dt.datetime(*time.localtime()[:6])
        else:
            self.tz = dt.timedelta(hours=float(tz))

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

        # allow for per-series every
        self.every = self.get('every', self.opt.every) if self.opt else None

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
                util.dbg('wrap', d, self.last_d, self.wrap_offset)
            elif self.last_d < -self.wrap/2 and d > self.wrap/2:
                self.wrap_offset -= 2 * self.wrap
                util.dbg('wrap', d, self.last_d, self.wrap_offset)
            self.last_d = d
            d += self.wrap_offset

        # compute a rate
        if self.rate:
            if self.last_t==t:
                return
            if self.last_t:
                dd = d - self.last_d
                if self.rate != 'delta':
                    dd /= t - self.last_t
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
            tt = t
            s0 = t
            s1 = s0 // self.buckets * self.buckets
            t = s1
            self.ys[t] = self.op(self.ys, t, d)
        elif self.queue:
            if d>self.queue_min_ms:
                ms = dt.timedelta(0, d/1000.0)
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
            new = Series(self.spec, self.descriptor, {}, self.fn, self.spec_ord, self.tag, self.opt)
            if self.split_field: # this is getting a little creaky - generalize? move up into data_point?
                if type(self.split_field)==str:
                    new.descriptor[self.split_field] = split_key
                else:
                    for name, value in zip(self.split_field, split_key):
                        new.descriptor[name] = value
                new.key = (self.tag, descriptors.split_ords[self.split_field], split_key, new.key)
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
                n = int(math.ceil((tmax-tmin) / self.buckets))
                dt = self.buckets
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
    util.dbg(spec_name, params, fn)

    # ignore punctuation, 
    def words(s):
        #return re.split('\W+', s.lower())
        return re.sub('[^a-zA-Z0-9]', ' ', s).lower().split()

    def is_metrics(fn):
        if os.path.isdir(fn):
            return any(is_metrics(f) for f in os.listdir(fn))
        else:
            return os.path.basename(fn).startswith('metrics.')

    def detect(fn):
        if is_metrics(fn):
            return 'metrics'
        with open(fn) as f:
            for i in range(10):
                try:
                    json.loads(f.next())
                    return 'json'
                except Exception as e:
                    util.dbg(e)
                    pass
        return 'text'

    file_type = detect(fn)
    util.msg('detected type of', fn, 'as', file_type)

    # find matching descriptors
    scored = collections.defaultdict(list)
    spec_name_words = words(spec_name)
    for desc in descriptors.descriptors:
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
    series = [Series(spec, desc, params, fn, spec_ord, tag, opt) for desc in best_descs]

    # no match?
    if not series:
        util.msg('no descriptors match', spec_name)

    return series


