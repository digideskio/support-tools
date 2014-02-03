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

shopt -s nullglob >> "$diagfile" 2>&1

msection args printeach "$@"
msection date date
msection whoami whoami
msection path echo "$PATH"
msection ld_library_path echo "$LD_LIBRARY_PATH"
msection ld_preload echo "$LD_PRELOAD"
msection pythonpath echo "$PYTHONPATH"
msection pythonhome echo "$PYTHONHOME"
msection distro getfiles /etc/*release /etc/*version
msection uname uname -a
msection blockdev blockdev --report
msection glibc ls -l /lib*/libc.so* /lib/*/libc.so*
msection glibc2 /lib*/libc.so* '||' /lib/*/libc.so*
msection ld.so.conf getfiles /etc/ld.so.conf /etc/ld.so.conf.d/*
msection lsb lsb_release -a
msection sysctl sysctl -a
msection sysctl.conf getfiles /etc/sysctl.conf /etc/sysctl.d/*
msection ifconfig ifconfig -a
msection route route -n
msection iptables iptables -L -v -n
msection iptables_nat iptables -t nat -L -v -n
msection ip_link ip link
msection ip_addr ip addr
msection ip_route ip route
msection ip_rule ip rule
msection keepalive cat /proc/sys/net/ipv4/tcp_keepalive_time
msection hosts getfiles /etc/hosts
msection host.conf getfiles /etc/host.conf
msection resolv getfiles /etc/resolv.conf
msection nsswitch getfiles /etc/nsswitch.conf
msection networks getfiles /etc/networks
msection dmesg dmesg
msection lspci lspci -vvv
msection ulimit ulimit -a
msection limits.conf getfiles /etc/security/limits.conf /etc/security/limits.d/*
msection fstab getfiles /etc/fstab
msection df-h df -h
msection df-k df -k
msection mount mount
msection procinfo getfiles /proc/mounts /proc/self/mountinfo /proc/cpuinfo /proc/meminfo /proc/swaps /proc/modules /proc/vmstat
msection top top -b -n 10
msection iostat iostat -xtm 5 10
msection rpcinfo rpcinfo -p
msection scsidevices getfiles /sys/bus/scsi/devices/*/model
msection selinux sestatus

msection timezone_config getfiles /etc/timezone /etc/sysconfig/clock
msection timedatectl timedatectl
msection localtime ls -l /etc/localtime
msection localtime_matches find /usr/share/zoneinfo -type f -exec cmp -s \{\} /etc/localtime \; -print

msection dmsetup dmsetup ls
msection device_mapper ls -laR /dev/mapper /dev/dm-*

msection lvm_pvs pvs -v
msection lvm_vgs vgs -v
msection lvm_lvs lvs -v

msection dmidecode dmidecode --type memory
msection sensors sensors
msection mcelog mcelog

msection transparent_hugepage <<EOF
ls -lR /sys/kernel/mm/{redhat_,}transparent_hugepage
find /sys/kernel/mm/{redhat_,}transparent_hugepage -type f | getfiles
EOF

msection proc/limits <<EOF
for i in \`pgrep mongo\`; do echo "PID: \$i"; cat /proc/\$i/cmdline; echo; echo "Limits:"; cat /proc/\$i/limits; echo; done
EOF

msection proc/fds <<EOF
for i in \`pgrep mongo\`; do echo "PID: \$i"; ls -la /proc/\$i/fd /proc/\$i/fdinfo; echo; echo "fdinfo:"; cat /proc/\$i/fdinfo/*; echo; done
EOF

msection proc/smaps <<EOF
for i in \`pgrep mongo\`; do echo "PID: \$i"; ls -la /proc/\$i/smaps; cat /proc/\$i/smaps; echo; done
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

