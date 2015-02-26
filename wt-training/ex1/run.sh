#
# configure for your environment
#
tools_dir=~/support-tools
repro_host=vm-ubuntu

#
# run repro on $repro_host
#
ssh $repro_host bash <<EOF
    rm -rf repro
    mkdir repro
EOF
scp repro.* $repro_host:repro
ssh $repro_host bash <<EOF
    cd repro
    bash repro.sh
EOF

#
# fetch results, visualize them
#
scp $repro_host:repro/ss.log .
python $tools_dir/timeseries/timeseries.py ss:ss.log >repro.html
open -a 'Google Chrome' repro.html





