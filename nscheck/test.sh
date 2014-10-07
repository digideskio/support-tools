# test recursive directory traversal, Python 2.4
function test1 {
    python2.4 nscheck.py test
}

# test recursive directory traversal, Python 2.6
function test2 {
    python2.6 nscheck.py test
}

# test list of file names
function test3 {
    python nscheck.py test/*.ns
}

# test repair
function test4 {
    rm -rf repair
    cp -r test repair
    echo === repairing
    python nscheck.py --repair repair
    echo === checking
    python nscheck.py repair
    echo === ls
    ls -Rs repair
}

# create db with collections with:
#   no indexes, <10 indexes, 10 indexes
#   existing, dropped
# test that we flag all as ok
function test5 {
    (
        killall mongod
        rm -rf db db.log
        mkdir db
        mongod --dbpath db --logpath db.log --fork >/dev/null
        sleep 1 # mongod comes up
        mongo generate.js
        sleep 1 # .ns file gets flushed
    ) >/dev/null
    python nscheck.py db/test.ns --detail
}

function dotest {
    $1 >/tmp/$1.out
    if ! diff -b /tmp/$1.out expected/$1.out; then
        echo $1 FAIL
    else
        echo $1 PASS
    fi
}

dotest test1
dotest test2
dotest test3
dotest test4
dotest test5
