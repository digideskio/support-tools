mdiag
=====

Script to give to users/customers, to gather a wide variety of system-level diagnostic information.

Latest version: [mdiag.sh](https://raw.github.com/10gen/support-tools/master/mdiag/mdiag.sh)  ([Changelog](https://github.com/10gen/support-tools/commits/master/mdiag/mdiag.sh))

To deploy this to a customer/user on a case, give them the `mdiag.sh` script (eg. attach
it to the Jira ticket), and have them run it with the command-line:

    sudo bash mdiag.sh CS-12345

(substituting an appropriate ticket number/id).  It is not necessary to `chmod` the script.

Please note that the script is undergoing continual development, so check this repo to make sure
that the latest version is being given to users.

See also:
* [XGENTOOLS-658](https://jira.mongodb.org/browse/XGENTOOLS-658)
* [MMSP-537](https://jira.mongodb.org/browse/MMSP-537)
* [SERVER-12698](https://jira.mongodb.org/browse/SERVER-12698)

- Owner: [Kevin Pulo](mailto:kevin.pulo@mongodb.com)

FAQs
----

* ulimits

  * Be careful - the `ulimit` section contains the limits that applied to the shell in which the user ran mdiag
  * This *might not* be the same as what currently applies to `mongod`!
  * Instead, check the `proc/limits` section later in the output, and/or the `limits.conf` section


* What should I look for with respect to Transparent Hugepages (THP)?

  * If setting in `/sys/kernel/mm/transparent_hugepage/enabled` or
    `/sys/kernel/mm/redhat_transparent_hugepage/enabled` is `[always]`
  * Non-zero values in any of the following (or their
    `/sys/kernel/mm/redhat_transparent_hugepage` counterparts):
    * `/sys/kernel/mm/transparent_hugepage/khugepaged/pages_collapsed`
    * `/sys/kernel/mm/transparent_hugepage/khugepaged/full_scans`
  * Large cumulative CPU time for the `khugepaged` process in the `top` output
	* This indicates that `khugepaged` is spending (wasting) time coalescing
	  regular 4KB pages into 2MB Hugepages (which requires scanning the whole
	  page table looking for contiguous pages), and then splitting them up
	  again when they need to be paged out to disk
  * Non-zero values of the following entries in `/proc/vmstat`:
    * `nr_anon_transparent_hugepages`
    * `thp_fault_alloc`
    * `thp_fault_fallback`
    * `thp_collapse_alloc`
    * `thp_collapse_alloc_failed`
    * `thp_split`
  * Non-zero values of the following entries in `/proc/meminfo`:
    * `AnonHugePages`
	* Note: *NOT* the `HugePages*:` entries in `/proc/meminfo`
      * These are red herrings and completely irrelevant: they refer to "regular" Hugepages, not Transparent Hugepages
  * See also: [DOCS-2131](https://jira.mongodb.org/browse/DOCS-2131)
  * See also: [Why THP doesn't play nicely with MongoDB (from HELP-352)](https://jira.mongodb.org/browse/HELP-352?focusedCommentId=493507&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-493507)


* Customer asks: "What does this mdiag script do?"

  Sample answer:
  > The mdiag script gathers a variety of detailed, low-level system
  > information about the host it is run on. This information relates to both
  > the hardware and software setup of the machine, and we often find it helps
  > us to diagnose a wide range of problems with MongoDB deployments. The
  > information includes details about things such as disk/storage setup,
  > memory setup, MongoDB details, operating system configuration details, and
  > so on. You can view the script file in a text editor; each "msection" line
  > indicates a set of commands that are run. None of the commands will modify
  > your system, they simply gather information and save it in a file in /tmp.
  > After running the script, you can peruse this file to see the information
  > that the script has gathered before sending it on to us. The script is able
  > to gather significantly more useful information when run as root, which is
  > why we ask you to run it with sudo.

