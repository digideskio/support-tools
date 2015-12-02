import argparse
import sys
import traceback

import descriptors
import flow
import util

#
#
#

def get_opt(args=sys.argv[1:]):

    p = argparse.ArgumentParser()
    p.add_argument('--dbg', '-d', action='store_true')
    p.add_argument(dest='specs', nargs='*')
    #p.add_argument('--descriptor-file', '-f', default=None)
    p.add_argument('--width', type=float, default=30)
    p.add_argument('--height', type=float, default=1.8)
    p.add_argument('--show-empty', action='store_true')
    p.add_argument('--show-zero', action='store_true')
    #p.add_argument('--no-shade', action='store_true')
    p.add_argument('--no-merges', action='store_false', dest='merges')
    p.add_argument('--number-rows', action='store_true')
    p.add_argument('--duration', type=float, default=None)
    p.add_argument('--after')
    p.add_argument('--before')
    p.add_argument('--itz', type=float, default=None)
    p.add_argument('--every', type=float, default=0)
    p.add_argument('--relative', action='store_true')
    p.add_argument('--list', action='store_true')
    p.add_argument('--level', type=int, default=1)
    p.add_argument('--bins', type=int, default=25)
    p.add_argument('--profile', action='store_true')
    p.add_argument('--overview', default='heuristic')
    p.add_argument('--server', action='store_true')
    p.add_argument('--browser', action='store_true')
    p.add_argument('--port', type=int, default=8888)
    p.add_argument('--connect', type=str)
    p.add_argument('--live', type=int, default=0)
    # might be useful: --cursors time,... 
    return p.parse_args(args)


def main():

    opt = get_opt()
    if opt.dbg:
        util.do_dbg = True

    # just list?
    if opt.list:
        descriptors.list_descriptors()
        return

    if opt.profile:
        # pip install -e git+https://github.com/joerick/pyinstrument.git#egg=pyinstrument
        # pylint: disable=import-error
        import pyinstrument, codecs
        p = pyinstrument.Profiler()
        p.start()
        flow.main(opt)
        p.stop()
        out = codecs.getwriter('UTF-8')(sys.stderr)
        out.write(p.output_text(unicode=True, color=True))
    else:
        flow.main(opt)

if __name__ == '__main__':
    try:
        main()
    except:
        traceback.print_exc()
