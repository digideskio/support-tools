import json
import sys
import os
import collections
import re
import datetime
import dateutil.parser

def elt(name, **attrs):
    sys.stdout.write('<%s' % name)
    for a in attrs:
        sys.stdout.write(' %s="%s"' % (a, attrs[a]))
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

def graph(
    ts=None, tmin=None, tmax=None, width=None,
    ys=None, ymin=None, ymax=None, height=1,
    ticks=None, line_width=0.1, shaded=True
):
    elt('svg', width='%gem' % width, height='%gem' % height,
        viewBox='0 0 %g %g' % (width, height))
    if ts:
        tspan = (tmax-tmin).total_seconds()
        yspan = (ymax - ymin)* (1+1e-10)
        if yspan==0:
            ymin -= 1
            yspan = 1
        ypad = 1.5 * line_width
        gx = lambda t: (t-tmin).total_seconds() / tspan * width
        gy = lambda y: (1.0 - (float(y)-ymin) / yspan) * (height-ypad) + ypad/2
        line = ' '.join('%g,%g' % (gx(t), gy(ys[t])) for t in ts)
        if shaded:
            shade = '0,1.05 ' + line + ' %d,1.05' % width
            eltend('polygon', points=shade, style='fill:rgb(230,230,230); stroke:none;')
        eltend('polyline', points=line, style='fill:none; stroke:black; stroke-width:0.1')
        if ticks:
            for i in range(ticks+1):
                x = width * i / ticks
                style = 'stroke:rgba(255,0,0,0.2); stroke-width:0.1'
                eltend('line', x1=x, x2=x, y1=0, y2=height, style=style)
    eltend('line', x1=0, x2=1, y1=0, y2=1, style='stroke:red, stroke-width:10')
    end('svg')

#
#
#

def op_for(fmt, s):
    if s=='max': return lambda ys, t, d: max(ys[t], d)
    if s=='count':
        count_min_ms = float(fmt.get("count_min_ms", 0))
        return lambda ys, t, d: ys[t]+1 if d>=count_min_ms else ys[t]

def series_one(formats, series):

    fmt_name, fn = series.split(':',2)
    fmt_name_params = fmt_name.split('(')
    fmt_name = fmt_name_params[0]
    fmt = formats[fmt_name]
    if len(fmt_name_params)>1:
        params = fmt_name_params[1].strip(' )')
        params = params.split(',')
        for p in params:
            n, v = p.split('=')
            fmt[n] = v
    description = fmt.get('description', fmt_name).format(**fmt)

    delta = fmt.get('delta', False)
    if delta:
        last_t = None

    buckets = float(fmt.get('bucket_size', 0))
    if buckets:
        t0 = dateutil.parser.parse('2000-01-01')
        op = op_for(fmt, fmt['bucket_op'])

    queue = fmt.get('queue', False)
    if queue:
        queue_times = []
        queue_min_ms = float(fmt.get('queue_min_ms', 0))

    ts = []
    ys = collections.defaultdict(int)

    for line in open(fn):
        line = line.strip()
        m = re.search(fmt['re'], line)
        if m:
            t, d = m.groups()
            t, d = dateutil.parser.parse(t), float(d)
            if delta:
                if last_t:
                    ts.append(t)
                    ys[t] = (d-last_d) / (t-last_t).total_seconds()
                last_t = t
                last_d = d
            elif buckets:
                s0 = (t - t0).total_seconds()
                s1 = s0 // buckets * buckets
                t = t + datetime.timedelta(0, s1-s0)
                ys[t] = op(ys, t, d)
            elif queue:
                if d>queue_min_ms:
                    ms = datetime.timedelta(0, d/1000.0)
                    queue_times.append((t-ms,+1))
                    queue_times.append((t,-1))
            else:
                ts.append(t)
                ys[t] = d

    if buckets:
        tmin = min(ys.keys())
        tmax = max(ys.keys())
        n = int((tmax-tmin).total_seconds() / buckets)
        dt = datetime.timedelta(0, buckets)
        ts = [tmin + dt*i for i in range(n+1)]
    elif queue:
        q = 0
        for t, d in sorted(queue_times):
            q += d
            ys[t] = q
            ts.append(t)

    return description, ts, ys

def series_load(formats, fn):
    try:
        for fmt in json.load(open(fn)):
            formats[fmt['name']] = fmt
    except Exception as e:
        #print >>sys.stderr, e
        pass

def series_all(specs):
    formats = {}
    series_load(formats, os.path.join(os.path.dirname(__file__), 'timeseries.json'))
    series_load(formats, 'timeseries.json')
    return [series_one(formats, s) for s in specs]


#
#
#

style = '''
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
'''
        
def td(cls, *content):
    elt('td', **{'class':cls})
    if content:
        put(*content)
        end('td')

if __name__ == '__main__':

    width = 30
    height = 1.5
    ticks = 5

    series = series_all(sys.argv[1:])
    tmin = min(min(ts) for _, ts, _ in series)
    tmax = max(max(ts) for _, ts, _ in series)

    elt('html')
    elt('head')
    elt('meta', charset='utf-8')
    elt('style')
    put(style)
    end('style')
    end('head')
    elt('body')
    elt('table')

    elt('tr')
    td('head data', 'avg')
    td('head data', 'max')
    td('head graph')
    graph(width=width, height=height)
    end('td')
    td('head desc', 'description')
    end('tr')

    for label, ts, ys in series:
        ymax = max(ys.values())
        yavg = float(sum(ys.values())) / len(ys)
        elt('tr')
        td('data', '%g' % yavg)
        td('data', '%g' % ymax)
        td('graph')
        graph(
            ts=ts, tmin=tmin, tmax=tmax, width=width,
            ys=ys, ymin=0, ymax=ymax, height=height,
            ticks=ticks, shaded=False
        )
        end('td')
        td('desc', label)
        end('tr')

    end('table')
    end('body')
    end('html')
