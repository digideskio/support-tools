####
#### configure for your environment
####
tools_dir=~/support-tools
repro_host=vm-ubuntu
###
####
#### run repro on $repro_host
####
###ssh $repro_host bash <<EOF
###    rm -rf repro
###    mkdir repro
###EOF
###scp repro.* $repro_host:repro
###scp $tools_dir/timeseries/gdbmon.py $repro_host:repro
###scp $tools_dir/timeseries/sysmon.py $repro_host:repro
###ssh -t $repro_host bash <<EOF
###    cd repro
###    bash repro.sh
###EOF
###
####
# fetch results, visualize them
#
scp "$repro_host:repro/*.log" .
python $tools_dir/timeseries/timeseries.py \
    'ss:ss.log' 'sysmon:sysmon.log' 'mongod(bucket_size=0.1):db.log' >repro.html
open -a 'Google Chrome' repro.html
python $tools_dir/timeseries/gdbprof.py -g 10 --graph-scale log --html \
    --series 'ss opcounters insert:ss.log' <gdbmon.log >gdbmon.html
open -a 'Google Chrome' gdbmon.html






