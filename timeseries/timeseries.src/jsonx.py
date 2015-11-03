import json
import traceback

import ftdc
import util


class File(util.Cache):

    def __init__(self, fn):
        self.fn = fn
        self.chunks = []

    def get_chunks(self, ses):
        if self.chunks:
            for chunk in util.item_progress(ses, self.fn, 'chunks', self.chunks, len(self.chunks)):
                yield chunk
        else:
            for chunk in self._get_chunks(ses):
                self.chunks.append(chunk)
                yield chunk

    def _get_chunks(self, ses):

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
        for line in util.file_progress(ses, self.fn):
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
                # ignore bad json
                pass
            except:
                traceback.print_exc()
                break
        yield metrics


def read(ses, fn, opt):
    f = File.get(fn)
    for metrics in f.get_chunks(ses):
        yield metrics

