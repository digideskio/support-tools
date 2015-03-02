import sys
import re
import json
import collections

inp = {}
out = {}
exprs = collections.OrderedDict()

def get(*xs):
    j = jnode
    for x in xs:
        j = j[x]
    try:
        j = j['floatApprox']
    except:
        pass
    try:
        return float(j)
    except:
        return j

sep = ','

for a in ' '.join(sys.argv[1:]).split(';'):
    lhs, rhs = a.split('=')
    lhs = lhs.replace('\n', ' ').strip()
    rhs = rhs.replace('\n', ' ').strip()
    expr = ''
    while rhs:
        m = re.match(' *([a-zA-Z_\.][a-zA-Z_\. ]+) *(.*)', rhs)
        if m:
            expr += 'get("' + '","'.join(m.group(1).strip().split('.')) + '")'
            rhs = m.group(2).strip()
            continue
        m = re.match(' *([^a-zA-Z_\. ]+) *(.*)', rhs)
        if m:
            expr += m.group(1)
            rhs = m.group(2).strip()
            continue
        break
    exprs[lhs] = expr

print sep.join(exprs.keys())

for line in sys.stdin:
    try:
        jnode = json.loads(line)
    except Exception as e:
        print >>sys.stderr, 'ignoring bad line', e
        continue
    print sep.join(str(eval(exprs[lhs])) for lhs in exprs)

