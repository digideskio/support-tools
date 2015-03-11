import sys
import re
import json
import collections
import argparse

inp = {}
out = {}
exprs = collections.OrderedDict()

def json2csv(args):

    def _get(j, *xs):
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
    
    def get(*xs):
        return _get(jnode, *xs)
    
    def delta(*xs):
        return _get(jnode, *xs) - _get(last_jnode, *xs) if last_jnode else 0
    
    sep = ','

    for stmt in ';'.join(args).split(';'):
        stmt = stmt.replace('\n', ' ').strip()
        if not stmt:
            continue
        dbg(stmt)
        lhs, rhs = stmt.split('=')
        lhs = lhs.strip()
        rhs = rhs.strip()
        expr = ''
        while rhs:
            m = re.match(" *([a-zA-Z_\.][a-zA-Z0-9_\. ']*) *(.*)", rhs)
            if m:
                var = m.group(1).strip()
                if var.endswith("'"):
                    fun = 'delta'
                    var = var[:-1]
                else:
                    fun = 'get'
                expr += fun + '("' + '","'.join(var.split('.')) + '")'
                rhs = m.group(2).strip()
                continue
            m = re.match(' *([^a-zA-Z_ ]+) *(.*)', rhs)
            if m:
                expr += ' ' + m.group(1) + ' '
                rhs = m.group(2).strip()
                continue
            break
        dbg(lhs, '=', expr)
        exprs[lhs] = expr
    
    print sep.join(exprs.keys())
    
    def ev(locals):
        for lhs in exprs:
            try:
                v = eval(exprs[lhs], locals)
                jnode[lhs] = v
                yield str(v)
            except Exception as e:
                yield ''

    last_jnode = None
    for line in sys.stdin:
        try:
            jnode = json.loads(line)
        except Exception as e:
            print >>sys.stderr, 'ignoring bad line', e
            continue
        print sep.join(v for v in ev(locals()))
        last_jnode = jnode

def list_json():
    def p(j, s):
        if type(j)==dict:
            for n in j:
                ss = s
                if n != 'floatApprox':
                    if ss: ss += '.'
                    ss += n
                p(j[n], ss)
        else:
            print s
    for line in sys.stdin:
        try:
            jnode = json.loads(line)
        except Exception as e:
            print >>sys.stderr, 'ignoring bad line', e
            continue
        p(jnode, '')
        break

parser = argparse.ArgumentParser()
parser.add_argument('--list', '-l', action='store_true')
parser.add_argument('--dbg', '-d', action='store_true')
parser.add_argument('exprs', nargs='*')
opt = parser.parse_args()

def dbg(*s):
    if opt.dbg:
        sys.stderr.write(' '.join(s) + '\n')

if opt.list:
    list_json()
else:
    json2csv(opt.exprs)


