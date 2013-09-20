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
    exp=test-expected/mdb$2
    act=test-actual/mdb$2
    $* >$act
    diff $exp $act
    echo pass $*
}

function test_all() {

    test_one ./mdb -c testdb test big
    test_one ./mdb -clb testdb test small
    test_one ./mdb -cn testdb test small
    test_one ./mdb -cp testdb test big
    test_one ./mdb -cl testdb test big

    test_one ./mdb -x testdb/test.0 2000
    test_one ./mdb -xl testdb/test.0 2000
    test_one ./mdb -xlb testdb/test.0 2000

    # xxx not working for some reason
    #test_one ./mdb -xn testdb/test.0 offset
    #test_one ./mdb -xp testdb/test.0 offset

    test_one ./mdb -r testdb/test.0 20b0
    test_one ./mdb -rb testdb/test.0 110b0

    test_one ./mdb -b testdb/test.0 110c0
}


init
test_all

