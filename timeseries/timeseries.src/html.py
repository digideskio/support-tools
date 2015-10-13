import base64
import collections
import datetime as dt
import json
import math
import os
import pkgutil
import pytz

import flow
import graphing
import html
import process
import util


#
# resources
#

html_css = pkgutil.get_data(__name__, "html.css")
html_js = pkgutil.get_data(__name__, "html.js")
graphing_css = pkgutil.get_data(__name__, "graphing.css")
cursors_css = pkgutil.get_data(__name__, "cursors.css")
cursors_js = pkgutil.get_data(__name__, "cursors.js")
leaf = base64.b64encode(pkgutil.get_data(__name__, "leaf.png"))

help_all = '''
click on a graph to put down a cursor line
click on a blue disk to delete a cursor
click on a name to select a row
^N select the next row 
^P select the previous row 
n move the selected row down 
p move the selected row up 
N move the selected row to the bottom 
P move the selected row to the top 
1-9 to change detail level
'''.strip().replace('\n', '<br/>') + '<br/>';

help_server = '''
o to change overview subsampling
z to zoom in
Z to zoom out
s to save
'''.strip().replace('\n', '<br/>') + '<br/>';


#
#
#

def _get_graphs(ses, specs):

    opt = ses.opt

    if not hasattr(opt, 'after') or not opt.after: opt.after = float('-inf')
    if not hasattr(opt, 'before') or not opt.before: opt.before = float('inf')
    if not hasattr(opt, 'every'): opt.every = 0
    if type(opt.after)==str: opt.after = util.datetime_parse(opt.after)
    if type(opt.before)==str: opt.before = util.datetime_parse(opt.before)
    if type(opt.after)==dt.datetime: opt.after = util.t2f(opt.after)
    if type(opt.before)==dt.datetime: opt.before = util.t2f(opt.before)

    # parse specs, group them by file and parse type
    series = [] # all
    fns = collections.defaultdict(list) # grouped by fn
    for spec_ord, spec in enumerate(specs):
        # xxxxxxxxxxx
        #try:
            for s in graphing.get_series(ses, spec, spec_ord):
                fns[(s.fn,s.parse_type)].append(s) # xxx canonicalize filename
                series.append(s)
        # XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        #except Exception as e:
        #    util.msg(e)

    # process by file according to parse_type
    for fn, parse_type in sorted(fns):
        opt.last_time = - float('inf')
        read_func = process.__dict__['series_read_' + parse_type]
        read_func(ses, fn, fns[(fn,parse_type)], opt)
        
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

def cursors_html(ses, width, tmin, tmax, ticks):

    ses.elt('svg', {
        'id':'cursors', 'width':'%dem'%width, 'height':'100%', 'viewBox':'0 0 1 1',
        'preserveAspectRatio':'none', 'style':'position:absolute; background:none',
        'onmousemove':'move(this)', 'onmouseout':'out(this)',  'onclick':'add_cursor_by_event(this)'
    })
    ses.eltend('line', {'id':'lll', 'class':'cursor', 'x1':-1, 'y1':0, 'x2':-1, 'y2':1})
    ses.end('svg')

    ses.elt('div', {'style':'position:relative; z-index:1000; background:white; margin-bottom:0.3em'})
    ses.eltend('svg', {'id':'letters', 'width':'%dem'%width, 'height':'1em'})
    h = 0.8
    viewBox = '0 0 %g %g' % (width, h)
    ses.put('<br/>')
    ses.eltend('svg', {'id':'deleters', 'width':'%gem'%width, 'height':'%gem'%h, 'viewBox':viewBox}),
    ses.end('div')

    # add the time axis labels
    labels = []
    last_d = None
    for t in ticks:
        t = util.f2t(t)
        d = t.strftime('%y-%m-%d')
        label = d if d != last_d else ''
        last_d = d
        labels.append(label + t.strftime('<br/>%H:%M:%S'))
    graphing.labels(ses, tmin, tmax, width, 2, ticks, labels)


#
# generate a page
#

