import collections
import json
import re

import ftdc
import util


################################################################################
#
# each read_* generator reads files of a given type
# and yields a sequence of parsed data structures
# useable as a src for transfer(src, *dst)
#

def read_csv(ses, fn, opt):
    for line in util.progress(ses, fn):
        yield [s.strip(' \n"') for s in line.split(',')]


# handle special names inserted by javascript JSON.stringify()
def json_fixup(j):
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
                json_fixup(v)
            elif type(v)==list:
                json_fixup(v)
    elif type(j)==list:
        for jj in j:
            json_fixup(jj)
            


def read_json(ses, fn, opt):
    for line in util.progress(ses, fn):
        if line.startswith('{'):
            try:
                jnode = json.loads(line)
                json_fixup(jnode)
                yield jnode
            except Exception as e:
                util.msg('ignoring bad line', e)


def read_lines(ses, fn, opt):
    return util.progress(ses, fn)

def read_metrics(ses, fn, opt):
    return ftdc.read(ses, fn, opt)



################################################################################
#
# each series_process_* generator accepts data of a given type
# and generates graphs from the data as determined by the series arg
# useable as a dst for transfer(src, *dst)
# 

# process metrics dictionaries, each representing e.g a single chunk from an ftdc file
# each dictionary maps a list of metric names, e.g. paths through a json metrics sample doc,
# to a list of metric values
def series_process_dict(series, opt):

    # to track metrics present in the data but not processed by any series
    unrecognized = set()

    # process all metrics that we are sent
    while True:

        try:

            # get our next input
            metrics = yield

            # we don't support these (yet) so we don't support:
            #     things that depend on set_field, like "joins per closure"
            #     auto-splits (but there are none of these currently for ftdc)
            getitem = None
            setitem = None
                
            # send each series our data points
            for s in series:
                data = s.dict_fields['data'] # e.g. 'serverStatus.uptime'
                time = s.dict_fields['time'] # e.g. 'serverStatus.localTime'
                if data in metrics:
                    for t, d in zip(metrics[time], metrics[data]):
                        t = t / 1000.0 # times come to us as ms, so convert to seconds here
                        if t>=opt.after and t<=opt.before:
                            s.data_point(t, d, getitem, setitem, opt)

            # track what we have used
            unrecognized.update(metrics.keys())

        except GeneratorExit:
            break

    # compute and print unrecognized metrics
    ignore = re.compile(
        '^serverStatus.(repl|start|end)|'
        '^local.oplog.rs|'
        '^replSetGetStatus|slot_closure_rate'
    )
    for s in series:
        unrecognized.discard(s.dict_fields['data'])
        unrecognized.discard(s.dict_fields['time'])
    unrecognized = sorted(u for u in unrecognized if not ignore.match(u))
    if unrecognized:
        util.msg('unrecognized metrics:')
        for u in unrecognized:
            util.msg('   ', u)

#
# process a sequence of json metric documents
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
    pt = util.parse_time()
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
                if fname=='time':
                    value = pt.parse_time(jnode, opt, pnode[fname][0])
                else:
                    value = jnode
                if value is not None:
                    for s in pnode[fname]:
                        result[s][fname] = value

    # process lines
    while True:
        try:
            jnode = yield
        except GeneratorExit:
            break
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
            except KeyError:
                pass

    # report on unmatched json paths
    if unmatched:
        util.msg('unmatched in', fn)
        for t in sorted(unmatched):
            util.msg('  ', [str(tt) for tt in t])

#
# process a series of fields such as produce by reading a csv file
# first element of sequenc is list of field names
# subsequent elements are field values matching the field names
#
def series_process_fields(series, opt):
    field_names = None
    pt = util.parse_time()
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
                t = pt.parse_time(field_values[time_field], opt, s)
                if not t:
                    break
                for i, (field_name, field_value) in enumerate(zip(field_names, field_values)):
                    if i != time_field and field_value not in ('', None):
                        m = re.match(s.field_name, field_name)
                        if m:
                            field_dict.update(m.groupdict())
                            getitem = field_dict.__getitem__
                            setitem = field_dict.__setitem__
                            field_value = s.data_point(t, field_value, getitem, setitem, opt)
                            field_dict[field_name] = field_value # xxx use set_field instead?

