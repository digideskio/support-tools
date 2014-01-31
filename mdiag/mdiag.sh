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

getfiles() {
	if [ $# -eq 0 ]; then
		while read i; do
			getfiles "$i"
		done
	else
		for f; do
			echo ""
			ls -l "$f"
			echo "--> start $f <--"
			cat "$f"
			echo "--> end $f <--"
		done
	fi
}

PATH="$PATH${PATH+:}/usr/sbin:/sbin:/usr/bin:/bin"

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
msection path echo "$PATH"
msection uname uname -a
msection blockdev blockdev --report
msection glibc ls -l /lib*/libc.so* /lib/*/libc.so*
msection glibc2 /lib*/libc.so*
msection glibc3 /lib/*/libc.so*
msection lsb lsb_release -a
msection sysctl sysctl -a
msection ifconfig ifconfig -a
msection route route -n
msection dmesg dmesg
msection lspci lspci -vvv
msection ulimit ulimit -a
msection df-h df -h
msection df-k df -k
msection mount mount
msection procinfo getfiles /proc/mounts /proc/self/mountinfo /proc/cpuinfo /proc/meminfo /proc/swaps /proc/modules /proc/vmstat
msection top top -b -n 10
msection iostat iostat -xtm 5 10
msection rpcinfo rpcinfo -p
msection scsidevices getfiles /sys/bus/scsi/devices/*/model

msection dmsetup dmsetup ls
msection device_mapper ls -laR /dev/mapper /dev/dm-*

msection lvm_pvs pvs -v
msection lvm_vgs vgs -v
msection lvm_lvs lvs -v

msection dmidecode dmidecode --type memory
msection sensors sensors
msection mcelog mcelog

msection transparent_hugepage <<EOF
ls -lR /sys/kernel/mm/*transparent_hugepage
find /sys/kernel/mm/*transparent_hugepage -type f | getfiles
EOF

msection proc/limits <<EOF
for i in \`pgrep mongo\`; do echo "PID: \$i"; cat /proc/\$i/cmdline; echo; echo "Limits:"; cat /proc/\$i/limits; echo; done
EOF

msection proc/fds <<EOF
for i in \`pgrep mongo\`; do echo "PID: \$i"; ls -la /proc/\$i/fd /proc/\$i/fdinfo; echo; echo "fdinfo:"; cat /proc/\$i/fdinfo/*; echo; done
EOF

msection smartctl <<EOF
smartctl --scan | sed -e "s/#.*$//" | while read i; do smartctl --all \$i; done
EOF

msection nr_requests <<EOF
find /sys -name nr_requests | getfiles
EOF

msection read_ahead_kb <<EOF
find /sys -name read_ahead_kb | getfiles
EOF

msection scheduler <<EOF
find /sys -name scheduler | getfiles
EOF


cat <<EOF


==============================================================
MongoDB Diagnostic information has been recorded in: $diagfile
Please attach the contents of $diagfile to the Jira ticket${1+ at:
    https://jira.mongodb.org/browse/$1}
==============================================================

EOF

