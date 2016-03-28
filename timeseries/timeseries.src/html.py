import base64
import collections
import datetime as dt
import json
import math
import pipes
import pkgutil
import traceback

import descriptors
import graphing
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
server_js = pkgutil.get_data(__name__, "server.js")
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
'''.strip().replace('\n', '<br/>') + '<br/>'

help_server = '''
o to open new view in current window
O to open new view in new window
z to zoom in
Z to zoom out
? to get detailed displayed values at a selected time
! to get detailed raw metrics at a selected time
@ to get metadata (for example, mongod version and host info) at a selected time
m to suppress merging groups of related metrics in single graph
M to enable merging groups of related metrics (default)
RETURN to refresh view
l to enable periodic refresh of live data
s to save
'''.strip().replace('\n', '<br/>') + '<br/>'


#
#
#

# a graph is a list of series
class Graph(list):
    def __init__(self):
        self.sparse = False

def _get_graphs(ses):

    opt = ses.opt

    if not hasattr(opt, 'after') or not opt.after: opt.after = float('-inf')
    if not hasattr(opt, 'before') or not opt.before: opt.before = float('inf')
    if not hasattr(opt, 'every'): opt.every = 0
    if type(opt.after)==str: opt.after = util.datetime_parse(opt.after)
    if type(opt.before)==str: opt.before = util.datetime_parse(opt.before)
    if type(opt.after)==dt.datetime: opt.after = util.t2f(opt.after)
    if type(opt.before)==dt.datetime: opt.before = util.t2f(opt.before)

    # generate descriptors by sniffing for specs that don't have it
    specs = descriptors.sniff(ses, *opt.specs)

    # parse specs, group them by file and parser
    ses.series = [] # all
    opt.fns = collections.defaultdict(list) # grouped by fn
    for spec_ord, spec in enumerate(specs):
        try:
            for s in graphing.get_series(ses, spec, spec_ord):
                opt.fns[(s.fn,s.parser)].append(s) # xxx canonicalize filename
                ses.series.append(s)
        except Exception as e:
            # xxx should we raise exception and so abort, or carry on processing all we can?
            traceback.print_exc()
            raise Exception('error processing %s: %s' % (spec, e))
    graphing.finish(ses.series)

    # process by file according to parser
    for fn, parser in sorted(opt.fns):
        opt.last_time = - float('inf')
        process.parse_and_process(ses, fn, opt.fns[(fn,parser)], opt, parser)
        
    # finish each series
    for s in ses.series:
        s.finish()

    # sort them
    ses.series.sort(key=lambda s: s.sort_ord)

    # get graphs taking into account splits and merges
    graphs = collections.defaultdict(Graph)
    ygroups = collections.defaultdict(list)
    for s in ses.series:
        s.get_graphs(graphs, ygroups, opt)

    # compute display_ymax taking into account spec_ymax and ygroup
    for g in graphs.values():
        for s in g:
            s.display_ymax = max(s.ymax, s.spec_ymax)
    for ygroup in ygroups.values():
        ygroup_ymax = max(s.ymax for s in ygroup)
        for s in ygroup:
            s.display_ymax = max(s.display_ymax, ygroup_ymax)

    # our result
    ses.graphs = graphs.values()

    # finish if no data
    if not ses.graphs:
        ses.progress('no data found')
        return

    # duration parameter overrides tmax
    if opt.duration: # in seconds
        opt.tmax = opt.tmin + dt.timedelta(0, opt.duration)

    # compute time ranges
    opt.tmin = min(s.tmin for g in graphs.values() for s in g if s.tmin)
    opt.tmax = max(s.tmax for g in graphs.values() for s in g if s.tmax)
    opt.tspan = opt.tmax - opt.tmin

    # compute left and right edges of graphing area
    graphing.get_time_bounds(opt)

    # show times
    start_time = util.f2t(opt.tmin).strftime('%Y-%m-%d %H:%M:%SZ')
    finish_time = util.f2t(opt.tmax).strftime('%Y-%m-%d %H:%M:%SZ')
    ses.advise('start: %s, finish: %s, duration: %s' % (
        start_time, finish_time, util.f2t(opt.tmax) - util.f2t(opt.tmin)
    ))

    # compute ticks
    ranges = [1, 2.5, 5, 10, 15, 20, 30, 60] # seconds
    ranges += [r*60 for r in ranges] # minutes
    ranges += [r*3600 for r in 1, 2, 3, 4, 6, 8, 12, 24] # hours
    nticks = int(opt.width / 5)
    if nticks<1: nticks = 1
    tickdelta = opt.tspan / nticks
    for r in ranges:
        if tickdelta < r:
            tickdelta = r
            break
    # long duration (multiple days); make tickedelta an exact number of days
    if tickdelta != r:
        tickdelta = math.ceil(tickdelta / (24*3600)) * (24*3600)
    slop = 0.1 # gives us ticks near beginning or end if those aren't perfectly second-aligned
    tickmin = math.ceil((opt.tmin-slop)/tickdelta) * tickdelta
    opt.ticks = []
    for i in range(nticks+1):
        t = tickmin + i * tickdelta
        if t > opt.tmax+slop: break
        opt.ticks.append(t)



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
    ses.eltend('svg', {'id':'deleters', 'width':'%gem'%width, 'height':'%gem'%h, 'viewBox':viewBox})
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
    graphing.get_labels(ses, tmin, tmax, width, 2, ticks, labels)


#
# generate a page
#

def _head(ses):
    ses.elt('html')
    ses.elt('head')
    ses.eltend('meta', {'charset':'utf-8'})
    ses.eltend('link', {'rel':'icon', 'type':'image/png', 'href':'data:image/png;base64,' + leaf})
    ses.eltend('style', {}, graphing_css, cursors_css, html_css)
    ses.eltend('script', {}, html_js, cursors_js)
    if ses.server:
        ses.eltend('script', {}, server_js)
    ses.end('head')

def container(ses):
    _head(ses)
    ses.elt('frameset', {
        'id': 'frameset',
        'rows': '90%, 0%, 10%',
        'border': 0,
        'onload': 'load_content()',
        'onunload': "do_unload('frameset')"
    })
    ses.eltend('frame', {'name': 'content', 'frameborder': 0})
    ses.eltend('frame', {'name': 'content', 'frameborder': 0})
    ses.eltend('frame', {'id': 'progress'})
    ses.endall()
    
def load(ses):

    # start page
    ses.advice = []
    _head(ses)
    ses.elt('body', {'onload': 'loaded_progress()'})

    # get our graphs, reading the data
    try:
        _get_graphs(ses)
        ses.progress('loading page...')
    except Exception as e:
        ses.progress(str(e))
        traceback.print_exc()
        ses.graphs = None

    ses.endall()


def page(ses):

    opt = ses.opt

    # support for save in server mode
    if ses.server:
        ses.start_save()

    # in server mode graphs were alread generated in the "progress" phase
    if not ses.server:
        _get_graphs(ses)

    # start page
    _head(ses)
    ses.eltend('script', {}, 'document.title="%s"' % ', '.join(ses.title))
    ses.elt('body', {
        'onkeypress': 'key()',
        'onload': 'loaded_content()',
        #'onunload': "do_unload('body')",
    })
    
    # no data - finish with empty page and return
    if not ses.graphs:
        ses.put('NO DATA')
        ses.endall()
        return

    # compute stats
    spec_matches = collections.defaultdict(int)
    for graph in ses.graphs:
        for series in graph:
            spec_matches[series.spec] += 1
    spec_empty = collections.defaultdict(int)
    spec_zero = collections.defaultdict(int)

    # provide browser with required client-side parameters
    if not hasattr(opt, 'cursors'): opt.cursors = []
    model_items = [
        'tleft', 'tright', 'cursors', 'level', 'before', 'after', 'live', 'selected', 'scrollY',
    ]
    model = dict((n, getattr(opt, n)) for n in model_items if hasattr(opt, n))
    spec_cmdline = ' '.join(pipes.quote(s) for s in opt.specs)
    model['spec_cmdline'] = spec_cmdline
    ses.advise('viewing ' + spec_cmdline + ' (use o or O to change)')
    #util.msg(model)
    ses.eltend('script', {}, 'top.model = %s' % json.dumps(model))

    # state-dependent informational message
    ses.advise('current detail level is <span id="current_level"></span> (hit 1-9 to change)', 0)
    
    # help message at the top
    ses.elt('div', {'onclick':'toggle_help()'})
    ses.put('<b>click here for help</b></br>')
    ses.elt('div', {'id':'help', 'style':'display:none'})
    ses.put(help_all)
    if ses.server:
        ses.put(help_server)
    ses.put('<br/>')
    ses.end('div')
    ses.end('div')
    ses.put('<br/>'.join(ses.advice))
    ses.put('<br/><br/>')

    # table of graphs
    ses.elt('table', {'id':'table', 'style':'position:relative;'})

    # this row holds cursor heads, cursor letters, and time labels
    ses.elt('tr')
    ses.eltend('td')
    ses.eltend('td')
    ses.elt('td')
    cursors_html(ses, opt.width, opt.tmin, opt.tmax, opt.ticks)
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
    def emit_graph(data, ymax=None, sparse=False):
        graphing.html_graph(
            ses, data=data,
            tmin=opt.tmin, tmax=opt.tmax, width=opt.width,
            ymin=0, ymax=ymax, height=opt.height,
            #ticks=ticks, shaded=not opt.no_shade and len(data)==1)
            ticks=opt.ticks, shaded=len(data)==1, bins=opt.bins,
            sparse=sparse
        )

    # colors for merged graphs
    colors = ['rgb(50,102,204)','rgb(220,57,24)','rgb(253,153,39)','rgb(20,150,24)',
              'rgb(153,20,153)', 'rgb(200,200,200)']
    def color(i):
        return colors[i] if i <len(colors) else 'black'

    # word-by-word common prefix
    # used to factor out common prefix and suffix in merged graph names
    def commonprefix(names):
        pfx = []
        for words in zip(*[n.split() for n in names]):
            if all(w==words[0] for w in words):
                pfx.append(words[0])
            else:
                break
        return ' '.join(pfx)

    # format graph name, factoring out common prefixes and common suffixes for merged graphs
    def name_td(g):
        ses.td('name')
        pfx = commonprefix([s.name for s in g])
        sfx = commonprefix([s.name[::-1] for s in g])[::-1]
        ses.put(pfx)
        if sfx != pfx:
            for i,s in enumerate(g):
                mid = ' ' + s.name[len(pfx):len(s.name)-len(sfx)]
                ses.eltend('span', {'style':'color:%s' % color(i)}, mid)
            ses.put(sfx)
        ses.end('td')

    # determine which graphs to show, suppressing empty and uniformly zero if desired
    # emit placeholders (graph==None, generating empty tr) to facilitate maintaining order
    rows = []
    for graph in sorted(ses.graphs, key=lambda g: g[0].sort_ord):
        graph.sort(key=lambda s: s.sort_ord)
        graph.ymin = min(s.ymin for s in graph)
        graph.ymax = max(s.ymax for s in graph)
        graph.ysum = sum(s.ysum for s in graph)
        graph.wrapped = any(s.wrapped for s in graph)
        graph.ylen = sum(len(s.ys) for s in graph)
        graph.display_ymax = max(s.display_ymax for s in graph)
        if graph.ylen:
            if graph.ymax!=0 or graph.ymin!=0 or opt.show_zero:
                rows.append(graph)
            else:
                rows.append(None) # placeholder
                util.dbg('skipping uniformly zero data for', graph[0].get('name'), 'in', graph[0].fn)
                for s in graph:
                    spec_zero[s.spec] += 1
        elif opt.show_empty:
            rows.append(graph)
        else:
            rows.append(None) # placeholder
            util.dbg('no data for', graph[0].get('name'), 'in', graph[0].fn)
            for s in graph:
                spec_empty[s.spec] += 1

    # emit html for graphs we are showing, in the requested order
    if hasattr(opt,'row_order') and len(opt.row_order)==len(rows):
        row_order = opt.row_order
    else:
        row_order = range(len(rows))    
    for row in row_order:
        graph = rows[row]
        if graph==None: # placeholder
            ses.eltend('tr', {
                'class': 'row',
                '_level': 1000,
                '_row': row,
            })
        elif graph.ylen:
            ses.elt('tr', {
                'onclick': 'sel(this)',
                'class': 'row',
                '_level': graph[0].level,
                '_row': row,
            })
            avg = '{:,.3f}'.format(float(graph.ysum)/graph.ylen) if not graph.wrapped else 'WRAPPED'
            ses.td('data', avg)
            ses.td('data', '{:,.3f}'.format(graph.ymax))
            ses.td('graph')
            graph_color = lambda graph, i: color(i) if len(graph)>1 else 'black'
            data = [(s.ts, s.ys, graph_color(graph,i)) for i,s in enumerate(graph)]
            emit_graph(data, graph.display_ymax, graph.sparse)
            ses.end('td')
            if opt.number_rows:
                ses.td('row-number', str(row))
            row += 1
            name_td(graph)
            ses.end('tr')
        else:
            ses.elt('tr', {'onclick':'sel(this)', 'class':'row', '_level':graph[0].level})
            ses.td('data', 'n/a')
            ses.td('data', 'n/a')
            ses.td('graph')
            emit_graph([])
            ses.end('td')
            if opt.number_rows:
                ses.td('row-number', str(row))
            name_td(graph)
            ses.end('tr')

    # close it out
    ses.endall()

    for spec in opt.specs:
        util.msg('spec', repr(spec), 'matched:', spec_matches[spec],
            'zero:', spec_zero[spec], 'empty:', spec_empty[spec])


def raw(ses, t, kind='info'):

    _head(ses)
    ses.elt('pre', {'class': 'info'})

    for fn, parser in sorted(ses.opt.fns):
        parser.info(ses, fn, t, kind)

    ses.endall()


def info(ses, t):

    _head(ses)
    ses.put('data as displayed at %s<br/><br/>\n' % util.f2s(t))
    ses.elt('table')

    for s in ses.series:
        for name, value in s.info(ses, t):
            ses.elt('tr')
            ses.td('info-data', '{:,.3f}'.format(value))
            ses.td('desc', name)
            ses.end('tr')

    ses.end('table')

