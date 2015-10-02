import collections
import datetime as dt
import math
import os
import pkgutil
import pytz

import graphing
import process
import util


#
# resources
#

html_css = pkgutil.get_data("__main__", "html.css")
html_js = pkgutil.get_data("__main__", "html.js")
graphing_css = pkgutil.get_data("__main__", "graphing.css")
cursors_css = pkgutil.get_data("__main__", "cursors.css")
cursors_js = pkgutil.get_data("__main__", "cursors.js")

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

def _get_graphs(specs, opt):

    if not hasattr(opt, 'after') or not opt.after: opt.after = pytz.utc.localize(dt.datetime.min)
    if not hasattr(opt, 'before') or not opt.before: opt.before = pytz.utc.localize(dt.datetime.max)
    if not hasattr(opt, 'every'): opt.every = 0
    if type(opt.after)==str: opt.after = util.datetime_parse(opt.after)
    if type(opt.before)==str: opt.before = util.datetime_parse(opt.before)
    if type(opt.after)==dt.datetime: opt.after = util.t2f(opt.after)
    if type(opt.before)==dt.datetime: opt.before = util.t2f(opt.before)

    # parse specs, group them by file and parse type
    series = [] # all
    fns = collections.defaultdict(list) # grouped by fn
    for spec_ord, spec in enumerate(specs):
        try:
            for s in graphing.get_series(spec, spec_ord, opt):
                fns[(s.fn,s.parse_type)].append(s) # xxx canonicalize filename
                series.append(s)
        except Exception as e:
            util.msg(e)

    # process by file according to parse_type
    for fn, parse_type in sorted(fns):
        opt.last_time = - float('inf')
        read_func = process.__dict__['series_read_' + parse_type]
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

def cursors_html(width, tmin, tmax, ticks):

    util.elt('svg', {
        'id':'cursors', 'width':'%dem'%width, 'height':'100%', 'viewBox':'0 0 1 1',
        'preserveAspectRatio':'none', 'style':'position:absolute; background:none',
        'onmousemove':'move(this)', 'onmouseout':'out(this)',  'onclick':'add(this)'
    })
    util.elt('line', {'id':'lll', 'class':'cursor', 'x1':-1, 'y1':0, 'x2':-1, 'y2':1})
    util.end('svg')

    util.elt('div', {'style':'position:relative; z-index:1000; background:white; margin-bottom:0.3em'})
    util.eltend('svg', {'id':'letters', 'width':'%dem'%width, 'height':'1em'})
    h = 0.8
    viewBox = '0 0 %g %g' % (width, h)
    util.put('<br/>')
    util.eltend('svg', {'id':'deleters', 'width':'%gem'%width, 'height':'%gem'%h, 'viewBox':viewBox}),
    util.end('div')

    graphing.labels(tmin, tmax, width, ticks, [util.f2t(t).strftime('%H:%M:%S') for t in ticks])



#
#
#

