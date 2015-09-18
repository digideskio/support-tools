#define STATIC_LIBMONGOCLIENT

#include "mongo/client/dbclient.h" 
#include <algorithm>
#include <boost/algorithm/string.hpp>
#include <boost/iostreams/copy.hpp>
#include <boost/iostreams/device/back_inserter.hpp>
#include <boost/iostreams/filter/zlib.hpp>
#include <boost/iostreams/filtering_streambuf.hpp>
#include <cstdlib>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <math.h>
#include <string>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>

using namespace std;
using namespace mongo;
using namespace boost;


//
// helpers
//

int verbosity = 2;

ostream& msg(int v) {
    static struct nullstream : std::ostream {
        nullstream() : std::ios(0), std::ostream(0) {}
    } nullstream;
    return verbosity>=v? cerr : nullstream;
}

double now() {
    struct timeval t;
    gettimeofday(&t, NULL);
    return t.tv_sec + t.tv_usec*1e-6;
}

void sleep(double t) {
    struct timespec ts;
    ts.tv_sec = (int) t;
    ts.tv_nsec = (int) ((t - ts.tv_sec) * 1e9);
    nanosleep(&ts, NULL);
}

Date_t now_ms() {
    struct timeval t;
    gettimeofday(&t, NULL);
    return Date_t(t.tv_sec*1000 + t.tv_usec/1000);
}

void err(string s, bool with_errno=true) {
    msg(0) << "error: " << s;
    if (with_errno)
        msg(0) << ": " << strerror(errno);
    msg(0) << endl;
    exit(-1);
}

class SpaceStats {

    string name;
    int n_samples;
    size_t n_bytes;

public:

    SpaceStats(string name) {
        msg(1) << name << endl;
        this->name = name;
        n_samples = 0;
        n_bytes = 0;
    }

    void record_sample(int ns, int nb) {
        n_samples += ns;
        n_bytes += nb;
    }

    ~SpaceStats() {
        msg(1) << name << " " << n_samples << " samples";
        if (n_samples)
            msg(1) << ", " << n_bytes << " bytes, " << (n_bytes/n_samples) << " bytes/sample";
        msg(1) << endl;
    }        
};

class TimeStats {

    string name;
    double t_start;
    double t_total;
    double t_max;
    double t_min;
    int n_samples;

public:

    TimeStats(string name) {
        this->name = name;
        n_samples = 0;
        t_total = 0;
        t_max = 0;
        t_min = 1.0 / 0.0;
    }

    void start() {
        t_start = now();
    }

    void stop(int ns = 1) {
        double t = now() - t_start;
        t_total += t;
        if (t > t_max) t_max = t;
        if (t < t_min) t_min = t;
        n_samples += ns;
    }

    double avg() {
        return t_total / n_samples;
    }

    double min() {
        return t_min;
    }

    ~TimeStats() {
        int t_avg_us = int(avg() * 1e6);
        int t_max_us = int(t_max * 1e6);
        int t_min_us = int(t_min * 1e6);
        msg(1) << name << " " << n_samples << " samples";
        if (n_samples)
            msg(1) << ", " << t_min_us << " µs min, " << 
                t_avg_us << " µs avg, " << t_max_us << " µs max ";
        msg(1) << endl;
    }        
};


//
// basic types
//

// metrics are represented as int64
// this loses range from doubles and requires that they be ints
// but avoids having to consider a change of numeric type a schema change
typedef int64_t METRIC;

// deltas are represented as int64 also
// using a smaller type here doesn't help any if we are doing packing
typedef int64_t DELTA;
//typedef int64_t DELTA;
//typedef int32_t DELTA;
//typedef int16_t DELTA;


//
// options for measuring impact on compression
//
// NO_COMP - disable zlib compression
// NO_PACK - disable packing deltas into variable-length ints
// NO_RUN - disable rle of runs of 0s
//

#ifndef NO_COMP
int z_level = 6;
//int z_level = 9;
#else
int z_level = 0;
#endif

#ifndef NO_PACK
template<class> struct PACK;
typedef PACK<char> pack;
#else
struct NOPACK;
typedef NOPACK pack;
#endif

#ifndef NO_RUN
static const bool run_length = true;
#else
static const bool run_length = false;
#endif


//
// PACK<T> packs an integer into a variable length integer coding
// T - unit of packed result
//

