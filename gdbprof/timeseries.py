import json
import sys
import os
import collections
import re
import datetime
import dateutil.parser
import argparse
import itertools
import pytz

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
    .curve {
        fill: none;
        stroke: black;
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
    .shade {
        fill: rgb(230,230,230);
        stroke: none;
    }
    .tick {
        stroke: rgba(255,0,0,0.2);
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
'''

def graph(
    data=[],
    tmin=None, tmax=None, width=None,
    ymin=None, ymax=None, height=None,
    ticks=None, line_width=0.1, shaded=True
):
    elt('svg', {
        'width':'%gem' % width, 'height':'%gem' % height,
        'viewBox':'%g %g %g %g' % (-0.05, -0.05, width, height+0.2)
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
        gx = lambda t: (t-tmin).total_seconds() / tspan * width
        gy = lambda y: (1.0 - (float(y)-ymin) / yspan) * height
        line = ' '.join('%g,%g' % (gx(t), gy(ys[t])) for t in ts)
        if shaded:
            left = '%g,%g' % (gx(ts[0]), height+0.05)
            right = '%g,%g' % (gx(ts[-1]), height+0.05)
            points = left + ' ' + line + ' ' + right
            eltend('polygon', {'points':points, 'class':'shade'})
        eltend('polyline', {'points':line, 'class':'curve', 'style':'stroke:%s'%color})
    if data and ticks:
        for i in range(ticks+1):
            x = width * i / ticks
            eltend('line', {'x1':x, 'x2':x, 'y1':0, 'y2':height, 'class':'tick'})
    end('svg')


#
#
#

class Series:

    def __init__(self, spec, fmt_name, fmt, params, fn):

        self.spec = spec
        self.fmt_name = fmt_name
        self.fmt = dict(fmt)
        self.fmt.update(params)
        self.fn = fn
        self.key = fmt['_ord']

        # compute delta (/s) 
        self.delta = get(self.fmt, 'delta', False)
        if self.delta:
            self.last_t = None
    
        # request to bucketize the data
        self.buckets = float(get(self.fmt, 'bucket_size', 0))
        if self.buckets:
            self.t0 = dateutil.parser.parse('2000-01-01T00:00:00Z')
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
        self.re = get(self.fmt, 're', None)
        if self.re and re.compile(self.re).groups==0:
            raise Exception('re ' + self.re + ' does not have any groups')
        self.re_time = get(self.fmt, 're_time', 0)
        self.re_data = get(self.fmt, 're_data', 1)

        # info for json-format files
        self.json_time = get(self.fmt, 'json_time', None)
        self.json_data = get(self.fmt, 'json_data', None)

        # timezone offset
        tz = float(get(self.fmt, 'tz', 0))
        self.tz = datetime.timedelta(hours=tz)

        # all graphs in a ygroup will be plotted with a common display_ymax
        self.ygroup = get(self.fmt, 'ygroup', id(self))

        # which output graph this series will be plotted on
        self.graph = id(self) # will update with fmt['merge'] later so can use split key

        # split into multiple series based on a data value
        self.split_field = get(self.fmt, 'split', None)
        self.split_series = {}


    def get_split(self, split_key):
        if split_key not in self.split_series:
            new = Series(self.spec, self.fmt_name, self.fmt, {}, self.fn)
            new.fmt[self.split_field] = split_key # make split key available for formatting
            new.split_field = None
            new.key = (split_ords[self.split_field], split_key, new.key)
            self.split_series[split_key] = new
        return self.split_series[split_key]

    def get_graphs(self, graphs, ygroups, merges):
        if not self.split_field:
            # do self.graph and .description late so they can use split key
            if merges:
                merge = get(self.fmt, 'merge', None)
                if merge: self.graph = merge
            self.description = get(self.fmt, 'description', self.fmt_name)
            graphs[self.graph].append(self)
            ygroups[self.ygroup].append(self)
        else:
            for s in self.split_series.values():
                s.get_graphs(graphs, ygroups, merges)

    def _data_point(self, t, d):
        t = dateutil.parser.parse(t)
        if not t.tzinfo:
            t = pytz.utc.localize(t-self.tz)
        d = float(d) / self.scale
        if self.delta:
            if self.last_t and self.last_t!=t:
                self.ts.append(t)
                self.ys[t] = (d-self.last_d) / (t-self.last_t).total_seconds()
            if not self.last_t or self.last_t!=t:
                self.last_t = t
                self.last_d = d
        elif self.buckets:
            s0 = (t - self.t0).total_seconds()
            s1 = s0 // self.buckets * self.buckets
            t = t + datetime.timedelta(0, s1-s0)
            self.ys[t] = self.op(self.ys, t, d)
        elif self.queue:
            if d>self.queue_min_ms:
                ms = datetime.timedelta(0, d/1000.0)
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
            tmin = min(self.ys.keys())
            tmax = max(self.ys.keys())
            n = int((tmax-tmin).total_seconds() / self.buckets)
            dt = datetime.timedelta(0, self.buckets)
            self.ts = [tmin + dt*i for i in range(n+1)]
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

def get(fmt, n, default=REQUIRED):
    v = fmt.get(n, default)
    if v is REQUIRED:
        raise Exception('missing required parameter ' + repr(n) + ' in ' + fmt['name'])
    if (type(v)==str or type(v)==unicode):
        v = str(v).format(**fmt)
    elif type(v)==list:
        v = [str(s).format(**fmt) for s in v] # xxx recursive? dict?
    return v


def series_spec(spec):

    # parse helper
    def split(s, expect, err, full):
        m = re.split('([' + expect + err + '])', s, 1)
        s1, d, s2 = m if len(m)==3 else (m[0], '$', '')
        if d in err:
            msg = 'expected %s at pos %d in %s, found %s' % (expect, len(full)-len(s)+1, full, d)
            raise Exception(msg)
        return s1, d, s2

    # parse the spec
    fmt_name, d, s = split(spec, '(:', ')=', spec)
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
    fn = s.lstrip(':')
    dbg(fmt_name, params, fn)

    # a series for all formats that match the specified name
    series = []
    for name, fmt in formats.items():
        if re.search('^' + fmt_name, name):
            series.append(Series(spec, fmt_name, fmt, params, fn))
    if not series:
        msg('no formats match', fmt_name)

    return series

def series_read_json(fn, series):

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
                else:
                    if not time:
                        raise Exception('time not found in ' + line)
                    s.data_point(time, v, None) # xxx splits?


def series_read_re(fn, series):

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
        dbg(chunk_re)
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
                        if not t:
                            t = last_time                            
                        if t:
                            d = field(s.re_data)
                            if d != None:
                                s.data_point(t, d, field)
                            last_time = t

formats = {}     # formats loaded from various def files
split_ords = {}  # sort order for each split_key - first occurrence of split_key in def file

def series_load(fn, ord):
    dbg('loading', fn)
    try:
        for o, fmt in enumerate(json.load(open(fn))):
            fmt['_ord'] = (ord, o)
            if 'split' in fmt:
                split_field = fmt['split']
                if not split_field in split_ords:
                    split_ords[split_field] = fmt['_ord']
            if '_inherit' in fmt:
                fmt = dict(formats[fmt['_inherit']].items() + fmt.items())
            formats[fmt['name']] = fmt
    except Exception as e:
        msg(fn + ': ' + e.message)

def series_all(format_file, specs, merges=True):

    # read timeseries.json files
    fn = os.path.join(os.path.dirname(__file__), 'timeseries.json')
    series_load(fn, 1001)
    series_load('timeseries.json', 1000)
    for ord, fn in enumerate(format_file):
        if fn:
            series_load(fn, ord)

    # parse specs, group them by file
    series = [] # all
    fns = collections.defaultdict(list) # grouped by fn
    for spec in specs:
        for s in series_spec(spec):
            fns[(s.fn, s.type)].append(s)
            series.append(s)

    # process by file according to file type
    for fn, type in sorted(fns):
        if type=='re': series_read_re(fn, fns[(fn,type)])
        elif type=='json': series_read_json(fn, fns[(fn,type)])
        
    # finish each series
    for s in series:
        s.finish()

    # get graphs taking into account splits and merges
    graphs = collections.defaultdict(list)
    ygroups = collections.defaultdict(list)
    for s in series:
        s.get_graphs(graphs, ygroups, merges)

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
        stroke: blue;
        stroke-width: 1;
        vector-effect: non-scaling-stroke;
    }
    .circle {
        fill: blue;
    }
'''

cursors_script = '''

    function ex(e) {
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
        e.parentNode.removeChild(e)
    }
  
    function move(e) {
        var x = ex(e)
        set_attrs(document.getElementById('lll'), {x1:x, x2:x})
    }
  
    function out(e) {
        set_attrs(document.getElementById('lll'), {x1:-1, x2:-1})
    }
  
    var cnum = 0;
    var width = %d;
  
    function add(e) {
        var x = ex(e)
        var line = elt(svg_ns, "line", {id:"l"+cnum, x1:x, x2:x, y1:0, y2:1, class:"cursor"})
        document.getElementById("cursors").appendChild(line)
        var circle = elt(svg_ns, "circle",
            {id:"c"+cnum, cx:x*width, cy:0.6, r:0.4, class:"circle", onclick:"del("+cnum+")"})
        document.getElementById("circles").appendChild(circle)
        cnum += 1
    }
  
    function del(i) {
        del_id("c"+i)
        del_id("l"+i)
    }
'''

def cursors_html(width):
    elt('table')
    elt('tr')
    td('graph')
    eltend('svg', {
        'id':'circles', 'width':'%dem'%(width), 'height':"1em", 'viewBox':"0 0 %d 1" % width
    })
    end('td')
    end('tr')
    elt('tr')
    td('graph')
    elt('svg', {
        'id':'cursors', 'width':'%dem'%width, 'height':'100%', 'viewBox':'0 0 1 1',
        'preserveAspectRatio':'none', 'style':'position:absolute; background:none;',
        'onmousemove':'move(this)', 'onmouseout':'out(this)',  'onclick':'add(this)'
    })
    elt('line', {'id':'lll', 'class':'cursor', 'x1':0, 'y1':0, 'x2':0, 'y2':1})
    end('svg')
    end('td')
    end('tr')
    end('table')

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
                }
            }
        } else if (c=='p') {
            if (selected) {
                if (selected!=first_row) {
                    prev = selected.previousSibling
                    parent = selected.parentNode
                    parent.removeChild(selected)
                    parent.insertBefore(selected, prev)
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
                }
            }
        } else if (c=='P') {
            if (selected && selected != first_row) {
                s = selected.previousSibling
                parent = selected.parentNode
                parent.removeChild(selected)
                parent.insertBefore(selected, first_row)
                sel(s)
            }
        }
        _sel(selected)
    }    
