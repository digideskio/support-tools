# configure for test env
if [[ $(hostname) == vm-ubuntu-2 ]]; then
    mongod24=~/mongodb/mongodb-linux-x86_64-2.4.10/bin/mongod
    mongod26=~/mongodb/mongodb-linux-x86_64-2.6.3/bin/mongod
    mongo=~/mongodb/mongodb-linux-x86_64-2.4.10/bin/mongo
    python24=python # not available on later ubuntu, so punt
    python26=python
    vulnerable=yes
elif [[ $(hostname) == reboot.local ]]; then
    mongod24=~/mongodb/mongodb-osx-x86_64-2.4.10/bin/mongod
    mongod26=~/mongodb/mongodb-osx-x86_64-2.6.4/bin/mongod
    mongo=~/mongodb/mongodb-osx-x86_64-2.4.10/bin/mongo
    python24=python2.4
    python26=python2.6
fi

function list {
    ls -l $(echo "${@}" | sort) | awk '{print $5, $9}'
}

# test recursive directory traversal, Python 2.4
function test1 {
    $python24 nscheck.py test | check
}

# test recursive directory traversal, Python 2.6
function test2 {
    $python26 nscheck.py test | check
}

# test list of file names
function test3 {
    python nscheck.py test/*.ns | check
}

# test repair
function test4 {
    (
        rm -rf repair
        cp -r test repair
        echo === repairing
        python nscheck.py --repair repair
        echo === checking
        python nscheck.py repair
        echo === ls
        list $(find repair -type f)
    ) | check
}

function fresh {
    killall mongod
    rm -rf db db.log
}

function start {
    echo hi
    mkdir db
    $* --dbpath db --logpath db.log --logappend --smallfiles --fork
    sleep 1
}

function stop {
    killall mongod
    while pgrep mongod; do
        echo waiting for mongod shutdown
        sleep 1
    done
}

# create db with collections with:
#   no indexes, <10 indexes, 10 indexes
#   existing, dropped
# test that we flag all as ok
# use 2.4 as it has one extra ns test.$freelist
function test5 {
    fresh
    start $mongod24
    $mongo generate.js
    stop
    python nscheck.py db/test.ns | check
}

# synthetic damage, basic case: damage 8KB region
function test6_ {

    # which mongod to use
    mongod=$1

    # insert collection test.c
    fresh
    start $mongod
    $mongo --eval 'printjson(db.c.insert({}))'

    # damage .ns file
    stop
    python damage.py db/test.ns 0x6b3000 0x1000

    # insert collection test.z, so it ends up at pos >0 in hash chain due to damage
    # must be done under 2.4 as damaged db won't start under 2.6
    start $mongod24
    $mongo --eval 'db.adminCommand("listDatabases")' # why is this needed?
    $mongo --eval 'printjson(db.z.insert({}))'
    $mongo --quiet --eval 'printjson(db.z.stats())' | check

    # 4. repair
    stop
    python nscheck.py --repair db/test.ns | check

    # 5. check live operations
    start $mongod
    $mongo --quiet --eval 'printjson(db.c.stats())' | check
    $mongo --quiet --eval 'printjson(db.z.stats())' | check
}        

# test6 using 2.4
function test6a {
    test6_ $mongod24
}

# test6 using 2.6
function test6b {
    test6_ $mongod26
}

# synthetic damage: bad hash
function test7 {

    # 1. insert collection test.c
    killall mongod
    rm -rf db
    start $mongod26
    $mongo --eval 'printjson(db.c.insert({}))'

    # 2. damage .ns file: change hash code of test.c entry
    stop
    python damage.py db/test.ns 0x006afd24 4
    old=$(md5 db/test.ns)

    # 3. attempt repair, should fail
    stop
    python nscheck.py --repair db/test.ns | check

    # 4. check that .repaired file is present, but .ns file was not changed
    (
        list $(find db -type f)
        new=$(md5 db/test.ns)
        if [[ $new == $old ]]; then
            echo test.ns was not changed
        else
            echo test.ns was changed!
            echo old: $old
            echo new: $new
        fi
    ) | check
}        

# problem file
function test8 {
    python nscheck.py nonexistentfile.ns | check
}

# existing .backup file
function test9 {
    (
        rm -rf repair
        mkdir repair
        cp test/ccs.ns repair
        touch repair/ccs.ns.backup
        python nscheck.py --repair repair/ccs.ns
        list $(find repair -type f | sort)
        cp repair/ccs.ns.repaired repair/ccs.ns
        python nscheck.py repair/ccs.ns
    ) | check
}

# customer repro - must run on 2.6 mongod <2.6.5, unpatched kernel
function test10 {

    # fill disk with non-zero stuff
    fresh
    python fill.py fill
    sync

    # create ns that will corrupt under 2.6 on vulnerable system
    start $mongod26
    $mongo mms-dev --eval 'load("test10.js"); create()'

    # make sure corruption is visible
    stop
    sync
    sudo bash -c 'echo 3 >/proc/sys/vm/drop_caches'

    # check that mongod sees the corruption
    start $mongod26
    (
        sleep 2
        echo "expecting assertion in log:"
        egrep -o 'Assertion: 10078.*' db.log
    ) | check

    # repair
    stop
    python nscheck.py --repair db/mms-dev.ns | check

    # check that mongod no longer sees corruption, and collections and indexes can be accessed
    start $mongod26
    (
        sleep 2
        echo "expecting only one assertion in log"
        egrep -o 'Assertion: 10078.*' db.log
        $mongo --quiet mms-dev --eval 'load("test10.js"); check()'
    ) | check

}



function check {
    if [[ $dbg == "yes" ]]; then
        cat 2>&1 | tee -a $test_fn
    else
        cat >>$test_fn 2>&1
    fi
}

function dotest {
    test_fn=/tmp/$1.out
    rm -f $test_fn
    if [[ $dbg == "yes" ]]; then
        $1
    else
        $1 >/dev/null 2>&1
    fi
    if ! diff -b /tmp/$1.out expected/$1.out; then
        echo $1 FAIL
        rc=-1
    else
        echo $1 PASS
    fi
}

#dbg=yes

function main {
    rc=0
    dotest test1
    dotest test2
    dotest test3
    dotest test4
    dotest test5
    dotest test6a
    dotest test6b
    dotest test7
    dotest test8
    dotest test9
    if [[ $vulnerable == yes ]]; then
        dotest test10
    fi
    exit $rc
}

main; exit
