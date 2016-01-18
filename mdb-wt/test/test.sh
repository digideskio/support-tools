function mdb-wt {
    python ../mdb-wt.py "$@"
}

fn=collection-2--2874409305134884122.wt

function test1 {
    mdb-wt p db/$fn
}

function test2 {
    mdb-wt pf db/$fn
}

function test3 {
    mdb-wt pe db/$fn
}

function test4 {
    mdb-wt peb db/$fn
}

function test5 {
    mdb-wt peB db/$fn
}

function test6 {
    (
        cd db
        python ../../mdb-wt.py pe $fn
    )
}

function run-test {
    echo === $1
    $1 >/tmp/$1.out
    if ! diff /tmp/$1.out ref/$1.out; then
        echo FAIL
        exit -1
    else
        echo OK
    fi
}

run-test test1
run-test test2
run-test test3
run-test test4
run-test test5
run-test test6



