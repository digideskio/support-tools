import sys

from collections import defaultdict

#
# process the output of perf malloc tracing into a form
# that can be visualized by the calltree tool
#

#
#
#

in_progress = {}               # alloc_start waiting for alloc_finish, by pid
ptrs = {}                      # (size, allocating stack) for each ptr
allocated = defaultdict(int)   # cumulative size for each stack
#last_shown = defaultdict(int) # last shown size for each stack

total_size = 0
max_size = 0
last_size = 0
finish_no_start = 0
free_no_alloc = 0

sep = ';'
MB = 1024.0 * 1024.0

def trace_begin():
    print '# metric=MB format=%.3f'
    print 'time;MB;stack'

def output_sample(all=False):
    for stack in allocated:
        print str(last_t) + sep + str(allocated[stack]/MB) + sep + stack
        #if allocated_size != last_shown[stack]:
        #last_shown[stack] = allocated_size
            

def accumulate(t, size, stack):

    global total_size, max_size, last_size, last_t

    # output previous sample if it may have been the global max
    #if total_size==max_size and size<0 and last_size!=max_size:
    #    output_sample()
    #    last_size = total_size

    # new size charged to stack
    allocated_size = allocated[stack] + size
    if allocated_size:
        allocated[stack] = allocated_size
    else:
        del allocated[stack]

    # running stats
    total_size += size
    max_size = max(total_size, max_size)
    last_t = t

    # output this sample if total size has changed by more than a given proportion
    if abs(total_size-last_size) > 0.02 * max_size:
        output_sample(True)
        last_size = total_size

def trace_end():
    output_sample(True)
    print >>sys.stderr, 'finish_no_start:', finish_no_start, 'free_no_alloc:', free_no_alloc
    print >>sys.stderr, 'max_size:', max_size


#
#
#

def show_stack(callchain):
    return sep.join(frame['sym']['name'] for frame in callchain if 'sym' in frame)

def alloc_start(pid, size, callchain):
    #print >>sys.stderrr, 'alloc_start'
    in_progress[pid] = (size, callchain)

def alloc_finish(pid, ptr, prog, secs, nsecs, callchain):
    #print >>sys.stderrr, 'alloc_finish', prog, callchain
    try:
        t = secs + 1e-9 * nsecs
        size, callchain = in_progress[pid]
        stack = prog
        for frame in reversed(callchain):
            try:
                stack += sep + frame['sym']['name']
            except:
                pass
        del in_progress[pid]
        ptrs[ptr] = (-size, stack)
        accumulate(t, size, stack)
    except KeyError:
        #print >>sys.stderr, 'alloc_finish with no alloc_start', pid, ptr, show_stack(callchain)
        global finish_no_start
        finish_no_start += 1


def free(ptr, secs, nsecs, callchain):
    if ptr:
        try:
            size, stack = ptrs[ptr]
            t = secs + 1e-9 * nsecs
            accumulate(t, size, stack)
        except KeyError:
            global free_no_alloc
            free_no_alloc += 1
            #print >>sys.stderr, 'free without alloc', ptr, show_stack(callchain)


#
#
#

def probe_mongod__alloc(
    event_name, context, common_cpu, common_secs, common_nsecs,
    common_pid, common_comm, common_callchain, __probe_ip, size
):
    alloc_start(common_pid, size, common_callchain)

def probe_mongod__allocRET(
    event_name, context, common_cpu, common_secs, common_nsecs,
    common_pid, common_comm, common_callchain, __probe_func, __probe_ret_ip, ptr
):
    alloc_finish(common_pid, ptr, common_comm, common_secs, common_nsecs, common_callchain)

#
#
#

def probe_mongod__free(
    event_name, context, common_cpu, common_secs, common_nsecs,
    common_pid, common_comm, common_callchain, __probe_ip, ptr
):
    free(ptr, common_secs, common_nsecs, common_callchain)


#
#
#


for i in range(10):
    fns = [f for f in globals().keys() if f.startswith('probe_mongod__')]
    for f in fns:
           globals()[f+'_'+str(i)] = globals()[f]





#
#
#

def probe_mongod__calloc(
    event_name, context, common_cpu, common_secs, common_nsecs,
    common_pid, common_comm, common_callchain, __probe_ip, n, elem_size
):
    alloc_start(common_pid, n * elem_size, common_callchain)

def probe_mongod__callocRET(
    event_name, context, common_cpu, common_secs, common_nsecs, common_pid,
    common_comm, common_callchain, __probe_func, __probe_ret_ip, ptr
):
    alloc_finish(common_pid, ptr, common_comm, common_secs, common_nsecs)

#
#
#

def probe_mongod__realloc(
    event_name, context, common_cpu, common_secs, common_nsecs,
    common_pid, common_comm, common_callchain, __probe_ip, ptr, size
):
    free(ptr, common_secs, common_nsecs, common_callchain)
    alloc_start(common_pid, size, common_callchain)

def probe_mongod__reallocRET(
    event_name, context, common_cpu, common_secs, common_nsecs, common_pid,
    common_comm, common_callchain, __probe_func, __probe_ret_ip, ptr
):
    alloc_finish(common_pid, ptr, common_comm, common_secs, common_nsecs, common_callchain)


#
#
#

def trace_unhandled(event_name, context, event_fields_dict):
    print event_name
    print ' '.join(['%s=%s'%(k,str(v))for k,v in sorted(event_fields_dict.items())])
    return