template<class T> struct PACK {

    static const int shift = sizeof(T)*8 - 1; // 7
    static const int more = 1 << shift; // 0x80
    static const T mask = (T)~more; // 0x7f
    static const int max = (sizeof(DELTA)*8 + shift-1) / shift * sizeof(T);

    // pack an integer
    // i - integer to pack
    // p - buffer to pack into
    // on return p is advanced by length of packed result
    static void pack(char*& p, DELTA i) {
        T* pp = (T*) p;
        uint64_t u = (uint64_t) i;
        while (u >= more) {
            *pp++ = (u & mask) | more;
            u >>= shift;
        }
        *pp++ = u & mask;
        p = (char*) pp;
    }

    // unpack an integer
    // i - resulting unpacked integer
    // p - buffer to unpack from
    // on return p is advanced by length of packed input
    static void unpack(char*& p, DELTA& i) {
        i = 0;
        DELTA b;
        int s = 0;
        T* pp = (T*) p;
        do {
            b = *pp++;
            i |= (b & mask) << s;
            s += shift;
        } while (b & more);
        p = (char*) pp;
    }
};

struct NOPACK {

    static const int max = sizeof(DELTA);

    static void pack(char*& p, DELTA i) {
        *(DELTA*)p = i;
        p += sizeof(DELTA);
    }

    static void unpack(char*& p, DELTA& i) {
        i = *(DELTA*)p;
        p += sizeof(DELTA);
    }
};


//
// extract numeric metrics from a sample, while comparing schema against a reference sample
//
// ref - reference sample
// curr - current sample to extract metrics from and compare with reference sample
// metrics - fills this vector with extracted metrics
// matches - returns true if schema of curr matces ref
//

void extract_metrics(const BSONObj& ref, const BSONObj& curr, vector<METRIC>& metrics, bool& matches, string indent = "") {

    BSONObjIterator i_curr(curr);
    BSONObjIterator i_ref(ref);

    while (i_curr.more()) {

        // schema mismatch if curr is longer than ref
        if (matches && !i_ref.more()) {
            msg(3) << "schema change: curr longer than ref" << endl;
            matches = false;
        }

        BSONElement e_curr = i_curr.next();
        BSONElement e_ref = matches? i_ref.next() : BSONElement();

        msg(4) << "e_curr: " << indent << e_curr.fieldName() << endl;

        if (matches) {

            // check for matching field names
            if (strcmp(e_ref.fieldName(), e_curr.fieldName())!=0 ) {
                msg(3) << "schema change: field name change " << e_ref.fieldName() << " "
                       << e_curr.fieldName() << endl;
                matches = false;
            }

            // check that types match, allowing any numeric type to match any other numeric type
            // this looseness is necessary because some metrics use varying numeric types,
            // and if that was considered a schema mismatch
            // it would increase the number of reference samples required
            if ((e_curr.type() != e_ref.type()) && (e_curr.isNumber() != e_ref.isNumber())) {
                msg(3) << "schema change: field type change " << e_ref.fieldName() << " "
                       <<  e_ref.type() << " " << e_curr.type() << endl;
                matches = false;
            }
        }

        switch (e_curr.type()) {

        // all numeric types are extracted as long (int64)
        // this supports the loose schema matching mentioned above,
        // but does create a range issue for doubles, and requires doubles to be integer
        case NumberDouble:
        case NumberInt:
        case NumberLong:
            metrics.push_back(e_curr.numberLong());
            break;

        case Bool:
            metrics.push_back(e_curr.Bool());
            break;

        case Date:
            metrics.push_back(e_curr.Date());
            break;

        case Timestamp:
            // very slightly more space efficient to treat these as two separate metrics
            metrics.push_back(e_curr.Timestamp().seconds());
            metrics.push_back(e_curr.Timestamp().increment());
            break;

        case Object:
        case Array:
            extract_metrics(matches? e_ref.Obj() : BSONObj(), e_curr.Obj(), metrics, matches, indent + "    ");
            break;

        // strings and objectids are not captured in the delta samples
        case jstOID:
        case String:
            break;

        default:
            if (matches && e_curr != e_ref) {
                msg(3) << "schema change: e_curr != e_ref" << endl;
                msg(3) << "e_curr " << e_curr << endl;
                msg(3) << "e_ref " << e_ref << endl;
                matches = false;
            }
            break;
        }

    }

    // schema mismatch if ref is longer than curr
    if (matches && i_ref.more()) {
        msg(3) << "schema change: ref longer than curr" << endl;
        matches = false;
    }
}


//
// construct a sample from decompressed metrics following the schema of a reference sample
//
// ref - the reference sample
// b - result following the schema of the reference sample will be constructed here
// metrics - the decompressed metrics to insert into the result
// at - current position in metrics
//

