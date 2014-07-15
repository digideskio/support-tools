function init() {
    if [[ ! -e testdb ]]; then
        killall mongod
        mkdir -p testdb
        mongod --dbpath testdb --logpath testdb.log --logappend --smallfiles --fork
        sleep 2
        mongo test.js
    fi
}

function test_one() {
    mkdir -p test-actual
    exp=expected/mdb$1
    act=/tmp/mdb$1
    python mdb.py $* >$act
    if diff $exp $act; then
        echo pass $*
    else
        echo FAIL $*
        exit -1
    fi
}

function test_all() {

    test_one  -cx testdb test.big
    test_one  -cxrb testdb test.small
    test_one  -cxrnpf testdb test.small
    test_one  -cf testdb test
    test_one  -cxrt testdb 'test.small.$_id_'

    test_one  -x testdb/test.0 0x2000
    test_one  -xr testdb/test.0 0x2000
    test_one  -xrb testdb/test.0 0x2000

    test_one  -r testdb/test.0 0x20b0
    test_one  -s testdb/test.0 0x20b0
    test_one  -rb testdb/test.0 0x110b0
    test_one  -B testdb/test.0 0x110c0

    test_one -g testdb/test.0 world

    #xxx need test for "o" flag
}

#init
test_all





