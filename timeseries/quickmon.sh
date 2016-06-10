pid=$1
delay=$2
count=$3

if [[ $pid == "" ]]; then
    echo "usage: bash $0 pid [delay [count]]"
    exit -1
fi

if [[ $delay == "" ]]; then
    count=1
fi

function build-if-needed {

    if [[ ! -e quickstack ]]; then
        echo fetching quickstack
        git clone https://github.com/yoshinorim/quickstack    
    fi
    
    if [[ ! -e quickstack/quickstack ]]; then
        echo building quickstack
        if which yum; then
            sudo yum install -y binutils-devel elfutils-devel libiberty-devel gcc-c++
        elif which apt-get; then
            sudo apt-get install -y binutils-dev elfutils-dev libiberty-dev gcc-c++
        fi
        (cd quickstack; g++ quickstack.cc -lbfd -lelf -o quickstack)
    fi
}

function sample {
    echo
    echo === $(date +%Y-%m-%dT%H:%M:%S.%N%z)
    quickstack/quickstack -d 1 -p $pid
    sleep $delay
}

build-if-needed >&2

if [[ $count == "" ]]; then
    while true; do
        sample
    done
else
    i=0
    while [[ $i < $count ]]; do
        sample
        let i+=1
    done
fi

