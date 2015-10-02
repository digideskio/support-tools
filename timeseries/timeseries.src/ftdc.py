import collections
import mmap
import os
import struct
import zlib

import util


#
# basic bson parser, to be extended as needed
# has special handling for ftdc:
#     returns numeric types as int64
#     ignores non-metric fields
# returns result as tree of OrderedDict, preserving order
#

int32 = struct.Struct('<i')
uint32 = struct.Struct('<I')
int64 = struct.Struct('<q')
uint64 = struct.Struct('<Q')
double = struct.Struct('<d')

BSON = collections.OrderedDict

def read_bson_doc(buf, at, ftdc=False):
    doc = BSON()
    doc_len = int32.unpack_from(buf, at)[0]
    doc.bson_len = doc_len
    doc_end = at + doc_len
    at += 4
    while at < doc_end:
        bson_type = ord(buf[at])
        at += 1
        name_end = buf.find('\0', at)
        n = buf[at : name_end]
        at = name_end + 1
        if bson_type==0: # eoo
            return doc
        elif bson_type==1: # double
            v = double.unpack_from(buf, at)[0]
            if ftdc: v = int(v)
            l = 8
        elif bson_type==2: # string
            l = uint32.unpack_from(buf, at)[0]
            at += 4
            v = buf[at : at+l-1] if not ftdc else None
        elif bson_type==3: # subdoc
            v = read_bson_doc(buf, at, ftdc)
            l = v.bson_len
        elif bson_type==4: # array
            v = read_bson_doc(buf, at, ftdc)
            l = v.bson_len
            if not ftdc: v = v.values() # return as array
        elif bson_type==8: # bool
            v = ord(buf[at])
            l = 1
        elif bson_type==5: # bindata
            l = uint32.unpack_from(buf, at)[0]
            at += 5 # length plus subtype
            v = buf[at : at+l] if not ftdc else None
        elif bson_type==7: # objectid
            v = None # xxx always ignore for now
            l = 12
        elif bson_type==9: # datetime
            v = uint64.unpack_from(buf, at)[0]
            v = int(v) if ftdc else v / 1000.0
            l = 8
        elif bson_type==16: # int32
            v = int32.unpack_from(buf, at)[0]
            if ftdc: v = int(v)
            l = 4
        elif bson_type==17: # timestamp
            v = BSON()
            v['t'] = int(uint32.unpack_from(buf, at)[0]) # seconds
            v['i'] = int(uint32.unpack_from(buf, at+4)[0]) # increment
            l = 8
        elif bson_type==18: # int64
            v = int(int64.unpack_from(buf, at)[0])
            l = 8
        else:
            raise Exception('unknown type %d(%x) at %d(%x)' % (bson_type, bson_type, at, at))
        if v != None:
            doc[n] = v
        at += l
    assert(not 'eoo not found') # should have seen an eoo and returned


