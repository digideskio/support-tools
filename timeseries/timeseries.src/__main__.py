import argparse

import html

#
#
#

if __name__ == '__main__':

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
    p.add_argument('--every', type=float, default=0)
    p.add_argument('--relative', action='store_true')
    p.add_argument('--list', action='store_true')
    p.add_argument('--level', type=int, default=1)
    p.add_argument('--bins', type=int, default=25)
    p.add_argument('--progress-every', type=int, default=10000)
    p.add_argument('--profile', action='store_true')
    p.add_argument('--overview', default='heuristic')
    opt = p.parse_args()

    if opt.profile:
        # pip install -e git+https://github.com/joerick/pyinstrument.git#egg=pyinstrument
        import pyinstrument, codecs, locale
        p = pyinstrument.Profiler()
        p.start()
        html.main(opt)
        p.stop()
        out = codecs.getwriter('UTF-8')(sys.stderr)
        out.write(p.output_text(unicode=True, color=True))
    else:
        html.main(opt)