void _insert_metrics(const BSONObj& ref, BSONObjBuilder& b, vector<METRIC>& metrics, int& at) {

    BSONObjIterator i(ref);
    while (i.more()) {

        BSONElement e = i.next();

        switch (e.type()) {

        case NumberDouble:
        case NumberInt:
        case NumberLong:
            b.append(e.fieldName(), (long long)metrics[at++]);
            break;

        case Bool:
            b.append(e.fieldName(), (bool)metrics[at++]);
            break;

        case Date:
            b.append(e.fieldName(), Date_t(metrics[at++]));
            break;

        case Timestamp: {
            uint64_t seconds = metrics[at++];
            uint64_t increment = metrics[at++];
            b.appendTimestamp(e.fieldName(), Timestamp_t(seconds, increment));
            break;
        }

        case Object: {
            BSONObjBuilder sub(b.subobjStart(e.fieldName()));
            _insert_metrics(e.Obj(), sub, metrics, at);
            break;
        }

        case Array: {
            BSONObjBuilder sub(b.subarrayStart(e.fieldName()));
            _insert_metrics(e.Obj(), sub, metrics, at);
            break;
        }

        default:
            b.append(e);
            break;
        }
    }
}

BSONObj insert_metrics(BSONObj& ref, vector<METRIC>& metrics) {
    int at = 0;
    BSONObjBuilder b;
    _insert_metrics(ref, b, metrics, at);
    return b.obj();
}


//
// 
//

// Callback for each accumulated chunk
class DataSink {
public:
    virtual void push_chunk(char* buf, char* end, Date_t id) = 0;
};

// Compress handles accumulating samples into chunks and compressing them
class Compress {
private:

    BSONObj ref;
    Date_t ref_id;

    scoped_ptr<vector<METRIC> > prev_metrics;
    scoped_ptr<vector<METRIC> > curr_metrics;

    int max_deltas;
    int chunk_update_size;
    int n_deltas;
    int n_metrics;
    int n_samples;
    int n_bytes;
    int n_chunks;
    scoped_array<DELTA> deltas;

    DataSink* sink;

    TimeStats put_sample_timer; // put_sample_timer()
    TimeStats push_compression_timer; // compression portion of push()
    TimeStats push_chunk_timer; // push_chunk()

    void push(bool interim) {

        if (ref.isEmpty())
            return;

        // timer for compression portion
        push_compression_timer.start();

        // set up compression
        vector<char> out;
        scoped_ptr<boost::iostreams::filtering_ostreambuf>
            z(new boost::iostreams::filtering_ostreambuf());
        boost::iostreams::zlib_params zlp(z_level); // xxx parameter
        z->push(boost::iostreams::zlib_compressor(zlp));
        z->push(boost::iostreams::back_insert_device<vector<char> >(out));

        // put ref sample
        z->sputn(ref.objdata(), ref.objsize());

        // deltas if there are any
        z->sputn((const char *)&n_metrics, sizeof(n_metrics));
        z->sputn((const char *)&n_deltas, sizeof(n_deltas));

        // transpose, run-length encode, pack, and compress the deltas
        char buf[2 * n_deltas * pack::max];
        char* end = buf + sizeof(buf);
        int n_zeroes = 0;
        for (int i=0; i<n_metrics; i++) {

            // pack into buf
            char* p = buf;

            // transpose, run-length encode and pack
            for (int j=0; j<n_deltas; j++) {
                DELTA delta = deltas[i*max_deltas + j];
                if (delta!=0 || !run_length) {
                    if (n_zeroes) {
                        pack::pack(p, 0);
                        pack::pack(p, n_zeroes-1);
                        n_zeroes = 0;
                    }
                    pack::pack(p, delta);
                } else {
                    n_zeroes += 1;
                }
            }
            if (i==n_metrics-1 && n_zeroes) {
                pack::pack(p, 0);
                pack::pack(p, n_zeroes-1);
            }
            assert(p <= end);

            // compress
            uint32_t sz = p - buf;
            z->sputn(buf, sz);
        }

        // finalize compression
        z.reset();

        // timing
        push_compression_timer.stop();

        // return data to caller if requested
        if (sink) {
            push_chunk_timer.start();
            sink->push_chunk(out.data(), out.data() + out.size(), ref_id);
            push_chunk_timer.stop();
        }

        // stats
        int ns = n_deltas + 1;
        msg(interim? 3 : 2) << "pushed " << (interim? "interim" : "finished") << " chunk, "
                            << ns << " sample(s), " << out.size() << " bytes, "
                            <<  (out.size() / ns) << " bytes/sample" << endl;

        // reset if this was the last update to this chunk
        if (!interim) {
            ref = BSONObj();
            ref_id = 0;
            n_deltas = 0;
        }
    }

public:

    //
    // Compress handles accumulating samples into chunks and compressing them
    // sink - callback for each compressed chunk
    // chunk_size - maximum number of samples per chunk
    //
    Compress(DataSink* sink, int chunk_size = 300, int chunk_update_size = 0) :
        put_sample_timer("put sample"),
        push_compression_timer("compression"),
        push_chunk_timer("push data")
    {

        prev_metrics.reset(new vector<METRIC>);
        curr_metrics.reset(new vector<METRIC>);

        this->sink = sink;

        max_deltas = chunk_size - 1;
        this->chunk_update_size = chunk_update_size;
        n_metrics = 0;
        n_deltas = 0;
    }

