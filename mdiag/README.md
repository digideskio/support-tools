mdiag
=====

mdiag is now publicly available, and the version that used to live here has been retired.

The current home of mdiag is:

* https://github.com/mongodb/support-tools

Because that repository is public, please **do not** create Issues or Pull Requests.

Instructions are coming soon for how to report problems, and/or request changes.


FAQs
----

Some (slightly dated, but still helpful) hints for TSEs on how to interpret the output from mdiag.

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

