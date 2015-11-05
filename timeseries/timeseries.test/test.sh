function @echo {
    echo ">" $* >&2
    "$@"
}

function run-timeseries {
    @echo time ../timeseries.py "${@}"
}

function test-001 {
    run-timeseries 'mongod logged(count_min=3000):data/r0.log' 'mongod max logged:data/r0.log'
}

function test-002 {
    run-timeseries --level 9 'iostat(tz=0):data/iostat.txt'
}

# tz -8 b/c the data files are in naive local time,
# and were gathered on an ubuntu vm that had tz set to pst
function test-003 {
    run-timeseries --level 9 --width 25 \
        'iostat(tz=-8):data/test-003/iostat.log' \
        'wt(tz=-8,default_date=2014):data/test-003/wtstats.log' \
        'grep(pat=insert .* ([0-9]+)$,name=app: insert /s):data/test-003/app.out' \
        'grep(pat=find .* ([0-9]+)$,name=app: find /s):data/test-003/app.out'
}

function test-003a {
    run-timeseries --level 9 --width 24 \
        'iostat(tz=-8):data/test-003/iostat.log' \
        'wt(tz=-8,default_date=2014):data/test-003/wtstats.log' \
        'grep(pat=insert .* ([0-9]+)$,name=app: insert /s):data/test-003/app.out' \
        'grep(pat=find .* ([0-9]+)$,name=app: find /s):data/test-003/app.out'
}

function test-003b {
    run-timeseries --level 2 --width 24 \
        'iostat(tz=-8):data/test-003/iostat.log' \
        'wt(tz=-8,default_date=2014):data/test-003/wtstats.log' \
        'grep(pat=insert .* ([0-9]+)$,name=app: insert /s):data/test-003/app.out' \
        'grep(pat=find .* ([0-9]+)$,name=app: find /s):data/test-003/app.out'
}

function test-004 {
    run-timeseries --level 9 'ss:data/test-004/ss.log'
}

function test-004a {
    run-timeseries 'ss:data/test-004/ss.log'
}

function test-005 {
    run-timeseries 'iostat(tz=0):data/test-005/iostat.log'
}

function test-006 {
    run-timeseries 'csv(tz=0):data/test-006.csv'
}

function test-007 {
    #bin-mongo 2.8.0-rc4
    #bsondump data/test-007/*.bson | python data/test-007/ping2ss.py >data/test-007/ss.json
    run-timeseries 'ss:data/test-007/ss.json'
}

function test-008 {
    run-timeseries --level 3 'cs:data/test-008/oplog.log'
}

function test-009 {
    run-timeseries --level 3 'oplog:data/test-009/oplog.json'
    #run-timeseries --level 3 'oplog:data/test-009/ol.json'
}

function test-010 {
    run-timeseries 'ss:data/ss-binning.log'
}

function test-011 {
    run-timeseries 'rs:data/rs.log'
}

function test-012 {
    run-timeseries 'ftdc:data/ss-wt-repl-600.json'
}


# basic test of an entire diagnostic.data directory
# size is large enough to invoke default overview limit of 1000
function test-013 {
    run-timeseries 'ftdc:data/diagnostic.data' --level 9
}

# entire directory with an overview small enough to go to 1 sample per chunk overview
function test-014 {
    run-timeseries 'ftdc:data/diagnostic.data' --level 9 --overview 100
}

# small time range
function test-015 {
    fn=data/diagnostic.data
    run-timeseries --after 2015-10-02T12:33Z --before 2015-10-02T12:36Z ftdc:$fn
}

# interim file
function test-016 {
    fn=data/diagnostic.data/metrics.interim
    run-timeseries ftdc:$fn
}

# single file
function test-017 {
    fn=data/diagnostic.data/metrics.2015-10-02T10-46-20Z-00000
    run-timeseries ftdc:$fn
}


function compare-html {

    ref=$1
    act=$2
    
    # webkit2png is a webkit-based html to image renderer
    if [[ ! -e webkit2png ]]; then
        git clone https://github.com/paulhammond/webkit2png        
    fi

    # new test, start with empty file
    if [[ ! -e $ref ]]; then
        touch $ref
    fi

    # render both pages
    o=$(basename $ref)
    webkit2png/webkit2png -W 1500 -F $ref -o /tmp/$o-ref
    webkit2png/webkit2png -W 1500 -F $act -o /tmp/$o-act

    # compute image hashes using ImageMagick
    ref_hash=$(identify -format '%#\n' /tmp/$o-ref-full.png)
    act_hash=$(identify -format '%#\n' /tmp/$o-act-full.png)
    echo ref hash: $ref_hash
    echo act hash: $act_hash

    function ask {
        if [[ ! -n $DONT_ASK ]]; then
            osascript -e "tell App \"Terminal\" to display dialog \"$*\""
        else
            return 0
        fi
    }

    # compare hashes
    if [[ $ref_hash != $act_hash ]]; then

        # hashes not equal; use Preview to do visual comparison
        open /tmp/$o-{ref,act}-full.png
        ask "Looks good?"
        if [[ $? == 1 ]]; then
            return -1
        fi

        # user said was ok; ask if we should update the reference html
        ask "Update reference html?"
        if [[ $? == 0 ]]; then
            @echo cp $act $ref
        fi
    fi
}

function run-test {

    test=$1

    echo === $test

    if $test >/tmp/$test.html && compare-html ref/$test.html /tmp/$test.html; then
        echo $test PASS
    else
        echo $test FAIL
        exit -1
    fi
}

function run-tests {
    run-test test-001
    run-test test-002
    run-test test-003
    run-test test-003a
    run-test test-003b
    run-test test-004
    run-test test-004a
    run-test test-005
    run-test test-006
    run-test test-007
    run-test test-008
    run-test test-009 # oplog: rework for new json parsing- needs split fields
    run-test test-010
    #run-test test-011 # rs: rework for new json parsing - needs split fields
    #run-test test-012 # rs part of ftdc/json: rework for new json parsing, also add to ftdc
    run-test test-013
    run-test test-014
    run-test test-015
    run-test test-016
    run-test test-017
}

function zip-source {
    in=../timeseries.src
    out=../timeseries.py
    zip=/tmp/temp.zip
    rm -f $zip
    (cd $in; rm *.pyc; zip $zip *)
    (
        echo "#!/usr/bin/env python";
        echo "# following is a zip archive generated from $in"
        cat $zip
    ) >$out
    chmod +x $out
}    

function main {
    pylint --output-format=parseable --disable=all --enable=E,F --reports=n ../timeseries.src/*.py || exit -1
    zip-source
    run-tests
}

if [[ -n $* ]]; then $*; else main; fi


