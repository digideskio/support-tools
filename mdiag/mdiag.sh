#!/bin/sh

diagfile="/tmp/mdiag-`hostname`.txt"

msection() {
	echo -n .
	(
		name="$1"
		shift
		echo ""
		echo ""
		echo "=========== start $name ==========="
		if [ $# -eq 0 ]; then
			eval "`cat`"
		else
			"$@"
		fi
		echo "============ end $name ============"
	) >> "$diagfile" 2>&1
}

printeach() {
	for i; do
		echo "$i"
	done
}

echo "========================="
echo "MongoDB Diagnostic Report"
echo "========================="
echo 
echo "Please wait while diagnostic information is gathered..."

[ -e "$diagfile" ] && mv -f "$diagfile" "$diagfile.old"
(
echo "========================="
echo "MongoDB Diagnostic Report"
echo "========================="
) > "$diagfile" 2>&1

msection args printeach "$@"
msection date date
msection whoami whoami
msection uname uname -a
msection blockdev /sbin/blockdev --report
msection glibc ls -l /lib*/libc.so* /lib/*/libc.so*
msection glibc2 /lib*/libc.so*
msection glibc3 /lib/*/libc.so*
msection lsb lsb_release -a
msection sysctl /sbin/sysctl -a
msection ifconfig /sbin/ifconfig -a
msection route /sbin/route -n
msection dmesg dmesg
msection lspci lspci -vvv
msection ulimit ulimit -a
msection df-h df -h
msection df-k df -k
msection mount mount
msection mounts cat /proc/mounts
msection mountinfo cat /proc/self/mountinfo
msection cpuinfo cat /proc/cpuinfo
msection meminfo cat /proc/meminfo
msection swaps cat /proc/swaps
msection modules cat /proc/modules
msection vmstat cat /proc/vmstat
msection top top -b -n 10
msection iostat iostat -xtm 5 10
msection rpcinfo /usr/sbin/rpcinfo -p
msection scsidevices cat /sys/bus/scsi/devices/*/model

msection proc/limits <<EOF
for i in \`pgrep mongo\`; do echo "PID: \$i"; cat /proc/\$i/cmdline; echo; echo "Limits:"; cat /proc/\$i/limits; echo; done
EOF

msection proc/fds <<EOF
for i in \`pgrep mongo\`; do echo "PID: \$i"; ls -la /proc/\$i/fd /proc/\$i/fdinfo; echo; echo "fdinfo:"; cat /proc/\$i/fdinfo/*; echo; done
EOF

msection smartctl <<EOF
/usr/sbin/smartctl --scan | sed -e "s/#.*$//" | while read i; do /usr/sbin/smartctl --all \$i; done
EOF

msection nr_requests <<EOF
for d in \`find /sys -name nr_requests\`; do echo \$d; cat \$d; done
EOF

msection read_ahead_kb <<EOF
for d in \`find /sys -name read_ahead_kb\`; do echo \$d; cat \$d; done
EOF

msection scheduler <<EOF
for d in \`find /sys -name scheduler\`; do echo \$d; cat \$d; done
EOF


cat <<EOF


==============================================================
MongoDB Diagnostic information has been recorded in: $diagfile
Please attach the contents of $diagfile to the Jira ticket${1+ at:
    https://jira.mongodb.org/browse/$1}
==============================================================

EOF

