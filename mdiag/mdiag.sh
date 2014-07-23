#!/bin/sh

diagfile="/tmp/mdiag-`hostname`.txt"

msection() {
	name="$1"
	shift
	echo -n "Gathering $name info... "
	(
		echo ""
		echo ""
		echo "=========== start section $name ==========="
		if [ $# -eq 0 ]; then
			eval "`cat`"
		else
			"$@"
		fi
		echo "============ end section $name ============"
	) >> "$diagfile" 2>&1
	echo "done"
}

msubsection() {
	name="$1"
	shift
	echo "--> start subsection $f <--"
	if [ $# -eq 0 ]; then
		eval "`cat`"
	else
		"$@"
	fi
	echo "--> end subsection $f <--"
}

printeach() {
	for i; do
		echo "$i"
	done
}

getfiles() {
	for f; do
		echo ""
		ls -l "$f"
		msubsection "$f" cat "$f"
	done
}

getstdinfiles() {
	while read i; do
		getfiles "$i"
	done
}

lsfiles() {
	somefiles=
	restfiles=
	for f; do
		if [ "x$restfiles" = "x" ]; then
			case "$f" in
				--) restfiles=y ;;
				-*) ;;
				*)
					somefiles=y
					break
					;;
			esac
		else
			somefiles=y
			break
		fi
	done
	if [ "x$somefiles" != "x" ]; then
		ls -la "$@"
	fi
}


PATH="$PATH${PATH+:}/usr/sbin:/sbin:/usr/bin:/bin"

echo "========================="
echo "MongoDB Diagnostic Report"
echo "========================="
if [ "$1" ]; then
	echo
	echo "Ticket: https://jira.mongodb.org/browse/$1"
fi
echo 
echo "Please wait while diagnostic information is gathered"
echo "into the $diagfile file..."
echo
echo "If the display remains stuck for more than 5 minutes,"
echo "please press Control-C."
echo

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
msection lsblk lsblk
msection mdstat getfiles /proc/mdstat
msection glibc lsfiles /lib*/libc.so* /lib/*/libc.so*
msection glibc2 /lib*/libc.so* '||' /lib/*/libc.so*
msection ld.so.conf getfiles /etc/ld.so.conf /etc/ld.so.conf.d/*
msection lsb lsb_release -a
msection sysctl sysctl -a
msection sysctl.conf getfiles /etc/sysctl.conf /etc/sysctl.d/*
msection rc.local getfiles /etc/rc.local
msection ifconfig ifconfig -a
msection route route -n
msection iptables iptables -L -v -n
msection iptables_nat iptables -t nat -L -v -n
msection ip_link ip link
msection ip_addr ip addr
msection ip_route ip route
msection ip_rule ip rule
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
msection procinfo getfiles /proc/mounts /proc/self/mountinfo /proc/cpuinfo /proc/meminfo /proc/zoneinfo /proc/swaps /proc/modules /proc/vmstat /proc/loadavg
msection ps ps -eLFww
msection top top -b -n 10 -c
msection top_threads top -b -n 10 -c -H
msection iostat iostat -xtm 1 120
msection rpcinfo rpcinfo -p
msection scsidevices getfiles /sys/bus/scsi/devices/*/model
msection selinux sestatus
msection netstat netstat -anpoe

msection timezone_config getfiles /etc/timezone /etc/sysconfig/clock
msection timedatectl timedatectl
msection localtime lsfiles /etc/localtime
msection localtime_matches find /usr/share/zoneinfo -type f -exec cmp -s \{\} /etc/localtime \; -print

msection dmsetup dmsetup ls
msection device_mapper lsfiles -R /dev/mapper /dev/dm-*

msection lvm_pvs pvs -v
msection lvm_vgs vgs -v
msection lvm_lvs lvs -v

msection mdadm_detail mdadm --detail --scan
msection mdadm_proc cat /proc/mdstat
msection mdadm_md <<EOF
for i in `ls /dev/md`; do mdadm --detail /dev/md/$i; done
EOF

msection dmidecode dmidecode --type memory
msection sensors sensors
msection mcelog getfiles /var/log/mcelog

msection transparent_hugepage <<EOF
lsfiles -R /sys/kernel/mm/{redhat_,}transparent_hugepage
find /sys/kernel/mm/{redhat_,}transparent_hugepage -type f | getstdinfiles
EOF

mongo_pids="`pgrep mongo`"

msection mongo_summary ps -Fww -p $mongo_pids

for pid in $mongo_pids; do

msection proc/$pid <<EOF
lsfiles /proc/$pid/cmdline
msubsection cmdline xargs -n1 -0 < /proc/$pid/cmdline

xargs -n1 -0 < /proc/$pid/cmdline | awk '\$0 == "-f" || \$0 == "--config" { getline; print; }' | getstdinfiles

getfiles /proc/$pid/limits /proc/$pid/mounts /proc/$pid/mountinfo /proc/$pid/smaps /proc/$pid/numa_maps

lsfiles /proc/$pid/fd 
getfiles /proc/$pid/fdinfo/*
EOF

done

msection global_mongodb_conf getfiles /etc/mongodb.conf /etc/mongod.conf
msection global_mms_conf getfiles /etc/mongodb-mms/*

msection smartctl <<EOF
smartctl --scan | sed -e "s/#.*$//" | while read i; do smartctl --all \$i; done
EOF

msection nr_requests <<EOF
find /sys -name nr_requests | getstdinfiles
EOF

msection read_ahead_kb <<EOF
find /sys -name read_ahead_kb | getstdinfiles
EOF

msection scheduler <<EOF
find /sys -name scheduler | getstdinfiles
EOF


cat <<EOF

==============================================================
MongoDB Diagnostic information has been recorded in: $diagfile
Please attach the contents of $diagfile to the Jira ticket${1+ at:
    https://jira.mongodb.org/browse/$1}
==============================================================

EOF

