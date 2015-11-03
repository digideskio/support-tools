import json
import traceback

import ftdc
import util

def read(ses, fn, opt):

    ignore = set(['floatApprox', '$date', '$numberLong', '$timestamp'])
    chunk_size = 100

    def flatten(result, j, key=None):
        if type(j)==dict:
            for k, v in j.items():
                if k in ignore:
                    flatten(result, v, key)
                else:
                    flatten(result, v, key + ftdc.SEP + k if key else k)
        else:
            result[key] = [j]
        return result

    metrics = {}
    for line in util.progress(ses, fn):
        try:
            j = flatten({}, json.loads(line))
            if j.keys() != metrics.keys() or len(metrics.values()[0]) >= chunk_size:
                if metrics:
                    yield metrics
                metrics = j
            else:
                for k, v in j.items():
                    metrics[k].extend(v)
        except ValueError:
            pass
        except:
            traceback.print_exc()
            break
    yield metrics

