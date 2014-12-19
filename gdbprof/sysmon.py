import time
import datetime
import re
import sys

delay = float(sys.argv[1]) if len(sys.argv)>1 else 1.0

stat_fields = {
    'cpu': ['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal', 'guest', 'guest_nice'],
    'page': ['in', 'out'],
    'swap': ['in', 'out'],
}

first = True

while True:
    t = datetime.datetime.utcnow().isoformat() + 'Z'
    nvs = [('time', t)]
    cpus = 0
    for line in open('/proc/stat'):
        line = line.split()
        if line[0] in stat_fields:
            for n, v in zip(stat_fields[line[0]], line[1:]):
                nvs.append(('stat_' + line[0] + '_' + n, v))
        elif re.match('cpu[0-9]+', line[0]):
            cpus += 1
        elif len(line)==2:
            nvs.append(('stat_' + line[0], line[1]))
    nvs.append(('stat_cpu_cpus', str(cpus)))
    if first:
        print ','.join(nv[0] for nv in nvs)
        first = False
    print ','.join(nv[1] for nv in nvs)
    time.sleep(delay)
    