    //
    // add a sample to the current chunk
    // curr_sample - sample to add
    // id - id supplied by caller; if 0 id will be supplied when pushed
    //
    void put_sample(BSONObj curr_sample, Date_t id = 0) {
        
        // start timer for put_sample
        put_sample_timer.start();

        // get metrics from current sample
        curr_metrics->clear();
        bool matches = !ref.isEmpty();
        extract_metrics(ref, curr_sample, *curr_metrics, matches);

        // schema change, so can't use deltas; finish off what we have
        if (!matches)
            push(false);

        if (ref.isEmpty()) {

            // ref sample: remember it, and allocate space for deltas
            ref = curr_sample.getOwned();
            ref_id = id;
            n_metrics = curr_metrics->size();
            deltas.reset(new DELTA[n_metrics * max_deltas]);
            n_deltas = 0;

        } else {

            // not ref sample - compute deltas
            for (int i=0; i<n_metrics; i++)
                deltas[n_deltas + i*max_deltas] = (*curr_metrics)[i] - (*prev_metrics)[i];
            n_deltas += 1;
        }

        // push what we have
        if (n_deltas==max_deltas)
            push(false);
        else if (chunk_update_size && (n_deltas+1)%chunk_update_size==0)
            push(true);

        // swap current and previous metrics
        boost::swap(curr_metrics, prev_metrics);

        // finish timer
        put_sample_timer.stop();
    }

    ~Compress() {
        push(false);
    }
};

//
//
//

// Callback to obtain each chunk
class DataSource {
public:
    virtual bool get_chunk(vector<char>& compressed) = 0;
};

// Decompress handles extracting samples from compressed chunks
class Decompress {
private:

    scoped_array<char> ref_data;
    BSONObj ref_sample;

    scoped_ptr<vector<METRIC> > prev_metrics;
    scoped_ptr<vector<METRIC> > curr_metrics;

    int n_deltas;
    int n_metrics;
    int delta_n;
    scoped_array<DELTA> deltas;

    DataSource* source;

    bool pull() {
        
        // get compressed data
        vector<char> compressed;
        if (!source->get_chunk(compressed))
            return false;
        char *data = compressed.data();
        char* end = data + compressed.size();

        // set up decompression
        boost::iostreams::filtering_istreambuf z;
        z.push(boost::iostreams::zlib_decompressor());
        z.push(boost::iostreams::basic_array_source<char>(data, end));

        // get reference sample
        uint32_t sz;
        z.sgetn((char*)&sz, sizeof(sz));
        ref_data.reset(new char[sz]);
        *(uint32_t*)(ref_data.get()) = sz;
        z.sgetn(ref_data.get() + sizeof(uint32_t), sz - sizeof(uint32_t));
        ref_sample = BSONObj(ref_data.get());
        
        // set up curr_metrics and prev_metrics
        bool matches = false;
        curr_metrics->clear();
        extract_metrics(BSONObj(), ref_sample, *curr_metrics, matches);
        n_metrics = curr_metrics->size();
        prev_metrics->resize(n_metrics);
        
        // get info about deltas
        z.sgetn((char*)&n_metrics, sizeof(n_metrics));
        z.sgetn((char*)&n_deltas, sizeof(n_deltas));
        if (n_metrics != curr_metrics->size())
            msg(1) << n_metrics << " " << curr_metrics->size() << endl;
        assert(n_metrics==curr_metrics->size());

        // report chunk stats
        int ns = n_deltas + 1;
        msg(2) << "pulled chunk, " << ns << " samples, " << compressed.size() << " bytes, "
             << (compressed.size()/ns) << " bytes/sample" << endl;

        // get compressed deltas
        char buf[2 * n_deltas * n_metrics * pack::max];
        end = buf + z.sgetn(buf, sizeof(buf));
        assert(end <= buf + sizeof(buf));
        char* p = buf;

        // decompress the deltas
        deltas.reset(new DELTA[n_deltas*n_metrics]);
        DELTA n_zeroes = 0;
        for (int i=0; i<n_metrics; i++) {
            for (int j=0; j<n_deltas; j++) {
                if (n_zeroes) {
                    deltas[i*n_deltas + j] = 0;
                    n_zeroes--;
                } else {
                    DELTA delta;
                    pack::unpack(p, delta);
                    if (delta==0 && run_length)
                        pack::unpack(p, n_zeroes);
                    deltas[i*n_deltas + j] = delta;
                }
                assert(p <= end);
            }
        }

        // got stuff
        return true;
    }

public:

    //
    // Decompress handles extracting samples from compressed chunks
    // source - callback to obtain each chunk
    //
    Decompress(DataSource* source) {

        prev_metrics.reset(new vector<METRIC>);
        curr_metrics.reset(new vector<METRIC>);

        this->source = source;
    }