class FTDC:

    def read_chunk(self, chunk_doc):
    
        # map from metric names to list of values for each metric
        # metric names are paths through the sample document
        metrics = collections.OrderedDict()
        metrics._id = chunk_doc['_id']
    
        # decompress chunk data field
        data = chunk_doc['data']
        data = data[4:] # skip uncompressed length, we don't need it
        data = zlib.decompress(data)
    
        # read reference doc from chunk data, ignoring non-metric fields
        ref_doc = read_bson_doc(data, 0, ftdc=True)
    
        # traverse the reference document and extract metric names
        def extract_names(doc, n=''):
            for k, v in doc.items():
                nn = n + '.' + k if n else k
                if type(v) == BSON:
                    extract_names(v, nn)
                else:
                    metrics[nn] = [v]
        extract_names(ref_doc)
    
        # get nmetrics, ndeltas
        nmetrics = uint32.unpack_from(data, ref_doc.bson_len)[0]
        ndeltas = uint32.unpack_from(data, ref_doc.bson_len+4)[0]
        at = ref_doc.bson_len + 8
        if nmetrics != len(metrics):
            # xxx remove when SERVER-20602 is fixed
            util.msg('ignoring bad chunk: nmetrics=%d, len(metrics)=%d' % (nmetrics, len(metrics)))
            return None
        #assert(nmetrics==len(metrics))
        self.read_samples += ndeltas+1
    
        # overview mode returns a subset of the samples, aiming for each sample to represent
        # the same number of bytes of compressed data,
        # except that we return at least one sample for each chunk
        if self.overview:
            bytes = self.total_bytes / self.overview
            if bytes==0:
                every = 1
            else:
                max_samples = (self.read_bytes+chunk_doc.bson_len) / bytes - self.read_bytes / bytes
                if max_samples==0:
                    return metrics
                elif max_samples==1:
                    return metrics
                else:
                    every = max((ndeltas+1)/max_samples, 1)
        else:
            every = 1

        # unpacks ftdc packed ints
        def unpack(data, at):
            res = 0
            shift = 0
            while True:
                b = ord(data[at])
                res |= (b&0x7F) << shift
                at += 1
                if not (b&0x80):
                    if res > 0x7fffffffffffffff: # negative 64-bit value
                        res = int(res-0x10000000000000000)
                    return res, at
                shift += 7
    
        # unpack, run-length, delta, transpose the metrics
        nzeroes = 0
        for metric_values in metrics.values():
            value = metric_values[-1]
            for n in xrange(1,ndeltas+1):
                if nzeroes:
                    delta = 0
                    nzeroes -= 1
                else:
                    delta, at = unpack(data, at)
                    if delta==0:
                        nzeroes, at = unpack(data, at)
                value += delta
                if n%every==0:
                    metric_values.append(value)
        assert(at==len(data))
    
        # our result
        return metrics


    def report_progress(self):
        util.msg('%d chunks, %d samples, %d bytes (%.0f%%), %d bytes/sample; %d samples out' % (
            self.read_chunks, self.read_samples, self.read_bytes, 
            100.0*self.read_bytes/self.total_bytes, self.read_bytes/self.read_samples,
            self.out_samples
        ))

    def read_file(self, fn):

        f = open(fn)
        buf = mmap.mmap(f.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)
        at = 0

        while at < len(buf):

            # read doc
            try:
                chunk_doc = read_bson_doc(buf, at)
            except Exception as e:
                self.report_progress()
                util.msg('stopping at bad bson doc (%s)' % e)
                return

            # decode the chunk, if any
            if chunk_doc['type']==1:
                metrics = self.read_chunk(chunk_doc)
                if metrics:
                    out_samples = len(metrics.values()[0])
                    self.out_samples += out_samples
                    #util.msg('chunk at=%d len=%d out=%d' % (at, chunk_doc.bson_len, out_samples))
                    yield metrics
            at += chunk_doc.bson_len

            # progress
            self.read_chunks += 1
            self.read_bytes += chunk_doc.bson_len
            if self.read_chunks%10 == 0 or self.read_bytes == self.total_bytes:
                self.report_progress()

        # bson docs should exactly cover file
        assert(at==len(buf))

    # read a file, yielding a sequence of chunks
    # this does minimal actual work since it mmaps the files
    # and only needs to read a few bytes for each chunk to construct
    # the chunk bson document, consisting largely of pointers into the file
    def read_file(self, fn):

        # open file
        f = open(fn)
        buf = mmap.mmap(f.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)
        at = 0

        # traverse the file
        while at < len(buf):

            # read doc
            try:
                chunk_doc = read_bson_doc(buf, at)
                at += chunk_doc.bson_len
                yield chunk_doc
            except Exception as e:
                util.msg('stopping at bad bson doc (%s)' % e)
                return

        # bson docs should exactly cover file
        assert(at==len(buf))


    # reads the chunks specified by the parameters to __init__
    # yields a sequence of metrics dictionaries
    def read(self):

        # we already filtered self.filtered_chunk_docs by type and time range
        for chunk_doc in self.filtered_chunk_docs:

            # read the chunk
            metrics = self.read_chunk(chunk_doc)
            if metrics:
                out_samples = len(metrics.values()[0])
                self.out_samples += out_samples
                #util.msg('chunk at=%d len=%d out=%d' % (at, chunk_doc.bson_len, out_samples))
                yield metrics
    
            # progress
            self.read_chunks += 1
            self.read_bytes += chunk_doc.bson_len
            if self.read_chunks%10 == 0 or self.read_bytes == self.total_bytes:
                self.report_progress()

    def dbg(self, show=False):
        def pt(t):
            return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(t/1000)) + ('.%03d' % (t%1000))
        for metrics in self.read():
            if show:
                if 'serverStatus.localTime' in metrics:
                    sslt = metrics['serverStatus.localTime']
                    util.msg(metrics._id, pt(metrics._id), pt(sslt[0]), pt(sslt[-1]),
                             'ds', len(sslt), 'ms', len(metrics))
                else:
                    #print 'no serverStatus.localTime'
                    util.msg(metrics.keys())

    def __init__(self, fn, opt):

        # metrics files start with 'metrics.'
        is_ftdc_file = lambda fn: os.path.basename(fn).startswith('metrics.')

        # get list of metrics files
        if os.path.isdir(fn):
            fns = [os.path.join(fn,f) for f in sorted(os.listdir(fn)) if is_ftdc_file(f)]
        elif is_ftdc_file(fn):
            fns = [fn]
        else:
            fns = []
        if not fns:
            raise Exception(fn + ' is not an ftdc file or directory')

        # load chunks, keeping type 1 metric chunks
        # per comment with read_file this does minimal actual work
        chunk_docs = []
        for fn in fns:
            for chunk_doc in self.read_file(fn):
                if chunk_doc['type']==1:
                    chunk_docs.append(chunk_doc)

        # compute time ranges for each chunk using _id timestamp
        for i in range(len(chunk_docs)):
            t = chunk_docs[i]['_id']
            fudge = -300 # xxx _id is end instead of start; remove when SERVER-20582 is fixed
            chunk_docs[i].start_time = t + fudge
            if i>0:
                chunk_docs[i-1].end_time = t
        chunk_docs[-1].end_time = float('inf') # don't know end time; will filter last chunk later

        # roughly filter by timespan using _id timestamp as extracted above
        # fine filtering will be done in series_process_dict
        in_range = lambda c: c.start_time <= opt.before and c.end_time >= opt.after
        self.filtered_chunk_docs = [c for c in chunk_docs if in_range(c)]

        # init stats for progress report
        self.total_bytes = sum(c.bson_len for c in self.filtered_chunk_docs)
        self.read_chunks = 0
        self.read_samples = 0
        self.read_bytes = 0
        self.out_samples = 0

        # compute number of output samples desired for overview mode
        # uses time-filtered data sizes so resolution automatically increases for smaller timespans
        # xxx need better heuristic that avoids step function?
        if opt.overview=='heuristic':
            self.overview = 10000 if self.total_bytes<10000000 else 1000
            util.msg('limiting output to %d samples; use --overview none to override' % self.overview)
        elif opt.overview=='none':
            self.overview = None
        else:
            self.overview = int(opt.overview)