def main(opt):

    # just list?
    if opt.list:
        for desc in sorted(descriptors, key=lambda desc: desc['name'].lower()):
            d = collections.defaultdict(lambda: '...')
            d.update(desc)
            util.msg(get(d, 'name'))
        return

    # get our graphs
    graphs = _get_graphs(opt.specs, opt)
    if not graphs:
        util.msg('no series specified')
        return
    try:
        tmin = min(s.tmin for g in graphs for s in g if s.tmin)
        tmax = max(s.tmax for g in graphs for s in g if s.tmax)
        tspan = tmax - tmin
    except ValueError:
        util.msg('no data found')
        return

    # stats
    spec_matches = collections.defaultdict(int)
    for graph in graphs:
        for series in graph:
            spec_matches[series.spec] += 1
    spec_empty = collections.defaultdict(int)
    spec_zero = collections.defaultdict(int)

    util.msg('start:', util.f2t(tmin))
    util.msg('finish:', util.f2t(tmax))


    util.msg('duration:', util.f2t(tmax) - util.f2t(tmin))
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
    tickmin = math.ceil(tmin/tickdelta) * tickdelta
    ticks = []
    for i in range(nticks+1):
        t = tickmin + i * tickdelta
        if t > tmax: break
        ticks.append(t)

    def _graph(data=[], ymax=None):
        graphing.html_graph(
            data=data,
            tmin=tmin, tmax=tmax, width=opt.width,
            ymin=0, ymax=ymax, height=opt.height,
            #ticks=ticks, shaded=not opt.no_shade and len(data)==1)
            ticks=ticks, shaded=len(data)==1, bins=opt.bins
        )

    util.elt('html')
    util.elt('head')
    util.elt('meta', {'charset':'utf-8'})
    util.elt('style')
    util.put(graphing_css)
    util.put(cursors_css)
    util.put(html_css)
    util.end('style')
    util.elt('script')
    util.put(cursors_js % opt.width)
    util.put(html_js)
    util.end('script')
    util.end('head')
    util.elt('body', {'onkeypress':'key()', 'onload':'initial_level(%d)'%opt.level})

    util.elt('div', {'onclick':'toggle_help()'})
    util.put('1-9 to choose detail level; current level: <span id="current_level"></span><br/>')
    util.put('click to toggle more help')
    util.eltend('div', {'id':'help', 'style':'display:none'}, _help)
    util.end('div')
    util.put('</br>')

    util.elt('table', {'id':'table', 'style':'position:relative;'})
    util.elt('tr')
    util.td('head data', 'avg')
    util.td('head data', 'max')
    util.elt('td')
    cursors_html(opt.width, tmin, tmax, ticks)
    util.end('td')
    if opt.number_rows:
        util.td('head row-number', 'row')
    util.td('head desc', 'name')
    util.end('tr')

    colors = ['rgb(50,102,204)','rgb(220,57,24)','rgb(253,153,39)','rgb(20,150,24)',
              'rgb(153,20,153)', 'rgb(200,200,200)']

    def color(i):
        return colors[i] if i <len(colors) else 'black'

    def name_td(g):
        util.td('name')
        pfx = os.path.commonprefix([s.name for s in g])
        sfx = os.path.commonprefix([s.name[::-1] for s in g])[::-1]
        util.put(pfx)
        if sfx != pfx:
            for i,s in enumerate(g):
                mid = ' ' + s.name[len(pfx):len(s.name)-len(sfx)]
                util.eltend('span', {'style':'color:%s' % color(i)}, mid)
            util.put(sfx)
        util.end('td')

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
                util.elt('tr', {'onclick':'sel(this)', 'class':'row', '_level':graph[0].level})
                util.td('data', '{:,.3f}'.format(float(ysum)/ylen))
                util.td('data', '{:,.3f}'.format(ymax))
                util.td('graph')
                graph_color = lambda graph, i: color(i) if len(graph)>1 else 'black'
                data = [(s.ts, s.ys, graph_color(graph,i)) for i,s in enumerate(graph)]
                _graph(data, display_ymax)
                util.end('td')
                if opt.number_rows:
                    util.td('row-number', str(row))
                    row += 1
                name_td(graph)
                util.end('tr')
            else:
                util.dbg('skipping uniformly zero data for', graph[0].get('name'), 'in', graph[0].fn)
                for s in graph:
                    spec_zero[s.spec] += 1
        elif opt.show_empty:
            util.elt('tr', {'onclick':'sel(this)', 'class':'row', '_level':graph[0].level})
            util.td('data', 'n/a')
            util.td('data', 'n/a')
            util.td('graph')
            _graph()
            util.end('td')
            if opt.number_rows:
                util.td('row-number', str(row))
                row += 1
            name_td(graph)
            util.end('tr')
        else:
            util.dbg('no data for', graph[0].get('name'), 'in', graph[0].fn)
            for s in graph:
                spec_empty[s.spec] += 1

    util.end('table')
    util.end('body')
    util.end('html')

    for spec in opt.specs:
        util.msg('spec', repr(spec), 'matched:', spec_matches[spec],
            'zero:', spec_zero[spec], 'empty:', spec_empty[spec])



