#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>


//
// error handling
//

void
err_exit(char* msg) {
    printf("\n");
    if (errno)
        perror(msg);
    else
        printf("%s\n", msg);
    exit(-1);
}


//
// utility to map a file
//

void*
map_file(char* fn) {
    int fd = open(fn, O_RDWR);
    if (fd<0) err_exit(fn);
    struct stat buf;
    int rc = fstat(fd, &buf);
    if (rc<0) err_exit("fstat");
    size_t len = buf.st_size;
    void* base = mmap(0, len, PROT_READ, MAP_SHARED, fd, 0);
    if (base==MAP_FAILED) err_exit("mmap");
    return base;
}


//
// state
//

void* base;
uint32_t curr_ext = 0;
uint32_t at = 0;
int indent = 0;
char* error = NULL;


//
// what we're printing
//

int print_collection_flag = 0;

int print_extent_flag = 0;

enum {
    NONE,
    FORWARD,
    REVERSE,
    LENGTHS
} print_record_flag = NONE;

int print_bson_flag = 0;


//
// start and end a line
//

void
print_start() {
    printf("%*s %x(%d): ", indent, "", at, at);
}

void
print_finish() {
    if (error)
        printf("ERROR %s", error);
    printf("\n");
    fflush(stdout);
}


//
//  BSON basic types
//

int
print_boolean() {
    uint8_t v = *(uint8_t*)(base+at);
    at += sizeof(uint8_t);
    printf("boolean %x ", v);
    return v;
}

uint8_t
print_uint8() {
    uint8_t v = *(uint8_t*)(base+at);
    at += sizeof(uint8_t);
    printf("0x%x ", v);
    return v;
}

uint32_t
print_uint32() {
    int v = *(int*)(base+at);
    at += sizeof(int);
    printf("%x(%d) ", v, v);
    return v;
}


char*
print_cstring() {
    char* v = (char*)(base+at);
    at += strlen(v) + 1;
    printf("'%s' ", v);
    return v;
}


void
print_string() {
    printf("len ");
    int len = print_uint32();
    char* v = (char*)(base+at);
    int slen = strlen(v) + 1;
    printf("'%s' strlen %x(%d) ", v, slen, slen);
    if (0) {
        at += slen;
        if (len!=slen) error = "STR LEN ERROR (USING strlen())";
    } else {
        at += len;
        if (len!=slen) printf("STR LEN ERROR (USING len) ");
        //if (len!=slen) error = "STR LEN ERROR (USING len) ";
    }
}


void
print_binary() {
    printf("binary len ");
    int len = print_uint32();
    printf("type ");
    int type = print_uint8();
    at += len;
}


void print_datetime() {
    int64_t v = *(int64_t*)(base+at);
    at += sizeof(int64_t);
    printf("date %llx", v);
}


void print_objectid() {
    printf("objectid ");
    for (int i=0; i<12; i++) {
        printf("%02x", *(uint8_t*)(base+at));
        at++;
    }
}


void print_double() {
    double v = *(double*)(base+at);
    at += sizeof(double);
    printf("double %lf", v);
}


//
// BSON document
//

void
print_doc() {
    print_start();
    int start = at;
    printf("doc len ");
    int len = print_uint32();
    if (len==(uint32_t)0xEEEEEEEE) {
        printf("DELETED");
        return;
    }
    int end = start + len;
    printf("end %x(%d)", end, end);
    print_finish();
    indent += 2;
    while (at < end) {
        print_start();
        printf("type ");
        int type = print_uint8();
        if (type==0) {
            if (at!=end) error = "DOC LEN ERROR";
            printf("END ");
            print_finish();
            break;
        }
        printf("name ");
        print_cstring();
        if (type==0x1) {
            print_double();
            print_finish();
        } else if (type==0x2) {
            print_string();
            print_finish();
        } else if (type==0x3) {
            indent += 2;
            printf("doc");
            print_finish();
            print_doc();
            indent -= 2;
        } else if (type==0x4) {
            indent += 2;
            printf("doc");
            print_finish();
            print_doc();
            indent -= 2;
        } else if (type==0x5) {
            print_binary();
            print_finish();
        } else if (type==0x6) {
            printf("undefined");
            print_finish();
        } else if (type==0x7) {
            print_objectid();
            print_finish();
        } else if (type==0x8) {
            print_boolean();
            print_finish();
        } else if (type==0x9) {
            print_datetime();
            print_finish();
        } else if (type==0xa) {
            printf("NULL ");
            print_finish();
        } else if (type==0xb) {
            printf("regexp ");
            print_cstring();
            print_cstring();
            print_finish();
        } else if (type==0x10) {
            printf("int ");
            print_uint32();
            print_finish();
        } else {
            error = "UNKNOWN TYPE";
            print_finish();
        }
        //if (error /* XXX and fail early */) break;
    }
    indent -= 2;
}



//
// record
//

typedef struct {
    int len;
    uint32_t ext;
    uint32_t next, prev;
} rec;

void
validate_record() {
    rec* r = (rec*)(base+at);
    if (curr_ext && r->ext!=curr_ext) error = "BAD EXT";    
    // xxx sanity check next, prev, len
}

