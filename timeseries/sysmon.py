import time
import datetime
import re
import sys
import os

delay = float(sys.argv[1]) if len(sys.argv)>1 else 1.0

stat_fields = {
    'cpu': ['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal', 'guest', 'guest_nice'],
    'page': ['in', 'out'],
    'swap': ['in', 'out'],
}

disk_fields = [
    'reads',
    'reads_merged',
    'read_sectors',
    'read_time_ms',
    'writes',
    'writes_merged',
    'write_sectors',
    'write_time_ms',
    'io_in_progress',
    'io_time_ms',
    'io_queued_ms',
]

sys_block = '/sys/block'
block_devs = []

for fn in os.listdir(sys_block):
    try: os.stat('%s/%s/partition' % (sys_block, fn))
    except OSError: block_devs.append(fn)


first = True

while True:

    # timestamp
    t = datetime.datetime.utcnow().isoformat() + 'Z'
    nvs = [('time', t)]

    # cpu
    cpus = 0
    for line in open('/proc/stat'):
        line = line.split()
        if line[0] in stat_fields:
            for n, v in zip(stat_fields[line[0]], line[1:]):
                nvs.append((line[0] + '_' + n, v))
        elif re.match('cpu[0-9]+', line[0]):
            cpus += 1
        elif len(line)==2:
            nvs.append((line[0], line[1]))
    nvs.append(('cpus', str(cpus)))

    # disk
    if first:
        active_devs = []
        for bd in block_devs:
            line = open('%s/%s/stat' % (sys_block, bd)).read().split()
            if not all(v=='0' for v in line):
                active_devs.append(bd)
    for bd in active_devs:
        line = open('%s/%s/stat' % (sys_block, bd)).read().split()
        nvs += zip((bd + '.' + f for f in disk_fields), line)

    # header
    if first:
        print ','.join(n for n,v in nvs)
        first = False

    # data
    print ','.join(v for n,v in nvs)
    sys.stdout.flush()

    # delay
    time.sleep(delay)





