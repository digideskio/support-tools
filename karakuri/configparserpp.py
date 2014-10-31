import argparse


class ConfigParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(ConfigParser, self).__init__(*args, **kwargs)

    def convert_arg_line_to_args(self, line):
        args = line.split()
        for i in range(len(args)):
            if i == 0:
                # ignore commented lines
                if args[i][0] == '#':
                    break
                if not args[i].startswith('--'):
                    # add '--' to simulate cli option
                    args[i] = "--%s" % args[i]
            if not args[i].strip():
                continue

            yield args[i]