    //
    // extract the next sample
    // curr_sample - returns the extracted sample
    // returns true if a sample was available
    //
    bool get_sample(BSONObj& curr_sample) {

        // get samples if needed and possible
        if (ref_sample.isEmpty() || delta_n==n_deltas) {

            // get more data if possible
            if (!pull())
                return false;

            // return reference sample
            curr_sample = ref_sample;

            // next sample will be ref delta
            delta_n = 0;

        } else {

            // apply deltas
            for (int i=0; i<n_metrics; i++)
                (*curr_metrics)[i] = (*prev_metrics)[i] + deltas[delta_n + i*n_deltas];

            // construct sample
            curr_sample = insert_metrics(ref_sample, *curr_metrics);

            // next sample will be next delta
            delta_n += 1;
        }

        // swap current and previous metrics
        boost::swap(curr_metrics, prev_metrics);

        // got a sample
        return true;
    }

};


//
//
//

class SampleSink {
public:
    virtual void put_sample(BSONObj& sample) = 0;
    virtual ~SampleSink() {};
};

class SampleSource {
public:
    virtual bool get_sample(BSONObj& sample) = 0;
    virtual ~SampleSource() {};
};


//
// simple compressed file container for debugging and testing
//

class CompressedFileSink : public DataSink, public SampleSink {

    int fd;
    SpaceStats space;
    scoped_ptr<Compress> compress;

    void push_chunk(char* buf, char* end, Date_t id) {
        int sz = end - buf;
        if (fd >= 0) {
            int n = write(fd, &sz, sizeof(sz));
            if (n!=sizeof(sz)) err("write");
            n = write(fd, buf, sz);
            if (n != sz)
                err("write");
        };
        space.record_sample(0, sz);
    };
    
public:

    CompressedFileSink(string fn, int chunk_size) : space("compressed file sink " + fn) {
        if (!fn.empty()) {
            fd = open(fn.c_str(), O_CREAT | O_WRONLY | O_TRUNC, 0666);
            if (fd<0) err(fn);
        } else {
            fd = -1;
        }
        compress.reset(new Compress(this, chunk_size));
    }

    void put_sample(BSONObj& sample) {
        compress->put_sample(sample);
        space.record_sample(1, 0);
    }
};


class CompressedFileSource : public DataSource, public SampleSource {

    int fd;
    scoped_ptr<Decompress> decompress;
    SpaceStats space;

    virtual bool get_chunk(vector<char>& compressed) {
        int sz = -1;
        int n = read(fd, (char*)&sz, sizeof(sz));
        if (n==0) return false;
        if (n<0) err("read");
        compressed.resize(sz);
        n = read(fd, compressed.data(), sz);
        if (n!=sz) err("read");
        space.record_sample(0, sz);
        return true;
    }
    
public:

    CompressedFileSource(string fn) : space("compressed file source " + fn) {
        fd = open(fn.c_str(), O_RDONLY);
        if (fd<0) err(fn);
        decompress.reset(new Decompress(this));
    }

    bool get_sample(BSONObj& sample) {
        bool rc = decompress->get_sample(sample);
        if (rc)
            space.record_sample(1, 0);
        return rc;
    }
};


//
// read compressed bson samples as generated by built-in server code
//

class CompressedBsonSource : public DataSource, public SampleSource {

    int fd;
    scoped_ptr<Decompress> decompress;
    SpaceStats space;
    int chunks_read;

    virtual bool get_chunk(vector<char>& compressed) {

        // get next bson document
        while (true) {

            // read size
            int sz = -1;
            int n = read(fd, (char*)&sz, sizeof(sz));
            if (n==0) return false;
            if (n<0) err("read");

            // explicit 0-length sample
            if (sz==0)
                return false;

            // read rest of doc
            char buf[sz];
            *(int*)buf = sz;
            n = read(fd, buf+sizeof(sz), sz-sizeof(sz));
            if (n==0) return false;
            if (n<0) err("read");
            BSONObj chunk(buf);

            // look for a doc type 1
            if (chunk.getIntField("type") == 1) {
                int len;
                const char* data = chunk["data"].binData(len);
                msg(3) << "processing doc type " << chunk.getIntField("type") <<
                    " bindata len " << len << endl;
                const int skip = sizeof(int); // skip uncompressed length header, we don't need it
                compressed.insert(compressed.begin(), &data[skip], &data[len]);
                chunks_read += 1;
                return true;
            } else {
                msg(2) << "skipping doc type " << chunk["type"] << endl;
            }
        }
        
        // didn't find anything
        return false;
    }
    
public:

    CompressedBsonSource(string fn) : space("compressed bson source " + fn) {
        fd = open(fn.c_str(), O_RDONLY);
        if (fd<0) err(fn);
        decompress.reset(new Decompress(this));
        chunks_read = 0;
    }