'''


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
    p.add_argument(dest='series', nargs='+')
    p.add_argument('--format-file', '-f', default=None)
    p.add_argument('--width', type=float, default=30)
    p.add_argument('--height', type=float, default=1.5)
    p.add_argument('--ticks', type=int, default=5)
    p.add_argument('--show-empty', action='store_true')
    p.add_argument('--show-zero', action='store_true')
    p.add_argument('--no-shade', action='store_true')
    p.add_argument('--no-merges', action='store_true')
    p.add_argument('--number-rows', action='store_true')

    global opt
    opt = p.parse_args()

    graphs = series_all([opt.format_file], opt.series, not opt.no_merges)
    if not graphs:
        msg('no series specified')
        return
    #dbg('zzz', [s.tmin for g in graphs for s in g])
    tmin = min(s.tmin for g in graphs for s in g if s.tmin)
    tmax = max(s.tmax for g in graphs for s in g if s.tmax)

    def _graph(data=[], ymax=None):
        graph(data=data,
              tmin=tmin, tmax=tmax, width=opt.width,
              ymin=0, ymax=ymax, height=opt.height,
              ticks=opt.ticks, shaded=not opt.no_shade and len(data)==1)

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
    elt('table', {'id':'table', 'style':'position:relative;'})

    elt('tr')
    td('head data', 'avg')
    td('head data', 'max')
    elt('td')
    cursors_html(opt.width)
    end('td')
    if opt.number_rows:
        td('head row-number', 'row&emsp;&emsp;') # xxx
    td('head desc', 'description')
    end('tr')

    colors = ['rgb(50,102,204)','rgb(220,57,24)','rgb(253,153,39)','rgb(20,150,24)',
              'rgb(153,20,153)', 'rgb(200,200,200)']

    def description(g):
        td('desc')
        pfx = os.path.commonprefix([s.description for s in g])
        sfx = os.path.commonprefix([s.description[::-1] for s in g])[::-1]
        put(pfx)
        if sfx != pfx:
            for i,s in enumerate(g):
                mid = ' ' + s.description[len(pfx):len(s.description)-len(sfx)]
                eltend('span', {'style':'color:%s' % colors[i]}, mid)
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
                data = [(s.ts, s.ys, colors[i] if len(g)>1 else 'black') for i,s in enumerate(g)]
                _graph(data, display_ymax)
                end('td')
                if opt.number_rows:
                    td('data', '%d&emsp;&emsp;' % row) # xxx
                    row += 1
                description(g)
                end('tr')
            else:
                msg('skipping uniformly zero data for', g[0].fmt['name'] + ':' + g[0].fn)
        elif opt.show_empty:
            elt('tr', {'onclick':'sel(this)', 'class':'row'})
            td('data', 'n/a')
            td('data', 'n/a')
            td('graph')
            _graph()
            end('td')
            if opt.number_rows:
                td('data', '%d&emsp;&emsp;' % row) # xxx
                row += 1
            description(g)
            end('tr')
        else:
            msg('no data for', g[0].fmt['name'] + ':' + g[0].fn)

    end('table')
    end('body')
    end('html')

if __name__ == '__main__':
    main()
