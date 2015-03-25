function @echo {
    echo ">" $* >&2
    if ! "$@"; then
        echo FAIL >&2
        result=FAIL
    fi
}

function compile {

    arch=$(uname)
    if [[ $arch == Linux ]]; then
        mt=
    else
        mt=-mt
    fi

    MCXX=$HOME/mongodb/mongo-cxx-driver-install
    g++ --std=c++11 ftdc.cpp -o ~/bin/ftdc -O4 $* \
        -I $MCXX/include -L $MCXX/lib \
        -I /usr/local/include -I /opt/local/include -L /usr/local/lib -L /opt/local/lib \
        -lmongoclient -lboost_system$mt -lboost_thread$mt -lboost_regex$mt \
        -lboost_date_time$mt -lboost_serialization$mt -lboost_filesystem$mt \
        -lboost_iostreams$mt -lpthread -rdynamic
}

function compare-bson {
    diff="diff "
    for ifn in $*; do
        ofn=/tmp/$(basename -s .bson $ifn).json
        bsondump $ifn | perl -pe '
            s/([0-9\-+][0-9\.\-+e]*)/int($1)/ge;
            s/{"\$numberLong":"([0-9\-+]+)"}/$1/g;
            s/NumberLong\(([0-9\-+]+)\)/$1/g;
            s/(,|{)/$1\n/g;
        ' | grep -v formattedString >$ofn # special-case: it's a string that changes (ugh)
        diff="$diff $ofn"
    done
    @echo $diff
}

function test-one {

    echo >&2
    echo === TESTING $* >&2

    ifn=$1
    bn=$(basename -s .bson $ifn)

    ofn=/tmp/$bn.ftdc
    ofn2=/tmp/$bn-2.ftdc
    ofnd=/tmp/$bn-d.bson
    rm -f $ofn $ofn2 $ofnd /tmp/*.json

    @echo ftdc $ifn $ofn   # compress it
    @echo ftdc $ofn $ofn2  # compress again to check for idempotency
    @echo ftdc $ofn $ofnd  # decompress to compare against original
    
    echo === checking idempotency of compression >&2
    @echo diff $ofn $ofn2

    echo === comparing compressed with original >&2
    compare-bson $ifn $ofnd
}


function test-all {
    if ! compile; then
        exit -1
    fi
    test-one test/ss-wt-idle-600.bson
    test-one test/ss-300-1.bson
    test-one test/ss-300-2.bson
    test-one test/ss-600-3.bson
    test-one test/ss-mmapv1-20k-mixed-600.bson
    test-one test/ss-wt-20k-mixed-600.bson
}

result=PASS
test-all
echo result: $result >&2
if [[ $result == FAIL ]]; then
    exit -1
fi