    bool get_sample(BSONObj& sample) {
        bool rc = decompress->get_sample(sample);
        if (rc)
            space.record_sample(1, 0);
        return rc;
    }
};


//
// read/write uncompressed samples from/to a .bson file
//

class BsonFileSource : public SampleSource {

    scoped_array<char> buf;
    struct stat s;
    int at;
    SpaceStats space;
    bool loop;

public:

    BsonFileSource(string fn, bool loop = false) : space("bson file source " + fn) {
        this->loop = loop;
        int fd = open(fn.c_str(), O_RDONLY);
        if (fd<0) err(fn);
        int rc = fstat(fd, &s);
        if (rc<0) err("fstat");
        buf.reset(new char[s.st_size]);
        int n = read(fd, buf.get(), s.st_size);
        if (n!=s.st_size) err("n!=s.st_size");
        at = 0;
    }

    bool get_sample(BSONObj& sample) {
        if (at >= s.st_size) {
            if (!loop)
                return false;
            at = 0;
        }
        sample = BSONObj(buf.get()+at);
        at += sample.objsize();
        space.record_sample(1, sample.objsize());
        return true;
    }        
};


class BsonFileSink : public SampleSink {

    int fd;
    SpaceStats space;

public:

    BsonFileSink(string fn) : space("bson file sink " + fn) {
        fd = open(fn.c_str(), O_CREAT | O_WRONLY | O_TRUNC, 0666);
        if (fd<0) err(fn);
    }

    BsonFileSink(int fd) : space("bson file sink fd=" + to_string(fd)) {
        this->fd = fd;
    }

    void put_sample(BSONObj& sample) {
        int n = write(fd, sample.objdata(), sample.objsize());
        if (n!=sample.objsize()) err("write");
        space.record_sample(1, sample.objsize());
    }
};


//
// write uncompressed samples to a .json file
//

class JsonFileSink : public SampleSink {

    ofstream file_out;
    ostream* out;
    SpaceStats space;

public:

    JsonFileSink(string fn) : space("json file sink " + fn) {
        file_out.open(fn, ios::out);
        out = &file_out;
    }

    JsonFileSink() : space("json stdout file sink") {
        out = &cout;
    }

    void put_sample(BSONObj& sample) {
        *out << sample.jsonString() << endl;
        space.record_sample(1, sample.objsize());
    }
};



//
// get serverStatus samples live from a mongodb source
//

void serverStatus(DBClientBase& c, BSONObj& result) {
    BSONObj cmd = BSON(
        "serverStatus" << 1 <<
        "tcmalloc" << 1
    );
    int rc = c.runCommand("local", cmd, result);
    if (!rc)
        err("serverStatus", false);
}

void replSetGetStatus(DBClientBase& c, BSONObj& result) {
    BSONObj cmd = BSON(
        "replSetGetStatus" << 1
    );
    int rc = c.runCommand("admin", cmd, result);
    if (!rc)
        err("replSetGetStatus", false);
}

class LiveSource : public SampleSource {

    scoped_ptr<DBClientBase> c;
    SpaceStats space;
    bool do_repl;

public:

    LiveSource(string spec = "localhost", bool do_repl = true) :
        space("live source " + spec),
        do_repl(do_repl)
    {

        // parse and check spec connection string
        string errmsg;
        ConnectionString cs = ConnectionString::parse(spec, errmsg);
        if (!cs.isValid())
            err(spec + ": " + errmsg, false);

        // connect
        client::initialize();
        c.reset(cs.connect(errmsg));
        if (!c)
            err(errmsg, false);
    }

    bool get_sample(BSONObj& sample) {
        if (do_repl) {
            BSONObj ss, rs;
            serverStatus(*c, ss);
            replSetGetStatus(*c, rs);
            sample = BSON(
                "serverStatus" << ss <<
                "replSetGetStatus" << rs
            );
        } else {
            serverStatus(*c, sample);
            space.record_sample(1, sample.objsize());
        }
        return true;
    }
};


//
// put compressed samples to a mongodb collection
// spec is: mongodb//host?ns=...&size=...
//    ns - destination ns - default is local.ftdc
//    size - capped size - default is 100 MB
// capped collection is created if it doesn't already exist
//

class LiveSink : public SampleSink, DataSink {

    scoped_ptr<DBClientBase> c;
    string ns;
    scoped_ptr<Compress> compress;
    SpaceStats space;
    Date_t last_id;

    void push_chunk(char* buf, char* end, Date_t id) {

        size_t sz = end - buf;

        BSONObjBuilder q;
        q.appendDate("_id", id);

        BSONObjBuilder b;
        b.appendDate("_id", id);
        b.appendNumber("type", 0);
        b.appendBinData("data", sz, BinDataGeneral, buf);

        c->update(ns, q.obj(), b.obj(), true);
        //c->insert(ns, b.obj());
        space.record_sample(0, sz);
    };

public:

    LiveSink(string spec, int chunk_size, int chunk_update_size, bool do_reset) :
        space("live sink " + spec), last_id(0)
    {

        // parse and check spec connection string
        string errmsg;
        ConnectionString cs = ConnectionString::parse(spec, errmsg);
        if (!cs.isValid())
            err(spec + ": " + errmsg, false);

        // ns - default is local.ftdc
        BSONElement _ns = cs.getOptions()["ns"];
        ns = !_ns.eoo()? _ns.String() : "local.ftdc";

        // capped collection size - default is 100 MB
        BSONElement _sizeMB = cs.getOptions()["sizeMB"];
        int size = !_sizeMB.eoo()? stoi(_sizeMB.String())*1024*1024 : 100*1024*1024;

        // connect
        client::initialize();
        c.reset(cs.connect(errmsg));
        if (!c)
            err(errmsg, false);

        // parse ns
        string::size_type dot = ns.find(".");
        string db = ns.substr(0, dot);
        string coll = ns.substr(dot+1, string::npos);

        // drop collection first if requested
        BSONObj cmd = BSON(
            "drop" << coll
        );
        BSONObj info;
        c->runCommand(db, cmd, info);
        msg(1) << "dropping " << db << "." << coll << ": " << info << endl;

        // create collection if it doesn't already exist
        cmd = BSON(
            "create" << coll <<
            "capped" << true <<
            "size" << size <<
            "storageEngine" << BSON("wiredTiger" << BSON("configString" <<  "block_compressor=none"))
        );
        c->runCommand(db, cmd, info);
        msg(1) << "creating " << db << "." << coll << ": " << info << endl;

        // initialize compressor with ourselves as data sink
        compress.reset(new Compress(this, chunk_size, chunk_update_size));
    }
  
    void put_sample(BSONObj& sample) {

        // compute id
        Date_t id = now_ms();
        if (id==last_id)
            id = last_id + 1;
        last_id = id;

        // put the sample
        compress->put_sample(sample, id);
        space.record_sample(1, 0);
    }
};


//
// extract and decompress samples from a mongodb collection
// spec is: mongodb//host?ns=...
//    ns - destination ns - default is local.ftdc
//

class CompressedCollectionSource : public SampleSource, DataSource {

    scoped_ptr<DBClientBase> c;
    string ns;
    auto_ptr<DBClientCursor> cursor;
    scoped_ptr<Decompress> decompress;
    
    SpaceStats space;

    virtual bool get_chunk(vector<char>& compressed) {
        if (!cursor->more())
            return false;
        int len;
        const char* data = cursor->next()["data"].binData(len); // xxx error checkign
        compressed.assign(data, data+len);
        space.record_sample(0, len);
        return true;
    }
    
public:

    CompressedCollectionSource(string spec) : space("compressed collection source " + spec) {

        // parse and check spec connection string
        string errmsg;
        ConnectionString cs = ConnectionString::parse(spec, errmsg);
        if (!cs.isValid())
            err(spec + ": " + errmsg, false);

        // ns - default is local.ftdc
        BSONElement _ns = cs.getOptions()["ns"];
        ns = !_ns.eoo()? _ns.String() : "local.ftdc";

        // connect
        client::initialize();
        c.reset(cs.connect(errmsg));
        if (!c)
            err(errmsg, false);

        // initialize cursor
        cursor = c->query(ns, BSONObj());

        // initialize decompressor
        decompress.reset(new Decompress(this));
    }

    bool get_sample(BSONObj& sample) {
        bool rc = decompress->get_sample(sample);
        if (rc)
            space.record_sample(1, 0);
        return rc;
    }
};


//
// time serverStatus and/or ping
//

void time_ping(string spec, int n, double delay) {

    // parse and check spec s connection string
    string errmsg;
    ConnectionString cs = ConnectionString::parse(spec, errmsg);
    if (!cs.isValid())
        err(spec + ": " + errmsg, false);

    // connect
    client::initialize();
    DBClientBase *c = cs.connect(errmsg);
    if (!c)
        err(errmsg, false);

    BSONObj result;
    TimeStats serverStatus_timer("serverStatus");
    TimeStats replSetGetStatus_timer("replSetGetStatus");
    TimeStats ping_timer("ping");

    for (int i=0; i<n; i++) {

        // serverStatus
        serverStatus_timer.start();
        serverStatus(*c, result);
        serverStatus_timer.stop();

        // replSetGetStatus
        replSetGetStatus_timer.start();
        replSetGetStatus(*c, result);
        replSetGetStatus_timer.stop();

        // ping
        ping_timer.start();
        int rc = c->simpleCommand("local", &result, "ping");
        ping_timer.stop();
        if (!rc)
            err("ping");

        // sleep if requested
        if (delay)
            sleep(delay);
    }

    /*
    int t_ss_less_ping_us_avg = int((serverStatus_timer.avg() - ping_timer.avg()) * 1e6);
    int t_ss_less_ping_us_min = int((serverStatus_timer.min() - ping_timer.min()) * 1e6);
    msg(0) << "serverStatus less ping " << t_ss_less_ping_us_min << " µs min, " << 
         t_ss_less_ping_us_avg << " µs avg" << endl;

    int t_rs_less_ping_us_avg = int((replSetGetStatus_timer.avg() - ping_timer.avg()) * 1e6);
    int t_rs_less_ping_us_min = int((replSetGetStatus_timer.min() - ping_timer.min()) * 1e6);
    msg(0) << "replSetGetStatus less ping " << t_rs_less_ping_us_min << " µs min, " << 
         t_rs_less_ping_us_avg << " µs avg" << endl;
    */
}