void
print_record() {

    // print record
    print_start();
    rec* r = (rec*)(base+at);
    printf("record len %x(%d) next %x(%d) prev %x(%d) ext %x(%d) ",
           r->len, r->len, r->next, r->next, r->prev, r->prev, r->ext, r->ext);
    validate_record();
    print_finish();
    if (error)
        return;

    // print doc if requested
    if (print_bson_flag) {
        at += sizeof(rec);
        indent += 2;
        print_doc();
        indent -= 2;
    }
}



//
// disk loc
//

typedef struct {
    uint32_t f;
    uint32_t off;
} loc;

void
print_loc(char* n, loc l) {
    printf("%s %x:%x ", n, l.f, l.off);
}


//
// extent
//

#define MAX_NS_LEN 128

typedef struct {
    unsigned magic;
    loc loc;
    loc next, prev;
    char ns[MAX_NS_LEN];
    uint32_t len;
    loc first, last;
} ext;


void
print_extent() {

    // the extent
    ext* x = (ext*)(base+at);
    uint32_t end = at + x->len;
    curr_ext = at; // for error checking

    // print header
    print_start();
    printf("extent magic %x ", x->magic);
    print_loc("me", x->loc);
    print_loc("next", x->next);
    print_loc("prev", x->prev);
    printf("ns %s ", x->ns);
    printf("len %x ", x->len);
    print_loc("first", x->first);
    print_loc("last", x->last);
    print_finish();

    indent += 2;

    if (print_record_flag) {

        // first record, based on chosen traversal order
        if (print_record_flag==LENGTHS) at += sizeof(ext);
        else if (print_record_flag==FORWARD) at = x->first.off;
        else if (print_record_flag==REVERSE) at = x->last.off;
        
        while (at < end) {
            
            // print it
            int start = at;
            rec* r = (rec*)(base+at);
            print_record();
            
            if (!error) {

                // no error, go on to next record according to chosen traversal order
                if (print_record_flag==LENGTHS) at = start + r->len;
                else if (print_record_flag==FORWARD) at = r->next;
                else if (print_record_flag==REVERSE) at = r->prev;

            } else if (print_record_flag==LENGTHS) {

                // if error and traversing going by LENGTHS
                // we can try to recover by looking for valid record header
                int skipped = 0;
                while (error) {
                    error = NULL;
                    at++;
                    skipped++;
                    validate_record();
                }
                printf("resynced by skipping %x(%d) bytes\n", skipped, skipped);

            } else {

                // otherwise give up on error
                err_exit(error);

            }
        }
    }

    indent -= 2;
}


//
// collection
//

#define NS_ENTRY_SIZE 628 // that's what it is

typedef struct {
    uint32_t hash;
    char name[MAX_NS_LEN];
    loc first;
    loc last;
    loc del;
} namespace;


void
print_collection(char* path, char* db, char* name) {

    // open namespace file
    char fn[5000];
    snprintf(fn, sizeof(fn), "%s/%s.ns", path, db);
    int fd = open(fn, O_RDONLY);
    if (fd < 0) err_exit(fn);

    // find collection
    namespace *ns = NULL;
    char buf[NS_ENTRY_SIZE];
    char full[1000]; // xxx
    snprintf(full, sizeof(full), "%s.%s", db, name);
    for (;;) {
        int n = read(fd, buf, sizeof(buf));
        if (n < sizeof(buf))
            break;
        ns = (namespace*)buf;
        if (strcmp(ns->name, full)==0)
            break;
        else
            ns = NULL;
    }

    if (ns) {

        // ns info
        printf("ns %s ", ns->name);
        print_loc("first", ns->first);
        print_loc("last", ns->last);
        print_finish();

        // traverse extents
        loc next;
        for (loc l = ns->first; l.f != 0xFFFFFFFF; l = next) {
            snprintf(fn, sizeof(fn), "%s/%s.%d", path, db, l.f);
            base = map_file(fn);
            at = l.off;
            next = ((ext*)(base+at))->next;
            print_extent();
        }

    } else {
        err_exit("ns not found");
    }
}

//
//
//

int
main(int argc, char* argv[]) {

    // usage
    if (argc < 2)
        err_exit("usage: md -cxrfvb ...");

    // what to print
    for (char* c = argv[1]; *c; c++) {
        if (*c=='-') ;
        else if (*c=='c') print_collection_flag = 1;
        else if (*c=='x') print_extent_flag = 1;
        else if (*c=='l') print_record_flag = LENGTHS;
        else if (*c=='n') print_record_flag = FORWARD;
        else if (*c=='p') print_record_flag = REVERSE;
        else if (*c=='r') print_record_flag = LENGTHS;
        else if (*c=='b') print_bson_flag = 1;
        else err_exit("unknown command-line flag");
    }

    if (print_collection_flag) {

        if (argc < 4)
            err_exit("usage: md -c[rfv[b]] path db ns");

        char* path = argv[2];
        char* db = argv[3];
        char* ns = argv[4];
        print_collection(argv[2], argv[3], argv[4]);

    } else {

        if (argc < 2)
            err_exit("usage: md -[x][rfv][b] fn [off]");

        char* fn = argv[2];
        if (argc > 2) at = strtol(argv[3], NULL, 16);

        // map the file
        base = map_file(fn);

        // do requested op at requested offset
        if (print_extent_flag) {
            print_extent();
        } else if (print_record_flag) {
            print_record();
        } else if (print_bson_flag) {
            print_doc();
        }
    }

}
