function @echo {
    echo ">" $* >&2
    "$@"
}

function run-timeseries {
    @echo time ../timeseries.py "${@}" --html $HTML
}

function test-001 {
    #run-timeseries 'mongod logged(count_min=3000):data/r0.log' 'mongod max logged:data/r0.log'
    run-timeseries 'data/r0.log' # AUTO MODE
}

function test-002 {
    run-timeseries --level 9 'iostat(tz=0):data/iostat.txt'
}

# tz -8 b/c the data files are in naive local time,
# and were gathered on an ubuntu vm that had tz set to pst
function test-003 {
    run-timeseries --level 9 --width 25 --itz -8 \
        'iostat:data/test-003/iostat.log' \
        'wt(default_date=2014):data/test-003/wtstats.log' \
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
    run-timeseries --level 2 --width 24 --itz -5 \
        'iostat(tz=-8):data/test-003/iostat.log' \
        'wt(tz=-8,default_date=2014):data/test-003/wtstats.log' \
        'grep(pat=insert .* ([0-9]+)$,name=app: insert /s):data/test-003/app.out' \
        'grep(pat=find .* ([0-9]+)$,name=app: find /s):data/test-003/app.out'
}

function test-004 {
    run-timeseries --level 9 'ss:data/test-004/ss.log'
}

function test-004a {
    run-timeseries 'data/test-004/ss.log' # AUTO MODE
}

function test-005 {
    run-timeseries --itz 0 'data/test-005/iostat.log' # AUTO MODE
}

function test-006 {
    run-timeseries --itz 0 'data/test-006.csv'
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
    run-timeseries 'data/ss-binning.log' # AUTO MODE
}

function test-011 {
    run-timeseries 'rs:data/rs.log'
}

function test-012 {
    run-timeseries 'data/ss-wt-repl-600.json' # AUTO MODE
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
    run-timeseries --after 2015-10-02T12:33Z --before 2015-10-02T12:36Z $fn # AUTO MODE
}

# interim file
function test-016 {
    fn=data/diagnostic.data/metrics.interim
    run-timeseries ftdc:$fn
}

# single file
function test-017 {
    fn=data/diagnostic.data/metrics.2015-10-02T10-46-20Z-00000
    run-timeseries $fn # AUTO MODE
}

function test-018 {
    run-timeseries data/test-018 # AUTO MODE
}

function test-019 {
    run-timeseries --level 9 data/test-019 # AUTO MODE}
}

function test-020 {
    # win perf csv, and ftdc WRAPPED
    run-timeseries data/test-020 # AUTO MODE
}

# test: identify
function test-021 {
    run-timeseries data/test-021
}

# test: identify; unique part of fn at end; proper merge behvior with multiple files; 
function test-022 {
    cp data/diagnostic.data/metrics.interim /tmp/metrics.interim.aaa
    cp data/diagnostic.data/metrics.interim /tmp/metrics.interim.bbb
    run-timeseries /tmp/metrics.interim.{aaa,bbb}
}

# more iostat, including dm-* disk
function test-023 {
    run-timeseries data/test-023/iostat.log --itz -5 --level 9
}

function compare-html {

    ref=$1
    act=$2
    
    # webkit2png is a webkit-based html to image renderer
    if [[ ! -e webkit2png ]]; then
        git clone https://github.com/paulhammond/webkit2png        
    fi

    # render both pages
    o=$(basename $ref)
    rm -f /tmp/$o-{ref,act}
    if [[ -e $ref ]]; then
        webkit2png/webkit2png -W 1500 -F $ref -o /tmp/$o-ref
    fi
    webkit2png/webkit2png -W 1500 -F $act -o /tmp/$o-act

    # compute image hashes using ImageMagick
    if [[ -e $ref ]]; then
        ref_hash=$(identify -format '%#\n' /tmp/$o-ref-full.png)
    fi
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
        if [[ -e /tmp/$o-ref-full.png ]]; then
            # use ImageMagick comparison tol
            compare /tmp/$o-{ref,act}-full.png /tmp/$o-diff-full.png
            open /tmp/$o-{ref,act,diff}-full.png
        else
            # no ref, must be new; just show it
            open /tmp/$o-act-full.png
        fi
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

    HTML=/tmp/$test.html
    if $test >$HTML && compare-html ref/$test.html $HTML; then
        echo $test PASS
    else
        echo $test FAIL
        exit -1
    fi
}

function run-tests {
    run-test test-001
    run-test test-002
    #run-test test-003 # restore wt stuff
    #run-test test-003a
    #run-test test-003b
    run-test test-004
    run-test test-004a
    run-test test-005
    run-test test-006
    run-test test-007
    run-test test-008
    run-test test-009
    run-test test-010
    #run-test test-011 # rs: rework for new json parsing - needs split fields
    #run-test test-012 # rs part of ftdc/json: rework for new json parsing, also add to ftdc
    run-test test-013
    run-test test-014
    run-test test-015
    run-test test-016
    run-test test-017
    run-test test-018
    run-test test-019
    run-test test-020
    run-test test-021
    run-test test-022
    run-test test-023

}

function zip-source {
    in=../timeseries.src
    out=../timeseries.py
    zip=/tmp/temp.zip
    rm -f $zip
    (cd $in; rm -f *.pyc *.log; zip $zip *)
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


