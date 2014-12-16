import argparse
import collections
import dateutil.parser
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
        sys.stdout.write(' %s="%s"' % (a.strip('_'), attrs[a]))
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
    .shade {
        fill: rgb(230,230,230);
        stroke: rgb(230,230,230);
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
    .tick {
        stroke: rgba(0,0,0,0.08);
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
'''

x_pad = 1.5
y_pad = 0.1

def graph(
    data=[],
    tmin=None, tmax=None, width=None,
    ymin=None, ymax=None, height=None,
    ticks=None, line_width=0.1, shaded=True
):
    elt('svg', {
        'width':'%gem' % width,
        'height':'%gem' % height,
        'viewBox':'%g %g %g %g' % (0, 0, width, height)
    })
    for ts, ys, color in data:
        tspan = float((tmax-tmin).total_seconds())
        yspan = float(ymax - ymin)
        if yspan==0:
            if ymin==0:
                yspan = 1
            else:
                ymin -= 1
                yspan = 1
        gx = lambda t: (t-tmin).total_seconds() / tspan * (width-2*x_pad) + x_pad
        gy = lambda y: ((1 - (y-ymin) / yspan) * (1-2*y_pad) + y_pad) * height
        line = ' '.join('%g,%g' % (gx(t), gy(ys[t])) for t in ts)
        if shaded:
            left = '%g,%g' % (gx(ts[0]), gy(0))
            right = '%g,%g' % (gx(ts[-1]), gy(0))
            points = left + ' ' + line + ' ' + right
            eltend('polygon', {'points':points, 'class':'shade'})
        eltend('polyline', {'points':line, 'class':'curve', 'style':'stroke:%s'%color})
    if data and ticks:
        if type(ticks)==int:
            ticks = [tmin + (tmax-tmin)*i/ticks for i in range(ticks+1)]
        for t in ticks:
            x = gx(t)
            eltend('line', {'x1':x, 'x2':x, 'y1':0, 'y2':height, 'class':'tick'})
    end('svg')

def labels(tmin, tmax, width, ts, labels):
    elt('div', {'style':'height: 1.1em; position:relative; width:%gem' % width})
    tspan = float((tmax-tmin).total_seconds())
    gx = lambda t: (t-tmin).total_seconds() / tspan * (width-2*x_pad) + x_pad
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

class Series:

    def __init__(self, spec, fmt, params, fn, spec_ord):

        self.spec = spec
        self.fmt = dict(fmt)
        self.fmt.update(params)
        self.fn = fn
        self.spec_ord = spec_ord
        self.key = (fmt['_ord'], spec_ord)

        # compute delta (/s) 
        self.delta = get(self.fmt, 'delta', False)
        if self.delta:
            self.last_t = None
    
        # request to bucketize the data
        self.buckets = float(get(self.fmt, 'bucket_size', 0))
        if self.buckets:
            self.op = op_for(self.fmt, get(self.fmt, 'bucket_op', 'max'))
    
        # compute queued ops from op execution time
        self.queue = get(self.fmt, 'queue', False)
        if self.queue:
            self.queue_times = []
            self.queue_min_ms = float(get(self.fmt, 'queue_min_ms', 0))
    
        # scale the data (divide by this)
        self.scale = get(self.fmt, 'scale', 1)
    
        # requested ymax
        self.spec_ymax = float(get(self.fmt, 'ymax', '-inf'))

        # initially empty timeseries data
        self.ts = []
        self.ys = collections.defaultdict(int)
    
        # re, json, ...
        self.type = get(self.fmt, 'type', 're')

        # info for re-format files
        if self.type=='re':
            self.re = get(self.fmt, 're', None)
            if self.re and re.compile(self.re).groups==0:
                raise Exception('re ' + self.re + ' does not have any groups')
            self.re_time = get(self.fmt, 're_time', 0)
            self.re_data = get(self.fmt, 're_data', 1)

        # info for json-format files
        if self.type=='json':
            self.json_time = get(self.fmt, 'json_time', None)
            self.json_data = get(self.fmt, 'json_data', None)

        # timezone offset
        tz = get(self.fmt, 'tz', None)
        if tz==None:
            self.tz = datetime(*time.gmtime()[:6]) - datetime(*time.localtime()[:6])
        else:
            self.tz = timedelta(hours=float(tz))

        # all graphs in a ygroup will be plotted with a common display_ymax
        self.ygroup = get(self.fmt, 'ygroup', id(self))

        # which output graph this series will be plotted on
        self.graph = id(self) # will update with fmt['merge'] later so can use split key

        # split into multiple series based on a data value
        self.split_field = get(self.fmt, 'split', None)
        self.split_series = {}

        # hack to account for wrapping data
        self.wrap = get(self.fmt, 'wrap', None)
        self.wrap_offset = 0
        self.last_d = 0


    def get_split(self, split_key):
        if split_key not in self.split_series:
            new = Series(self.spec, self.fmt, {}, self.fn, self.spec_ord)
            new.fmt[self.split_field] = split_key # make split key available for formatting
            new.split_field = None
            new.key = (split_ords[self.split_field], split_key, new.key)
            self.split_series[split_key] = new
        return self.split_series[split_key]

    def get_graphs(self, graphs, ygroups, opt):
        if not self.split_field:
            # do self.graph and .name late so they can use split key
            if opt.merges:
                merge = get(self.fmt, 'merge', None)
                if merge: self.graph = merge
            self.name = get(self.fmt, 'name')
            graphs[self.graph].append(self)
            ygroups[self.ygroup].append(self)
        else:
            for s in self.split_series.values():
                s.get_graphs(graphs, ygroups, opt)

    def _data_point(self, t, d):
        d = float(d)
        if self.wrap:
            if self.last_d > self.wrap/2 and d < -self.wrap/2:
                self.wrap_offset += 2 * self.wrap
                dbg('wrap', d, self.last_d, self.wrap_offset)
            elif self.last_d < -self.wrap/2 and d > self.wrap/2:
                self.wrap_offset -= 2 * self.wrap
                dbg('wrap', d, self.last_d, self.wrap_offset)
            self.last_d = d
            d += self.wrap_offset
        d /= self.scale
        if self.delta:
            if self.last_t and self.last_t!=t:
                self.ts.append(t)
                self.ys[t] = (d-self.last_d) / (t-self.last_t).total_seconds()
            if not self.last_t or self.last_t!=t:
                self.last_t = t
                self.last_d = d
        elif self.buckets:
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
            self.ts.append(t)
            self.ys[t] = d

    def data_point(self, t, d, field):
        s = self.get_split(field(self.split_field)) if self.split_field else self
        s._data_point(t, d)


    def finish(self):

        if self.buckets:
            if self.ys.keys():
                tmin = min(self.ys.keys())
                tmax = max(self.ys.keys())
                n = int((tmax-tmin).total_seconds() / self.buckets)
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
    
        self.tmin = min(self.ts) if self.ts else None
        self.tmax = max(self.ts) if self.ts else None
        self.ymin = min(self.ys.values()) if self.ys else float('inf')
        self.ymax = max(self.ys.values()) if self.ys else float('-inf')
        self.ysum = sum(self.ys.values()) if self.ys else 0
    
        for s in self.split_series.values():
            s.finish()

def op_for(fmt, s):
    if s=='max': return lambda ys, t, d: max(ys[t], d)
    if s=='count':
        count_min_ms = float(fmt.get("count_min_ms", 0))
        return lambda ys, t, d: ys[t]+1 if d>=count_min_ms else ys[t]


REQUIRED = []
fmtr = string.Formatter()

def get(fmt, n, default=REQUIRED):
    v = fmt.get(n, default)
    if v is REQUIRED:
        raise Exception('missing required parameter '+repr(n)+' in '+fmt['name'])
    try:
        if (type(v)==str or type(v)==unicode):
            v = fmtr.vformat(str(v), (), fmt)
        elif type(v)==list:
            v = [fmtr.vformat(str(s), (), fmt) for s in v] # xxx recursive? dict?
    except KeyError as e:
        raise Exception('missing required parameter '+repr(e.message)+' in '+fmt['name'])
    return v


def series_spec(spec, spec_ord, opt):

    # parse helper
    def split(s, expect, err, full):
        m = re.split('([' + expect + err + '])', s, 1)
        s1, d, s2 = m if len(m)==3 else (m[0], '$', '')
        if d in err:
            msg = 'expected %s at pos %d in %s, found %s' % (expect, len(full)-len(s)+1, full, d)
            raise Exception(msg)
        return s1, d, s2

    # parse the spec
    spec_name, d, s = split(spec, '(:', ')=', spec)
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
                except:
                    pass
        return 're'

    file_type = detect(fn)
    msg('detected type of', fn, 'as', file_type)

    # find matching formats
    scored = collections.defaultdict(list)
    spec_name_words = words(spec_name)
    for fmt in formats:
        if get(fmt,'type','re') != file_type:
            continue
        fmt_name_words = words(fmt['name'])
        last_i = -1
        beginning = matched = in_order = adjacent = 0
        for w, word in enumerate(spec_name_words):
            try:
                i = fmt_name_words.index(word)
                if i==0 and w==0: beginning = 1
                matched += 1
                if i==last_i+1: adjacent += 1
                elif i>last_i: in_order += 1
                last_i = i
            except ValueError:
                pass
        score = (beginning, matched, adjacent, in_order)
        scored[score].append(fmt)
    best_score = sorted(scored.keys())[-1]
    best_fmts = scored[best_score] if best_score != (0,0,0,0) else []
    series = [Series(spec, fmt, params, fn, spec_ord) for fmt in best_fmts]

    # no match?
    if not series:
        msg('no formats match', spec_name)

    return series

def get_time(time, opt, s):
    time = dateutil.parser.parse(time)
    if not time.tzinfo:
        time = pytz.utc.localize(time-s.tz)
    if time < opt.after or time >= opt.before:
        return None
    elif opt.every:
        if time - opt.last_time < opt.every:
            return None
        else:
            opt.last_time = time
    return time

def series_read_json(fn, series, opt):

    # add a path to the path tree
    def add_path(node, path, leaf):
        head = str(path[0])
        if len(path)==1:
            node[head] = leaf
        else:
            if not head in node:
                node[head] = interior()
            add_path(node[head], path[1:], leaf)
        return node

    # construct combined path tree for all series
    # assumes 1) each path is specified only for one series and 2) all series specify same time path
    interior = collections.OrderedDict
    root = interior()
    for s in series:
        if not s.json_data: raise Exception(s.fmt['name'] + ' does not specify json_data')
        if not s.json_time: raise Exception(s.fmt['name'] + ' does not specify json_time')
        add_path(root, s.json_time, 'time') # must go first so we get a t first
        add_path(root, s.json_data, s)

    # match a path tree with a json doc
    def match(node, jline):
        for name in node:
            if name in jline:
                node_child = node[name]
                jline_child = jline[name]
                if type(node_child)==interior and type(jline_child)==dict:
                    for n, j in match(node_child, jline_child):
                        yield n, j
                elif type(node_child)!=interior and type(jline_child)!=dict:
                    yield node_child, jline_child

    # process lines
    for line in open(fn):
        time = None
        if line.startswith('{'):
            j = json.loads(line)
            for s, v in match(root, j):
                if s=='time':
                    time = v
                    time = get_time(time, opt, s)
                    if not time:
                        break
                else:
                    if not time:
                        raise Exception('time not found in ' + line)
                    s.data_point(time, v, None) # xxx splits?


def series_read_re(fn, series, opt):

    # group series by re
    series_by_re = collections.defaultdict(list)
    for s in series:
        series_by_re[s.re].append(s)

    # group res into chunks
    # Python re impl can only handle 100 groups
    # so we process the formats in chunks, constructing one chunk_re for each chunk
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
    for line in open(fn):
        line = line.strip()
        for chunk_re, chunk, chunk_groups in chunks:
            m = chunk_re.match(line)
            if m:
                #dbg(m.groups())
                for chunk_group, s_re in zip(chunk_groups, chunk):
                    def field(g):
                        try: return m.group(chunk_group+g+1) if type(g)==int else m.group(g)
                        except Exception as e: raise Exception(g + ': ' + e.message)
                    for s in series_by_re[s_re]:
                        t = field(s.re_time)
                        if t:
                            t = get_time(t, opt, s)
                            if not t:
                                continue
                        else:
                            t = last_time                            
                        if t:
                            d = field(s.re_data)
                            if d != None:
                                s.data_point(t, d, field)
                            last_time = t

formats = []     # formats loaded from various def files
split_ords = {}  # sort order for each split_key - first occurrence of split_key in def file
format_ord = 0

def format(**fmt):
    global format_ord
    fmt['_ord'] = format_ord
    if 'split' in fmt:
        split_field = fmt['split']
        if not split_field in split_ords:
            split_ords[split_field] = fmt['_ord']
    formats.append(fmt)
    format_ord += 1


def series_all(specs, opt):

    if not hasattr(opt, 'after') or not opt.after: opt.after = pytz.utc.localize(datetime.min)
    if not hasattr(opt, 'before') or not opt.before: opt.before = pytz.utc.localize(datetime.max)
    if not hasattr(opt, 'every'): opt.every = None
    if type(opt.every)==float: opt.every = timedelta(seconds=opt.every)
    if type(opt.after)==str: opt.after = dateutil.parser.parse(opt.after) # xxx local tz by default
    if type(opt.before)==str: opt.before = dateutil.parser.parse(opt.before) # xxx local tz

    # parse specs, group them by file
    series = [] # all
    fns = collections.defaultdict(list) # grouped by fn
    for spec_ord, spec in enumerate(specs):
        for s in series_spec(spec, spec_ord, opt):
            fns[(s.fn,s.type)].append(s) # xxx canonicalize filename
            series.append(s)

    # process by file according to file type
    for fn, filetype in sorted(fns):
        opt.last_time = pytz.utc.localize(datetime.min)
        if filetype=='re': series_read_re(fn, fns[(fn,filetype)], opt)
        elif filetype=='json': series_read_json(fn, fns[(fn,filetype)], opt)
        
    # finish each series
    for s in series:
        s.finish()

    # get graphs taking into account splits and merges
    graphs = collections.defaultdict(list)
    ygroups = collections.defaultdict(list)
    for s in series:
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
    .desc {
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

    function key() {
        var evt = window.event
        var c = String.fromCharCode(evt.charCode)
        first_row = document.getElementById("table").firstChild.firstChild
        while (first_row && !first_row.classList.contains('row'))
            first_row = first_row.nextSibling
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
            else if (selected.nextSibling) {
                _desel()
                selected = selected.nextSibling
            }
        } else if (c=='') {
            if (!selected)
                selected = last_selected
            else if (selected != first_row) {
                selected.classList.remove('selected')
                selected = selected.previousSibling
            }
        } else if (c=='n') {
            if (selected) {
                next = selected.nextSibling
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
                    prev = selected.previousSibling
                    parent = selected.parentNode
                    parent.removeChild(selected)
                    parent.insertBefore(selected, prev)
                    re_number()
                }
            }
        } else if (c=='N') {
            if (selected) {
                s = selected.nextSibling
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
                s = selected.previousSibling
                parent = selected.parentNode
                parent.removeChild(selected)
                parent.insertBefore(selected, first_row)
                sel(s)
                re_number()
            }
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
    p.add_argument(dest='series', nargs='*')
    #p.add_argument('--format-file', '-f', default=None)
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
    p.add_argument('--list', action='store_true')

    global opt
    opt = p.parse_args()

    # just list?
    if opt.list:
        for fmt in sorted(formats, key=lambda fmt: fmt['name'].lower()):
            f = collections.defaultdict(lambda: '...')
            f.update(fmt)
            msg(get(f, 'name'))
        return

    # get our graphs
    graphs = series_all(opt.series, opt)
    if not graphs:
        msg('no series specified')
        return
    tmin = min(s.tmin for g in graphs for s in g if s.tmin)
    tmax = max(s.tmax for g in graphs for s in g if s.tmax)
    tspan = float((tmax-tmin).total_seconds())

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
        graph(data=data,
              tmin=tmin, tmax=tmax, width=opt.width,
              ymin=0, ymax=ymax, height=opt.height,
              #ticks=ticks, shaded=not opt.no_shade and len(data)==1)
              ticks=ticks, shaded=len(data)==1)

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
    elt('body', {'onkeypress':'key()'})

    elt('div', {'onclick':'toggle_help()'})
    put('click to toggle help')
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
        td('desc')
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
    for g in sorted(graphs, key=lambda g: g[0].key):
        g.sort(key=lambda s: s.key)
        ymin = min(s.ymin for s in g)
        ymax = max(s.ymax for s in g)
        ysum = sum(s.ysum for s in g)
        ylen = sum(len(s.ys) for s in g)
        display_ymax = max(s.display_ymax for s in g)
        if ylen:
            if ymax!=0 or ymin!=0 or opt.show_zero:
                elt('tr', {'onclick':'sel(this)', 'class':'row'})
                td('data', '{:,.3f}'.format(float(ysum)/ylen))
                td('data', '{:,.3f}'.format(ymax))
                td('graph')
                data = [(s.ts, s.ys, color(i) if len(g)>1 else 'black') for i,s in enumerate(g)]
                _graph(data, display_ymax)
                end('td')
                if opt.number_rows:
                    td('row-number', str(row))
                    row += 1
                name_td(g)
                end('tr')
            else:
                name = get(g[0].fmt, 'name')
                msg('skipping uniformly zero data for', name, 'in', g[0].fn)
        elif opt.show_empty:
            elt('tr', {'onclick':'sel(this)', 'class':'row'})
            td('data', 'n/a')
            td('data', 'n/a')
            td('graph')
            _graph()
            end('td')
            if opt.number_rows:
                td('row-number', str(row))
                row += 1
            name_td(g)
            end('tr')
        else:
            msg('no data for', get(g[0].fmt, 'name'), 'in', g[0].fn)

    end('table')
    end('body')
    end('html')


################################################################################
#
# built-in formats
#

#
# generic grep format
# usage: timeseries 'grep(pat=pat):fn
#     pat - re to locate data; must include one re group identifying data
#     fn - file to be searched
# this format supplies a generic re to identify a timestamp
# assumes the timestamp precedes the data
#

format(
    name = 'grep {pat}',
    re = '^.*(....-..-..T..:..:..(?:\....)?Z?|(?:... )?... .. .... ..:..:..).*{pat}',
)


#
# serverStatus json output, for example:
# mongo --eval "while(true) {print(JSON.stringify(db.serverStatus())); sleep($delay*1000)}"
#

MB = 1024*1024

def fmt_units(scale, delta):
    units = ''
    if scale==MB: units = 'MB'
    if delta: units += '/s'
    return units

def ss(json_data, name=None, scale=1, delta=False, units=None, **kwargs):
    if not name: name = 'ss ' + json_data[0] +  ': ' + ' '.join(json_data[1:])
    if not units: units = fmt_units(scale, delta)
    if units: units = ' (' + units + ')'
    name = name + units
    format(
        type = 'json',
        name = name,
        json_data = json_data,
        json_time = ['localTime'],        
        scale = scale,
        delta = delta,
        **kwargs
    )

def ss_opcounter(opcounter, **kwargs):
    ss(
        json_data = ['opcounters', opcounter],
        merge = 'ss_opcounters',
        name = 'ss opcounters: ' + opcounter,
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
    json_data = ['globalLock', 'activeClients', 'readers'],
    name = 'ss global: read queue',
    merge = '_ss_queue',
)

ss(
    json_data = ['globalLock', 'activeClients', 'writers'],
    name = 'ss global: write queue',
    merge = '_ss_queue',
)

# TBD
#["asserts", "msg"]
#["asserts", "regular"]
#["asserts", "rollovers"]
#["asserts", "user"]
#["asserts", "warning"]
#["backgroundFlushing", "average_ms"]
#["backgroundFlushing", "flushes"]
#["backgroundFlushing", "last_finished"]
#["backgroundFlushing", "last_ms"]
#["backgroundFlushing", "total_ms"]
#["connections", "available"]
ss(["connections", "current"])
#["connections", "totalCreated", "floatApprox"]
#["cursors", "clientCursors_size"]
#["cursors", "note"]
#["cursors", "pinned"]
#["cursors", "timedOut"]
#["cursors", "totalNoTimeout"]
#["cursors", "totalOpen"]
#["dur", "commits"]
#["dur", "commitsInWriteLock"]
#["dur", "compression"]
#["dur", "earlyCommits"]
#["dur", "journaledMB"]
#["dur", "timeMs", "dt"]
#["dur", "timeMs", "prepLogBuffer"]
#["dur", "timeMs", "remapPrivateView"]
#["dur", "timeMs", "writeToDataFiles"]
#["dur", "timeMs", "writeToJournal"]
#["dur", "writeToDataFilesMB"]
ss(["extra_info", "heap_usage_bytes"], scale=MB, level=1, wrap=2.0**31)
#["extra_info", "note"]
ss(["extra_info", "page_faults"], delta=True, level=1)
###["globalLock", "activeClients", "readers"] # see above
ss(['globalLock', 'activeClients', 'total'], level=99)
####["globalLock", "activeClients", "writers"] # see above
ss(['globalLock', 'currentQueue', 'readers'], level=99)
ss(['globalLock', 'currentQueue', 'writers'], level=99)
ss(['globalLock', 'currentQueue', 'total'], level=99)
ss(['globalLock', 'totalTime', 'floatApprox'], level=99)
#["host"]
#["localTime"]
#["mem", "bits"]
ss(["mem", "mapped"], scale=MB, level=1)
ss(["mem", "mappedWithJournal"], scale=MB)
ss(["mem", "resident"], units="MB", level=1)
#["mem", "supported"]
ss(["mem", "virtual"], units="MB", level=1)
ss(["metrics", "commands", "serverStatus", "failed", "floatApprox"], delta=True, level=1)
ss(["metrics", "commands", "serverStatus", "total", "floatApprox"], delta=True, level=1)
ss(["metrics", "commands", "whatsmyuri", "failed", "floatApprox"], delta=True, level=1)
ss(["metrics", "commands", "whatsmyuri", "total", "floatApprox"], delta=True, level=1)
ss(["metrics", "cursor", "open", "noTimeout", "floatApprox"], level=1)
ss(["metrics", "cursor", "open", "pinned", "floatApprox"], level=1)
ss(["metrics", "cursor", "open", "total", "floatApprox"], level=1)
ss(["metrics", "cursor", "timedOut", "floatApprox"], delta=True, level=1)
ss(["metrics", "document", "deleted", "floatApprox"], delta=True, level=1)
ss(["metrics", "document", "inserted", "floatApprox"], delta=True, level=1)
ss(["metrics", "document", "returned", "floatApprox"], delta=True, level=1)
ss(["metrics", "document", "updated", "floatApprox"], delta=True, level=1)
ss(["metrics", "getLastError", "wtime", "num"], delta=True, level=1)
ss(["metrics", "getLastError", "wtime", "totalMillis"], delta=True, level=1)
ss(["metrics", "getLastError", "wtimeouts", "floatApprox"], delta=True, level=1)
ss(["metrics", "operation", "fastmod", "floatApprox"], delta=True, level=1)
ss(["metrics", "operation", "idhack", "floatApprox"], delta=True, level=1)
ss(["metrics", "operation", "scanAndOrder", "floatApprox"], delta=True, level=1)
ss(["metrics", "queryExecutor", "scanned", "floatApprox"], delta=True, level=1)
ss(["metrics", "queryExecutor", "scannedObjects", "floatApprox"], delta=True, level=1)
ss(["metrics", "record", "moves", "floatApprox"], delta=True, level=1)
ss(["metrics", "repl", "apply", "batches", "num"], delta=True, level=1)
ss(["metrics", "repl", "apply", "batches", "totalMillis"], delta=True, level=1)
ss(["metrics", "repl", "apply", "ops", "floatApprox"], delta=True, level=1)
ss(["metrics", "repl", "buffer", "count", "floatApprox"], delta=True, level=1)
ss(["metrics", "repl", "buffer", "maxSizeBytes"], delta=True, level=1)
ss(["metrics", "repl", "buffer", "sizeBytes", "floatApprox"], delta=True, level=1)
ss(["metrics", "repl", "network", "bytes", "floatApprox"], delta=True)
ss(["metrics", "repl", "network", "getmores", "num"], delta=True, level=1)
ss(["metrics", "repl", "network", "getmores", "totalMillis"], delta=True)
ss(["metrics", "repl", "network", "ops", "floatApprox"], delta=True, level=1)
ss(["metrics", "repl", "network", "readersCreated", "floatApprox"], delta=True)
ss(["metrics", "repl", "preload", "docs", "num"], delta=True, level=1)
ss(["metrics", "repl", "preload", "docs", "totalMillis"], delta=True)
ss(["metrics", "repl", "preload", "indexes", "num"], delta=True, level=1)
ss(["metrics", "repl", "preload", "indexes", "totalMillis"], delta=True)
ss(["metrics", "storage", "freelist", "search", "bucketExhausted", "floatApprox"], delta=True, level=1)
ss(["metrics", "storage", "freelist", "search", "requests", "floatApprox"], delta=True)
ss(["metrics", "storage", "freelist", "search", "scanned", "floatApprox"], delta=True, level=1)
ss(["metrics", "ttl", "deletedDocuments", "floatApprox"], delta=True, level=1)
ss(["metrics", "ttl", "passes", "floatApprox"], delta=True, level=1)
ss(["network", "bytesIn"], delta=True, scale=MB, level=1)
ss(["network", "bytesOut"], delta=True, scale=MB, level=1)
ss(["network", "numRequests"], delta=True, level=1)
#["ok"]
#["opcounters", "command"]
#["opcounters", "delete"]
#["opcounters", "getmore"]
#["opcounters", "insert"]
#["opcounters", "query"]
#["opcounters", "update"]
#["opcountersRepl", "command"]
#["opcountersRepl", "delete"]
#["opcountersRepl", "getmore"]
#["opcountersRepl", "insert"]
#["opcountersRepl", "query"]
#["opcountersRepl", "update"]
#["pid", "floatApprox"]
#["process"]
#["storageEngine", "name"]
#["uptime"]
#["uptimeEstimate"]
#["uptimeMillis", "floatApprox"]
#["version"]


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
iostat_cpu('idle')

def iostat_disk(re_data, name, **kwargs):
    iostat(
        re_data = re_data,
        split = 'iostat_disk',
        name = 'iostat disk: {iostat_disk} ' + name,
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
    name = 'mongod max logged query (ms) per {bucket_size}s',
    re = '.* query: .* ([0-9]+)ms$',
    bucket_op = 'max',
    bucket_size = 1, # size of buckets in seconds
)

mongod(
    name = 'mongod logged queries longer than {count_min_ms}ms per {bucket_size}s',
    re = '.* query: .* ([0-9]+)ms$',
    bucket_op = 'count',
    bucket_size = 1,       # size of buckets in seconds
    count_min_ms = 0,      # minimum query duration to count',
)

mongod(
    name = 'mongod queued queries longer than {queue_min_ms}ms',
    re = '.* query: .* ([0-9]+)ms$',
    queue = True,
    queue_min_ms = 0,  # minimum op duration to count for queue',
)

mongod(
    name = 'mongod: waiting to acquire lock per {bucket_size}s',
    re = '.* has been waiting to acquire lock for more than (30) seconds',
    bucket_op = 'count',
    bucket_size = 1,  # size of buckets in seconds
)

#
# wt
#

def wt(wt_cat, wt_name, delta=False, scale=1.0, **kwargs):

    units = fmt_units(scale, delta)
    if units: units = ' (' + units + ')'

    # for parsing wt data in json format files
    format(
        type = 'json',
        json_time = ['localTime'],
        json_data = ['wiredTiger', wt_cat, wt_name],
        scale = scale,
        delta = delta,
        name = 'ss wt {}: {}{}'.format(wt_cat, wt_name, units),
        **kwargs
    )

    # for parsing wt data in json re format files
    format(
        type = 're',
        re = '^(... .. ..:..:..) ([0-9]+) .* {}: {}'.format(wt_cat, wt_name),
        scale = scale,
        delta = delta,
        name = 'wt {}: {}{}'.format(wt_cat, wt_name, units),
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
wt('cache', 'checkpoint blocked page eviction', delta=True)
wt('cache', 'data source pages selected for eviction unable to be evicted')
wt('cache', 'eviction server candidate queue empty when topping up', delta=True)
wt('cache', 'eviction server candidate queue not empty when topping up', delta=True)
wt('cache', 'eviction server evicting pages', delta=True)
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

#["wiredTiger", "LSM", "application work units currently queued"]
#["wiredTiger", "LSM", "merge work units currently queued"]
#["wiredTiger", "LSM", "rows merged in an LSM tree"]
#["wiredTiger", "LSM", "sleep for LSM checkpoint throttle"]
#["wiredTiger", "LSM", "sleep for LSM merge throttle"]
#["wiredTiger", "LSM", "switch work units currently queued"]
#["wiredTiger", "LSM", "tree maintenance operations discarded"]
#["wiredTiger", "LSM", "tree maintenance operations executed"]
#["wiredTiger", "LSM", "tree maintenance operations scheduled"]
#["wiredTiger", "LSM", "tree queue hit maximum"]
#["wiredTiger", "async", "current work queue length"]
#["wiredTiger", "async", "maximum work queue length"]
#["wiredTiger", "async", "number of allocation state races"]
#["wiredTiger", "async", "number of flush calls"]
#["wiredTiger", "async", "number of operation slots viewed for allocation"]
#["wiredTiger", "async", "number of times operation allocation failed"]
#["wiredTiger", "async", "number of times worker found no work"]
#["wiredTiger", "async", "total allocations"]
#["wiredTiger", "async", "total compact calls"]
#["wiredTiger", "async", "total insert calls"]
#["wiredTiger", "async", "total remove calls"]
#["wiredTiger", "async", "total search calls"]
#["wiredTiger", "async", "total update calls"]
#["wiredTiger", "block-manager", "blocks pre-loaded"]
#["wiredTiger", "block-manager", "blocks read"]
#["wiredTiger", "block-manager", "blocks written"]
#["wiredTiger", "block-manager", "bytes read"]
#["wiredTiger", "block-manager", "bytes written"]
#["wiredTiger", "block-manager", "mapped blocks read"]
#["wiredTiger", "block-manager", "mapped bytes read"]
#["wiredTiger", "btree", "cursor create calls"]
#["wiredTiger", "btree", "cursor insert calls"]
#["wiredTiger", "btree", "cursor next calls"]
#["wiredTiger", "btree", "cursor prev calls"]
#["wiredTiger", "btree", "cursor remove calls"]
#["wiredTiger", "btree", "cursor reset calls"]
#["wiredTiger", "btree", "cursor search calls"]
#["wiredTiger", "btree", "cursor search near calls"]
#["wiredTiger", "btree", "cursor update calls"]
#["wiredTiger", "cache", "bytes currently in the cache"]
#["wiredTiger", "cache", "bytes read into cache"]
#["wiredTiger", "cache", "bytes written from cache"]
#["wiredTiger", "cache", "checkpoint blocked page eviction"]
#["wiredTiger", "cache", "eviction server candidate queue empty when topping up"]
#["wiredTiger", "cache", "eviction server candidate queue not empty when topping up"]
#["wiredTiger", "cache", "eviction server evicting pages"]
#["wiredTiger", "cache", "eviction server populating queue, but not evicting pages"]
#["wiredTiger", "cache", "eviction server unable to reach eviction goal"]
#["wiredTiger", "cache", "failed eviction of pages that exceeded the in-memory maximum"]
#["wiredTiger", "cache", "hazard pointer blocked page eviction"]
#["wiredTiger", "cache", "internal pages evicted"]
#["wiredTiger", "cache", "maximum bytes configured"]
#["wiredTiger", "cache", "modified pages evicted"]
#["wiredTiger", "cache", "page split during eviction deepened the tree"]
#["wiredTiger", "cache", "pages currently held in the cache"]
#["wiredTiger", "cache", "pages evicted because they exceeded the in-memory maximum"]
#["wiredTiger", "cache", "pages read into cache"]
#["wiredTiger", "cache", "pages selected for eviction unable to be evicted"]
#["wiredTiger", "cache", "pages split during eviction"]
#["wiredTiger", "cache", "pages walked for eviction"]
#["wiredTiger", "cache", "pages written from cache"]
#["wiredTiger", "cache", "tracked dirty bytes in the cache"]
#["wiredTiger", "cache", "tracked dirty pages in the cache"]
#["wiredTiger", "cache", "unmodified pages evicted"]
#["wiredTiger", "connection", "files currently open"]
#["wiredTiger", "connection", "memory allocations"]
#["wiredTiger", "connection", "memory frees"]
#["wiredTiger", "connection", "memory re-allocations"]
#["wiredTiger", "connection", "pthread mutex condition wait calls"]
#["wiredTiger", "connection", "pthread mutex shared lock read-lock calls"]
#["wiredTiger", "connection", "pthread mutex shared lock write-lock calls"]
#["wiredTiger", "connection", "total read I/Os"]
#["wiredTiger", "connection", "total write I/Os"]
#["wiredTiger", "data-handle", "session dhandles swept"]
#["wiredTiger", "data-handle", "session sweep attempts"]
#["wiredTiger", "log", "consolidated slot closures"]
#["wiredTiger", "log", "consolidated slot join races"]
#["wiredTiger", "log", "consolidated slot join transitions"]
#["wiredTiger", "log", "consolidated slot joins"]
#["wiredTiger", "log", "failed to find a slot large enough for record"]
#["wiredTiger", "log", "log buffer size increases"]
#["wiredTiger", "log", "log bytes of payload data"]
#["wiredTiger", "log", "log bytes written"]
#["wiredTiger", "log", "log read operations"]
#["wiredTiger", "log", "log scan operations"]
#["wiredTiger", "log", "log scan records requiring two reads"]
#["wiredTiger", "log", "log sync operations"]
#["wiredTiger", "log", "log write operations"]
#["wiredTiger", "log", "logging bytes consolidated"]
#["wiredTiger", "log", "maximum log file size"]
#["wiredTiger", "log", "record size exceeded maximum"]
#["wiredTiger", "log", "records processed by log scan"]
#["wiredTiger", "log", "slots selected for switching that were unavailable"]
#["wiredTiger", "log", "total log buffer size"]
#["wiredTiger", "log", "yields waiting for previous log file close"]
#["wiredTiger", "reconciliation", "page reconciliation calls"]
#["wiredTiger", "reconciliation", "page reconciliation calls for eviction"]
#["wiredTiger", "reconciliation", "split bytes currently awaiting free"]
#["wiredTiger", "reconciliation", "split objects currently awaiting free"]
#["wiredTiger", "session", "open cursor count"]
#["wiredTiger", "session", "open session count"]
#["wiredTiger", "transaction", "transaction begins"]
#["wiredTiger", "transaction", "transaction checkpoint currently running"]
#["wiredTiger", "transaction", "transaction checkpoint max time (msecs)"]
#["wiredTiger", "transaction", "transaction checkpoint min time (msecs)"]
#["wiredTiger", "transaction", "transaction checkpoint most recent time (msecs)"]
#["wiredTiger", "transaction", "transaction checkpoint total time (msecs)"]
#["wiredTiger", "transaction", "transaction checkpoints"]
#["wiredTiger", "transaction", "transaction failures due to cache overflow"]
#["wiredTiger", "transaction", "transaction range of IDs currently pinned"]
#["wiredTiger", "transaction", "transactions committed"]
#["wiredTiger", "transaction", "transactions rolled back"]
#["wiredTiger", "uri"]



#
#
#

if __name__ == '__main__':
    main()
