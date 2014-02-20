mdiag
=====

Script to give to users/customers, to gather a wide variety of system-level diagnostic information.

To deploy this to a customer/user on a case, give them the [mdiag.sh](./mdiag.sh) script (eg. attach
it to the Jira ticket), and have them run it with the command-line:

    sudo bash mdiag.sh CS-12345

(substituting an appropriate ticket number/id).

See also [XGENTOOLS-658](https://jira.mongodb.org/browse/XGENTOOLS-658).

- Owner: [Kevin Pulo](mailto:kevin.pulo@@mongodb.com) ?

FAQs
----

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

