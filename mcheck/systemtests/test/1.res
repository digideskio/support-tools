
Analyzing file: 1.mdiags
FAIL - hugepage-0002 - Hugepage are enabled, they should not - in /sys/kernel/mm/redhat_transparent_hugepage/enabled
  never

FAIL - log-0001 - Found potential error or warning messages in dmesg - in dmesg
  ACPI Warning: Invalid length for Pm2ControlBlock: 16, using default 8 (20090903/tbfadt-611)
  ERST: Error Record Serialization Table (ERST) support is initialized.
  ACPI Error: No handler for Region [IPMI] (ffff883009d84270) [IPMI] (20090903/evregion-319)
  ACPI Error: Region IPMI(7) has no handler (20090903/exfldio-295)
  ACPI Error (psparse-0537): Method parse/execution failed [\_SB_.PMI0._GHL] (Node ffff882009d71600), AE_NOT_EXIST
  ...

FAIL - numa-0001 - References to NUMA in dmesg, it may be active - in dmesg
  NUMA: Allocated memnodemap from b000 - 8b400

FAIL - os-0011 - Soft limit for processes is too low, must be at least 64000 - in proc/limits - 58346
  1024

FAIL - os-0011 - Soft limit for processes is too low, must be at least 64000 - in proc/limits - 19540
  1024

FAIL - os-0011 - Soft limit for processes is too low, must be at least 64000 - in proc/limits - 58509
  1024

FAIL - os-0011 - Soft limit for processes is too low, must be at least 64000 - in proc/limits - 10450
  1024

FAIL - os-0011 - Soft limit for processes is too low, must be at least 64000 - in proc/limits - 19658
  1024

FAIL - os-0013 - Soft limit for open files is too low, must be at least 64000 - in proc/limits - 58346
  1024

FAIL - os-0013 - Soft limit for open files is too low, must be at least 64000 - in proc/limits - 19540
  1024

FAIL - os-0013 - Soft limit for open files is too low, must be at least 64000 - in proc/limits - 58509
  1024

FAIL - os-0013 - Soft limit for open files is too low, must be at least 64000 - in proc/limits - 10450
  1024

FAIL - os-0013 - Soft limit for open files is too low, must be at least 64000 - in proc/limits - 19658
  1024

FAIL - os-0014 - Hard limit for open files is too low, must be at least 64000 - in proc/limits - 58346
  4096

FAIL - os-0014 - Hard limit for open files is too low, must be at least 64000 - in proc/limits - 19540
  4096

FAIL - os-0014 - Hard limit for open files is too low, must be at least 64000 - in proc/limits - 58509
  4096

FAIL - os-0014 - Hard limit for open files is too low, must be at least 64000 - in proc/limits - 10450
  4096

FAIL - os-0014 - Hard limit for open files is too low, must be at least 64000 - in proc/limits - 19658
  4096

FAIL - os-0024 - Zone reclaim mode is on, it should be off - in sysctl
  1

