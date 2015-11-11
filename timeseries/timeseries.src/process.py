import collections
import re
import traceback

import ftdc
import jsonx
import util


################################################################################
#
# each read_* generator reads files of a given type
# and yields a sequence of parsed data structures
# useable as a src for transfer(src, *dst)
#

def read_csv(ses, fn, opt):
    for line in util.file_progress(ses, fn):
        yield [s.strip(' \n"') for s in line.split(',')]


#
# read json files
# yields flat dictionaries like {'json/path/key': value}
#
def read_json(ses, fn, opt):
    return jsonx.read(ses, fn, opt)

#
# read lines from a file
# yields strings
#
def read_lines(ses, fn, opt):
    return util.file_progress(ses, fn)

#
# read ftdc metrics files
# yields flat dictionaries
#
def read_metrics(ses, fn, opt):
    return ftdc.read(ses, fn, opt)

def info_metrics(ses, fn, t):
    def prt(*stuff):
        ses.put(' '.join(str(s) for s in stuff) + '\n')
    ftdc.info(ses, fn, t, prt)


################################################################################
#
# each series_process_* generator accepts data of a given type
# and generates graphs from the data as determined by the series arg
# useable as a dst for transfer(src, *dst)
# 

# process metrics dictionaries, each representing e.g a single chunk from an ftdc file
# each dictionary maps a list of metric names, e.g. paths through a json metrics sample doc,
# to a list of metric values
def series_process_flat(series, opt):

    # to track metrics present in the data but not processed by any series
    unrecognized = set()

    # process all metrics that we are sent
    while True:

        try:

            # get our next input
            metrics = yield
                    
            def process_series(s, data_key):
                time_key = s.flat_time_key # e.g. 'serverStatus.localTime'
                if data_key in metrics and time_key in metrics:
                    ts = metrics[time_key]
                    if type(ts[0])==str or type(ts[0])==unicode:
                        for i, t in enumerate(ts):
                            ts[i] = util.t2f(util.datetime_parse(t))
                    if ts[0]/s.time_scale > opt.before or ts[-1]/s.time_scale < opt.after:
                        return
                    for i, (t, d) in enumerate(zip(metrics[time_key], metrics[data_key])):
                        t = t / s.time_scale
                        if t>=opt.after and t<=opt.before:
                            get_field = lambda key: metrics[key][i]
                            s.data_point(t, d, get_field, None, opt)

            # send each series our data points
            for s in series:
                if s.special:
                    s.special(metrics)
                if s.split_on_key_match:
                    for data_key in metrics:
                        m = s.split_on_key_match_re.match(data_key)
                        if m:
                            description = m.groupdict()
                            ss = s.get_split(data_key, description)
                            process_series(ss, data_key)
                else:
                    process_series(s, s.flat_data_key)

            # track what we have used
            unrecognized.update(metrics.keys())

        except GeneratorExit:
            break

        except:
            traceback.print_exc()
            break

    # compute and print unrecognized metrics
    ignore = re.compile(
        '^serverStatus.(repl|start|end)|'
        '^local.oplog.rs|'
        '^replSetGetStatus|slot_closure_rate'
    )
    for s in series:
        unrecognized.discard(s.flat_data_key)
        unrecognized.discard(s.flat_time_key)
    unrecognized = filter(lambda x: not ignore.match(x), unrecognized)
    is_str = lambda x: type(x)==str or type(x)==unicode
    unrecognized = filter(lambda x: x in metrics and not is_str(metrics[x][0]), unrecognized)
    if unrecognized:
        util.msg('unrecognized metrics:')
        for u in sorted(unrecognized):
            util.msg('   ', u)

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
    dst = series_process_flat(series, opt)
    transfer(src, dst)

def series_read_csv(ses, fn, series, opt):
    src = read_csv(ses, fn, opt)
    dst = series_process_fields(series, opt)
    transfer(src, dst)
    
def series_read_metrics(ses, fn, series, opt):
    src = read_metrics(ses, fn, opt)
    dst = series_process_flat(series, opt)
    transfer(src, dst)
    # TBD: implement rs lag computation

def series_info_metrics(ses, fn, t):
    info_metrics(ses, fn, t)
