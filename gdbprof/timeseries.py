import json
import sys
import os
import collections
import re
import datetime
import dateutil.parser
import argparse

def elt(name, **attrs):
    sys.stdout.write('<%s' % name)
    for a in attrs:
        sys.stdout.write(' %s="%s"' % (a.strip('_'), attrs[a]))
    sys.stdout.write('>')

def eltend(name, **attrs):
    elt(name, **attrs)
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
    if __name__=='__main__' and 'opt.dbg':
        sys.stderr.write(' '.join(str(s) for s in ss) + '\n')

#
#
#

graph_style = '''
    .data {
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
    ts=None, tmin=None, tmax=None, width=None,
    ys=None, ymin=None, ymax=None, height=None,
    ticks=None, line_width=0.1, shaded=True
):
    elt('svg', width='%gem' % width, height='%gem' % height,
        viewBox='%g %g %g %g' % (-0.05, -0.05, width+0.2, height+0.2))
    if ts:
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
            eltend('polygon', points=points, _class='shade')
        eltend('polyline', points=line, **{'class':'data'})
        if ticks:
            for i in range(ticks+1):
                x = width * i / ticks
                eltend('line', x1=x, x2=x, y1=0, y2=height, **{'class':'tick'})
    end('svg')


#
#
#

class Series:

    def __init__(self, fmt, params, fmt_name):

        self.fmt = dict(fmt)
        self.fmt.update(params)
        self.fmt_name = fmt_name

        self.description = get(self.fmt, 'description', self.fmt_name)
    
        self.delta = get(self.fmt, 'delta', False)
        if self.delta:
            self.last_t = None
    
        self.buckets = float(get(self.fmt, 'bucket_size', 0))
        if self.buckets:
            self.t0 = dateutil.parser.parse('2000-01-01')
            self.op = op_for(self.fmt, get(self.fmt, 'bucket_op', 'max'))
    
        self.queue = get(self.fmt, 'queue', False)
        if self.queue:
            self.queue_times = []
            self.queue_min_ms = float(get(self.fmt, 'queue_min_ms', 0))
    
        self.scale = get(self.fmt, 'scale', 1)
    
        self.ts = []
        self.ys = collections.defaultdict(int)
    
        self.re = get(self.fmt, 're')

    def data_point(self, t, d):
        t = dateutil.parser.parse(t)
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
    
        self.tmin = min(self.ts) if self.ts else datetime.datetime.max
        self.tmax = max(self.ts) if self.ts else datetime.datetime.min
        self.ymin = min(self.ys.values()) if self.ys else float('inf')
        self.ymax = max(self.ys.values()) if self.ys else float('-inf')
    

def op_for(fmt, s):
    if s=='max': return lambda ys, t, d: max(ys[t], d)
    if s=='count':
        count_min_ms = float(fmt.get("count_min_ms", 0))
        return lambda ys, t, d: ys[t]+1 if d>=count_min_ms else ys[t]


def get(fmt, *n):
    v = fmt.get(*n)
    if (type(v)==str or type(v)==unicode):
        v = v.format(**fmt)
    return v


def series_spec(formats, spec):

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
            value, d, s = split(s, '()', '', spec) # bare value
            p = 0
            while d=='(' or p>0: # plus balanced parens
                value += d
                if d=='(': p += 1
                elif d==')': p -= 1
                v, d, s = split(s, '(),', '', spec)
                value += v
            params[name] = value
    fn = s.lstrip(':')

    # a series for all formats that match the specified name
    series = []
    for name, fmt in sorted(formats.items()):
        if re.search('^' + fmt_name, name):
            series.append(Series(fmt, params, fmt_name))

    # Python re impl can only handle 100 groups
    # so we process the formats in chunks, constructing one regex for each chunk
    # and match each line against the regex for each chunk
    chunk_size = 40
    rs = {}
    for i in range(0, len(series), chunk_size):
        chunk = series[i:i+chunk_size]
        r = '|'.join('(?:' + s.re + ')' for s in chunk)
        rs[i] = re.compile(r)
    for line in open(fn):
        line = line.strip()
        for i in range(0, len(series), chunk_size):
            chunk = series[i:i+chunk_size]
            m = rs[i].match(line)
            if m:
                groups = m.groups()
                for i, s in enumerate(chunk):
                    t = groups[2*i]
                    if t:
                        d = groups[2*i+1]
                        s.data_point(t, d)

    # finish each series
    for s in series:
        s.finish()

    # our result
    return series


def series_load(formats, fn):
    dbg('loading', fn)
    try:
        for fmt in json.load(open(fn)):
            if '_inherit' in fmt:
                fmt = dict(formats[fmt['_inherit']].items() + fmt.items())
            formats[fmt['name']] = fmt
    except Exception as e:
        dbg(e)
        pass


def series_all(format_file, specs):
    formats = {}
    series_load(formats, os.path.join(os.path.dirname(__file__), 'timeseries.json'))
    series_load(formats, 'timeseries.json')
    for fn in format_file:
        series_load(formats, fn)
    return [series for spec in specs for series in series_spec(formats, spec)]


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
            {id:"c"+cnum, cx:x*width-1, cy:0.6, r:0.4, class:"circle", onclick:"del("+cnum+")"})
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
    eltend('svg', id='circles', width='%dem'%(width+2), height="1em", viewBox="0 0 %d 1" % width)
    end('td')
    end('tr')
    elt('tr')
    td('graph')
    elt('svg', id='cursors', width='%dem'%width, height='100%', viewBox='0 0 1 1',
        preserveAspectRatio='none', style='position:absolute; background:none;',
        onmousemove='move(this)', onmouseout='out(this)',  onclick='add(this)')
    elt('line', id='lll', _class='cursor', x1=0, y1=0, x2=0, y2=1)
    end('svg')
    end('td')
    end('tr')
    end('table')

#
#
#

_style = '''
    body {
        font-family: sans-serif;
        font-size: 8pt;
    }
    .data {
        text-align: right;
    }
    .desc {
        text-align: left;
    }
    .graph {
        padding-left: 1em;
        padding-right: 1em;
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
    elt('td', **{'class':cls})
    if content:
        put(*content)
        end('td')

if __name__ == '__main__':

    p = argparse.ArgumentParser()
    p.add_argument('--dbg', '-d', action='store_true')
    p.add_argument(dest='series', nargs='+')
    p.add_argument('--format-file', '-f', default=None)
    opt = p.parse_args()

    # xxx make these parameters
    width = 30
    height = 1.5
    ticks = 5
    show_empty = False
    show_zero = False
    shade = True

    series = series_all([opt.format_file], opt.series)
    tmin = min(s.tmin for s in series)
    tmax = max(s.tmax for s in series)

    def _graph(ts=None, ys=None, ymax=None):
        graph(ts=ts, tmin=tmin, tmax=tmax, width=width,
              ys=ys, ymin=0, ymax=ymax, height=height,
              ticks=ticks, shaded=shade)

    elt('html')
    elt('head')
    elt('meta', charset='utf-8')
    elt('style')
    put(graph_style)
    put(cursors_style)
    put(_style)
    end('style')
    elt('script')
    put(cursors_script % width)
    put(_script)
    end('script')
    end('head')
    elt('body', onkeypress='key()')
    elt('table', id='table', style='position:relative;')

    elt('tr')
    td('head data', 'avg')
    td('head data', 'max')
    elt('td')
    cursors_html(width)
    end('td')
    td('head desc', 'description')
    end('tr')

    for s in series:
        if s.ys.values():
            yavg = float(sum(s.ys.values())) / len(s.ys)
            if s.ymax!=0 or s.ymin!=0 or show_zero:
                elt('tr', onclick='sel(this)', _class='row')
                td('data', '%.3f' % yavg)
                td('data', '%.3f' % s.ymax)
                td('graph')
                _graph(s.ts, s.ys, s.ymax)
                end('td')
                td('desc', s.description)
                end('tr')
        elif show_empty:
            elt('tr', onclick='sel(this)', _class='row')
            td('data', 'n/a')
            td('data', 'n/a')
            td('graph')
            _graph()
            end('td')
            td('desc', s.description)
            end('tr')

    end('table')
    end('body')
    end('html')
