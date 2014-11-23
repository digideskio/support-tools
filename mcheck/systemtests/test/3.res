
Analyzing file: 2.mdiags
Match: /dev/mapper/vg_os-lv_swap	swap	swap	defaults	0	0
INFO - disk-0001 - Presence of swap partition in /etc/fstab - in etc/fstab
  /dev/mapper/vg_os-lv_swap	swap	swap	defaults	0	0

Match: /dev/dm-1                               partition	4194296	136820	-1
INFO - disk-0002 - Presence of swap partition in /proc/swaps - in proc/swaps
  /dev/dm-1                               partition	4194296	136820	-1

Match: 256, /sda
Match: 256, /sda1
Match: 256, /sda2
Match: 256, /sda3
Match: 256, /sdb
Match: 256, /sdb1
Match: 256, /dm-0
Match: 256, /dm-1
Match: 256, /dm-2
Match: 256, /dm-3
Match: 256, /dm-4
Match: 256, /dm-5
Match: 256, /dm-6
Match: 256, /dm-7
Match: 256, /dm-8
Match: 256, /dm-9
Match: 256, /dm-10
Match: 256, /dm-11
FAIL - disk-0003 - Read ahead is too high, it should not be bigger than 64 - in blockdev
  256, /sda
  256, /sda1
  256, /sda2
  256, /sda3
  256, /sdb
  256, /sdb1
  256, /dm-0
  256, /dm-1
  256, /dm-2
  256, /dm-3
  256, /dm-4
  256, /dm-5
  256, /dm-6
  256, /dm-7
  256, /dm-8
  256, /dm-9
  256, /dm-10
  256, /dm-11
  See: http://docs.mongodb.org/manual/administration/production-notes/#mongodb-on-linux

WARNING - Skipping rule hugepage-0001, section '/sys/kernel/mm/transparent_hugepage/enabled' missing
Match: never
FAIL - hugepage-0002 - Hugepage are enabled, they should not - in /sys/kernel/mm/redhat_transparent_hugepage/enabled
  never

Match: ipmi_si: Interface detection failed
Match: ipmi_si: Interface detection failed
Match: ipmi_si: Interface detection failed
Match: opcacta[14158]: segfault at 18 ip 00007fbeb95b07a8 sp 00007fffcb99a1a8 error 4 in libOvXpl.so[7fbeb9534000+1fa000]
FAIL - log-0001 - Found potential error or warning messages in dmesg - in dmesg
  ipmi_si: Interface detection failed
  ipmi_si: Interface detection failed
  ipmi_si: Interface detection failed
  opcacta[14158]: segfault at 18 ip 00007fbeb95b07a8 sp 00007fffcb99a1a8 error 4 in libOvXpl.so[7fbeb9534000+1fa000]

Match: NUMA: Allocated memnodemap from 100000 - 180840
FAIL - numa-0001 - References to NUMA in dmesg, it may be active - in dmesg
  NUMA: Allocated memnodemap from 100000 - 180840
  See: http://docs.mongodb.org/manual/administration/production-notes/#production-numa

Match: Red Hat Enterprise Linux Server release 6.5 (Santiago)
INFO - os-0001 - OS description - in /etc/system-release
  Red Hat Enterprise Linux Server release 6.5 (Santiago)

NOMATCH - os-0002 - SUSE version must at least 11 - in /etc/system-release
  No matching line, not defined as required

Match: 6.5
PASS - os-0003 - Red Hat is version 5.7 or more - in /etc/system-release
  6.5

Match: 1024
FAIL - os-0011 - Soft limit for processes is too low, must be at least 64000 - in proc/limits - 7470
  1024

Match: 127420
PASS - os-0012 - Hard limit of 64000 processes or more - in proc/limits - 7470
  127420

Match: 12000
FAIL - os-0013 - Soft limit for open files is too low, must be at least 64000 - in proc/limits - 7470
  12000

Match: 12000
FAIL - os-0014 - Hard limit for open files is too low, must be at least 64000 - in proc/limits - 7470
  12000

Match: 1620510
PASS - os-0021 - Kernel max of 98000 open files or more - in sysctl
  1620510

Match: 32768
PASS - os-0022 - Kernel max PID of 32768 or more - in sysctl
  32768

Match: 254840
PASS - os-0023 - Kernel max of 64000 threads or more - in sysctl
  254840

Match: 0
PASS - os-0024 - Zone reclaim mode off - in sysctl
  0

NOMATCH - vm-0001 - VMWare ballooning is enabled - in procinfo
  No matching line, not defined as required