#
# process a series of lines using regexps
#
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
        #util.dbg(chunk_re)
        chunk_re = re.compile(chunk_re)
        chunks.append((chunk_re, chunk, chunk_groups))


    # process the file
    last_time = None
    pt = util.parse_time()
    while True:
        line = yield
        line = line.strip()
        for chunk_re, chunk, chunk_groups in chunks:
            m = chunk_re.match(line)
            if m:
                for chunk_group, s_re in zip(chunk_groups, chunk):
                    def get_field(g):
                        try: return m.group(chunk_group+g+1) if type(g)==int else m.group(g)
                        except Exception as e: raise Exception(g + ': ' + e.message)
                    for s in series_by_re[s_re]:
                        t = get_field(s.re_time)
                        if t:
                            t = pt.parse_time(t, opt, s)
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
# replica set status
# do special-case computation of repl set lag here to produce a sequence of samples
# then delegate to the generic series_process_fields
#
def series_process_rs(series, opt):

    # delegate to generic field processor
    p = init_dst(series_process_fields(series, opt))

    # wait for a config with members
    jnode = yield
    while not 'members' in jnode:
        jnode = yield

    # compute and send headers
    jnode = yield
    headers = ['time']
    if 'members' in jnode:
        for m in jnode['members']:
            name = m['name']
            for s in ['state', 'lag']:
                headers.append(name + ' ' + s)
    p.send(headers)

    while True:

        # next json doc
        jnode = yield
        
        # still a valid config?
        if 'members' in jnode:

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
                secondary_optime = m['optime']['t']
                if primary_optime and secondary_optime > 1:
                    result.append(primary_optime - secondary_optime)
                else:
                    result.append('')

        # send result to field processor
        p.send(result)


#
# transfer(src, *dst) pulls data from src and pushes it to each *dst
# as a convenience we init each dst with .next
#

def init_dst(d):
    d.next()
    return d

def transfer(src, *dst):
    ds = [init_dst(d) for d in dst]
    for x in src:
        for d in ds:
            d.send(x)
    for d in ds:
        d.close()

#
# each series_read_* routine processes and generates graphs from a file of a given type
# typically implemented by glueing a source and a destination together using transfer(src, *dst)
#

# lines of text parsed using regexps
def series_read_re(ses, fn, series, opt):
    src = read_lines(ses, fn, opt)
    dst = series_process_re(series, opt)
    transfer(src, dst)

# json docs
def series_read_json(ses, fn, series, opt):
    src = read_json(ses, fn, opt)
    dst = series_process_json(fn, series, opt)
    transfer(src, dst)

def series_read_csv(ses, fn, series, opt):
    src = read_csv(ses, fn, opt)
    dst = series_process_fields(series, opt)
    transfer(src, dst)
    
def series_read_rs(ses, fn, series, opt):
    transfer(read_json(ses, fn, opt), series_process_rs(series, opt))


#
# ftdc processing
# demultiplex the embedded streams:
#     series_process_json processes serverStatus
#     series_process_rs does special-case processing (e.g. replica lag) for replSetGetStatus
#

def series_read_ftdc_json(ses, fn, series, opt):
    ss = init_dst(series_process_json(fn, series, opt))
    rs = init_dst(series_process_rs(series, opt))
    for jnode in read_json(ses, fn, opt):
        if 'serverStatus' in jnode:
            ss.send(jnode['serverStatus'])
        if 'replSetGetStatus' in jnode:
            rs.send(jnode['replSetGetStatus'])

    #dst = [series_process_json(fn, series, opt), series_process_rs(series, opt)]
    #transfer(read_json(fn, opt), *dst)

def series_read_ftdc_dict(ses, fn, series, opt):
    #FTDC(fn).dbg(); return # for timing
    src = read_metrics(ses, fn, opt)
    dst = series_process_dict(series, opt)
    transfer(src, dst)
    # TBD: implement rs lag computation