//
// signal handling for clean exit on ^C
//

static bool stop = false;

void signal_exit(int s) {
    msg(0) << "interrupt" << endl;
    stop = true;
}


//
//
//

int main(int argc, char* argv[]) {

    int n = 0;
    string source_spec;
    string sink_spec;
    float delay = 0.0;
    string ping_spec;
    int chunk_size = 300;
    int chunk_update_size = 0;
    bool do_fork = false;
    bool do_reset = false;
    bool replSet = false;

    for (int i=1; i<argc; i++) {
        if (argv[i]==string("-n"))
            n = atoi(argv[++i]);
        else if (argv[i]==string("-t"))
           delay = atof(argv[++i]);
        else if (argv[i]==string("-p"))
            ping_spec = argv[++i];
        else if (argv[i]==string("-c"))
            chunk_size = atoi(argv[++i]);
        else if (argv[i]==string("-u"))
            chunk_update_size = atoi(argv[++i]);
        else if (argv[i]==string("-v"))
            verbosity = atoi(argv[++i]);
        else if (argv[i]==string("-r"))
            replSet = true;
        else if (argv[i]==string("--fork"))
            do_fork = true;
        else if (argv[i]==string("--reset"))
            do_reset = true;
        else if (starts_with(argv[i], "-"))
            err(string("unrecognized arg ") + argv[i], false);
        else if (source_spec.empty())
            source_spec = argv[i];
        else if (sink_spec.empty())
            sink_spec = argv[i];
        else
            err(string("unrecognized arg ") + argv[i], false);
    }

    // timing for ping and/or serverStatus
    if (!ping_spec.empty()) {
        time_ping(ping_spec, n, delay);
        return 0;
    }

    scoped_ptr<SampleSource> source;
    scoped_ptr<SampleSink> sink;

    // construct source from source_spec
    if (ends_with(source_spec, ".bson")) {
        source.reset(new BsonFileSource(source_spec, n>0));
    } else if (starts_with(source_spec, "mongodb:")) {
        if (source_spec.find("?ns") != string::npos) {
            source.reset(new CompressedCollectionSource(source_spec));
        } else {
            source.reset(new LiveSource(source_spec, replSet));
            if (!delay)
                delay = 1.0;
        }
    } else if (ends_with(source_spec, ".ftdc")) {
        source.reset(new CompressedFileSource(source_spec));
    } else {
        // assume compressed bson source from mongod built-in ftdc facility
        source.reset(new CompressedBsonSource(source_spec));
    }

    // construct sink from sink_spec
    if (ends_with(sink_spec, ".bson")) {
        sink.reset(new BsonFileSink(sink_spec));
    } else if (algorithm::ends_with(sink_spec, ".json")) {
        sink.reset(new JsonFileSink(sink_spec));
    } else if (sink_spec=="-") {
        sink.reset(new JsonFileSink());
    } else if (starts_with(sink_spec, "mongodb:")) {
        sink.reset(new LiveSink(sink_spec, chunk_size, chunk_update_size, do_reset));
    } else if (ends_with(sink_spec, ".ftdc") || sink_spec=="") {
        sink.reset((new CompressedFileSink(sink_spec, chunk_size)));
    } else {
        err(string("unrecognized sink ") + sink_spec, false);
    }

    // overall timers
    TimeStats get_sample_timer("get_sample");
    TimeStats overall_timer("overall");

    // clean exit on ^C or kill
    signal(SIGINT, signal_exit);
    signal(SIGTERM, signal_exit);

    // fork?
    if (do_fork)
        int rc = daemon(true /*nochdir*/, false /*noclose*/);

    // shovel samples
    BSONObj sample;
    for (int i=0; (n==0 || i<n) && !stop; i++) {
        overall_timer.start();
        get_sample_timer.start();
        if (!source->get_sample(sample))
            break;
        get_sample_timer.stop();
        sink->put_sample(sample);
        overall_timer.stop();
        if (delay)
            sleep(delay);
    }

}