def page(ses, server=False):

    opt = ses.opt

    # state-dependent informational messages
    ses.advice = ['current detail level is <span id="current_level"></span> (hit 1-9 to change)']

    # support for save in server mode
    if server:
        ses.start_save()

    # start the page before reading the data so we can emit progress messages
    ses.elt('html')
    ses.elt('head')
    ses.eltend('meta', {'charset':'utf-8'})
    ses.eltend('link', {'rel':'icon', 'type':'image/png', 'href':'data:image/png;base64,' + leaf})
    ses.elt('style')
    ses.put(graphing_css)
    ses.put(cursors_css)
    ses.put(html_css)
    ses.end('style')
    ses.elt('script')
    ses.put(html_js)
    ses.put(cursors_js)
    ses.end('script')
    ses.end('head')
    ses.elt('body', {'onkeypress':'key()', 'onload':'initialize_model()'})
    if server:
        ses.elt('div', {'id':'progress'})
        ses.in_progress = True

    # get our graphs, reading the data
    graphs = _get_graphs(ses, ses.opt.specs)

    # set page title
    ses.eltend('script', {}, 'document.title="%s"' % ', '.join(ses.title))
    
    # handle some no-data edge cases
    if not graphs:
        ses.progress('no series specified')
        ses.endall()
        return
    try:
        opt.tmin = min(s.tmin for g in graphs for s in g if s.tmin)
        opt.tmax = max(s.tmax for g in graphs for s in g if s.tmax)
        tspan = opt.tmax - opt.tmin
    except ValueError:
        ses.progress('no data found')
        ses.endall()
        return

    # having read the data, now close off progress messages before generating the rest of the page
    if ses.in_progress:
        ses.in_progress = False
        ses.end('div') # id=progress
        ses.eltend('script', {},
                    'document.getElementById("progress").setAttribute("hidden","true")')

    # provide browser with required client-side parameters
    if not hasattr(opt, 'cursors'): opt.cursors = []
    graphing.get_time_bounds(opt)
    model_items = ['tleft', 'tright', 'cursors', 'level', 'before', 'after']
    model = dict((n, getattr(opt, n)) for n in model_items)
    #util.msg(model)
    ses.eltend('script', {}, 'model = %s' % json.dumps(model))

    # help message at the top
    ses.elt('div', {'onclick':'toggle_help()'})
    ses.put('<b>click here for help</b></br>')
    ses.elt('div', {'id':'help', 'style':'display:none'})
    ses.put(help_all)
    if server:
        ses.put(help_server)
    ses.put('<br/>')
    ses.end('div')
    ses.end('div')
    ses.put('<br/>'.join(ses.advice))
    ses.put('<br/><br/>')

    # compute stats
    spec_matches = collections.defaultdict(int)
    for graph in graphs:
        for series in graph:
            spec_matches[series.spec] += 1
    spec_empty = collections.defaultdict(int)
    spec_zero = collections.defaultdict(int)
    util.msg('start:', util.f2t(opt.tmin))
    util.msg('finish:', util.f2t(opt.tmax))
    util.msg('duration:', util.f2t(opt.tmax) - util.f2t(opt.tmin))
    if opt.duration: # in seconds
        opt.tmax = opt.tmin + timedelta(0, opt.duration)

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
    slop = 0.1 # gives us ticks near beginning or end if those aren't perfectly second-aligned
    tickmin = math.ceil((opt.tmin-slop)/tickdelta) * tickdelta
    ticks = []
    for i in range(nticks+1):
        t = tickmin + i * tickdelta
        if t > opt.tmax+slop: break
        ticks.append(t)

    # table of graphs
    ses.elt('table', {'id':'table', 'style':'position:relative;'})

    # this row holds cursor heads, cursor letters, and time labels
    ses.elt('tr')
    ses.eltend('td')
    ses.eltend('td')
    ses.elt('td')
    cursors_html(ses, opt.width, opt.tmin, opt.tmax, ticks)
    ses.end('td')
    ses.end('tr')

    # this row holds data column heads (min, max, name)
    ses.elt('tr')
    ses.td('head data', 'avg')
    ses.td('head data', 'max')
    ses.eltend('td')
    if opt.number_rows:
        ses.td('head row-number', 'row')
    ses.td('head desc', 'name')
    ses.td('', ' ')
    ses.end('tr')

    # function to emit a graph
    def emit_graph(data=[], ymax=None):
        graphing.html_graph(
            ses, data=data,
            tmin=opt.tmin, tmax=opt.tmax, width=opt.width,
            ymin=0, ymax=ymax, height=opt.height,
            #ticks=ticks, shaded=not opt.no_shade and len(data)==1)
            ticks=ticks, shaded=len(data)==1, bins=opt.bins
        )

    # colors for merged graphs
    colors = ['rgb(50,102,204)','rgb(220,57,24)','rgb(253,153,39)','rgb(20,150,24)',
              'rgb(153,20,153)', 'rgb(200,200,200)']
    def color(i):
        return colors[i] if i <len(colors) else 'black'

    # format graph name, factoring out common prefixes and common suffixes for merged graphs
    def name_td(g):
        ses.td('name')
        pfx = os.path.commonprefix([s.name for s in g])
        sfx = os.path.commonprefix([s.name[::-1] for s in g])[::-1]
        ses.put(pfx)
        if sfx != pfx:
            for i,s in enumerate(g):
                mid = ' ' + s.name[len(pfx):len(s.name)-len(sfx)]
                ses.eltend('span', {'style':'color:%s' % color(i)}, mid)
            ses.put(sfx)
        ses.end('td')

    # output each graph as a table row
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
                ses.elt('tr', {'onclick':'sel(this)', 'class':'row', '_level':graph[0].level})
                ses.td('data', '{:,.3f}'.format(float(ysum)/ylen))
                ses.td('data', '{:,.3f}'.format(ymax))
                ses.td('graph')
                graph_color = lambda graph, i: color(i) if len(graph)>1 else 'black'
                data = [(s.ts, s.ys, graph_color(graph,i)) for i,s in enumerate(graph)]
                emit_graph(data, display_ymax)
                ses.end('td')
                if opt.number_rows:
                    ses.td('row-number', str(row))
                    row += 1
                name_td(graph)
                ses.end('tr')
            else:
                util.dbg('skipping uniformly zero data for', graph[0].get('name'), 'in', graph[0].fn)
                for s in graph:
                    spec_zero[s.spec] += 1
        elif opt.show_empty:
            ses.elt('tr', {'onclick':'sel(this)', 'class':'row', '_level':graph[0].level})
            ses.td('data', 'n/a')
            ses.td('data', 'n/a')
            ses.td('graph')
            emit_graph()
            ses.end('td')
            if opt.number_rows:
                ses.td('row-number', str(row))
                row += 1
            name_td(graph)
            ses.end('tr')
        else:
            util.dbg('no data for', graph[0].get('name'), 'in', graph[0].fn)
            for s in graph:
                spec_empty[s.spec] += 1

    # close it out
    ses.end('table')
    ses.end('body')
    ses.end('html')

    for spec in opt.specs:
        util.msg('spec', repr(spec), 'matched:', spec_matches[spec],
            'zero:', spec_zero[spec], 'empty:', spec_empty[spec])

