mdiag.ps1
=====

Script to give to users/customers, to gather a wide variety of system-level diagnostic information.

Owner: [Andrew Ryder](mailto:andrew.ryder@mongodb.com)


### License

DISCLAIMER
----------
Please note: all tools/ scripts in this repo are released for use "AS IS" **without any warranties of any kind**,
including, but not limited to their installation, use, or performance.  We disclaim any and all warranties, either 
express or implied, including but not limited to any warranty of noninfringement, merchantability, and/ or fitness 
for a particular purpose.  We do not warrant that the technology will meet your requirements, that the operation 
thereof will be uninterrupted or error-free, or that any errors will be corrected.

Any use of these scripts and tools is **at your own risk**.  There is no guarantee that they have been through 
thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with 
their use.

You are responsible for reviewing and testing any scripts you run *thoroughly* before use in any non-testing 
environment.

Thanks,  
The MongoDB Support Team


## Usage

The easiest way to run the script is from the Run dialog (Win+R) type the following command and press `Enter`:
```bat
powershell -ExecutionPolicy Unrestricted -File "<full-path-to-mdiag.ps1>" CS-XXXX
```

This may trigger a UAC dialog to which the user will need to click Yes. Although the script will still run if UAC elevation is denied, it may provide less output.

As the script progresses it will fill a text file in the Documents folder of the current user. The file is named "mdiag-\<hostname\>.txt"

## Console Output (stdout)

The console output will look something like this:

```
Gathering section [sysinfo]
Finished with section [sysinfo]. Closing

Gathering section [is_admin]
Finished with section [is_admin]. Closing

Gathering section [tasklist]
Finished with section [tasklist]. Closing

Gathering section ...


Finished. Please attach mdiag-Boomtime.txt to the support case CS-XXXX.

Press any key to continue.
```


## Format of JSON Output File

The JSON output is an array of documents. The first character in the file will always be the array opening square bracket [. The remainder of the file is a series of comma separated JSON documents, with a trailing closing square bracket ] to complete the array. Each document in the array has (at least) the following schema:
```
{
    "ref":  "CS-XXXX",
    "section":  "section-title",
    "ts":  { "$date":  "2014-11-03T16:34:53.123+10:00" },
    "run":  { "$date":  "2014-11-03T16:34:53.123+10:00" },
    "output":  <output-document>,
    "ok":  true,
    "command":  <system-command-that-was-run>
}
```

### Persistent Fields

The following fields always appear in each probe document.

member | description
------ | -----------
`ref` | The argument passed to the script from the command-line. It is suggested to be the case number for identification purposes, however, it may take any string value.
`section` | Descriptive name of the system probe being run, should be unique within any single file. See below for a list of all values that appear in this field, and a definition of the system probe that each represents.
`ts` | Contains the timestamp that bounded the command being performed. In this revision it is 1 second accurate. In a later revision, when longer running statistical collection is performed, this field will contain a sub-document with two fields containing the starting and ending timestamps for those probes.
`run` | The system timestamp at the beginning of the script. This remains constant for the duration of the run and can be used (in conjunction with 'ref') as a (probably) unique identifier given a larger set of probe documents. The combination of 'section' and 'run' should be unique per host (across time).
`ok` | Boolean indicating if the script believes the system probe completed without error.
`command` | A short-form of the system probe that was attempted. May be the actual command-line that was run or a short version of it. The "fingerprint" document is unique in that it sets this value to false.
`output` | Free format value chosen by the command being run.

### Optional Fields

The following fields may appear depending on the results from a probe attempt.

member | description
------ | -----------
`fallback_from` | If present, this indicates that the command and output fields contain the results of a fallback probe that was issued because the desired (primary) probe failed. Several system probes have a less invasive fallback request that can be made in the event that the primary request fails. In such a case, the fallback probe is issued and the fallback_from sub-document indicates the results from the original attempt. The field only appears if the fallback probe is successful. The sub-document contains two fields, `command` is the original command that was tried and `error` is the reason (system verbatim) given for the command failure.



### Section documents in the output

The following section names appear in a given output.

section | content type | description
------- | ------------ | -----------
`fingerprint` | Document | A static fingerprint of the `mdiag` script used to create the output. This permits the unique identification of the script (and version) which produced the remainder of the output.
`sysinfo` | Document | Key/value pairs describing the host system. The operating system and all applied patches are contained. A rough hardware overview, like CPU and memory are here also. This is a good section for getting an overall impression of a system without going into obscene detail (that comes later).
`is_admin` | Boolean | Indicates if the execution context is an administrator. Note that a human administrator who launches the script from a Run dialog or by a regular shell will launch the script into a limited user environment (because Microsoft have painfully learned that people can't be trusted with matches). See instructions above for how to instruct Windows to execute the script in an elevated environment (which will trigger a UAC dialog).
`tasklist` | Array of Document | Currently running processes. Basic information about each process is contained, including the executable that started it, the total CPU time it has consumed, memory statistics and many others.
`network-adapter` | Array of Document | Physical network adapters (or virtual devices that look the same) with information about the status and abilities of the supported physical layers.
`network-interface` | Array of Document | Protocol interface and associated status.
`network-route` | Array of Document | Individual network route entries.
`network-dns-cache` | Array of Document | Local DNS cache entry. Includes name, resolution, TTL, among others.
`services` | Array of Document | System services which contain the wildcard "mongo" somewhere in the name.
`firewall` | Array of Document | Firewall rules that contain the wildcard "mongo" somewhere in the policy.
`storage-disk` | Array of Document | Physical storage systems (or virtual devices that look the same) with information about the characteristics.
`storage-volume` | Array of Document | Information about all partitions (mounted or not, simulated or physical) with information about the characteristics.
`environment` | Array of Document | Literal dump of the key/value pairs from the execution environment, containing all system variables.
`user-list-local` | Array of Document | System descriptions of all local user accounts.
`user-current` | Document | Detailed system descriptor of the current user.
`drivers` | Array of Document | Short description of each active driver. Note that de-activated (but otherwise loaded) drivers are not listed.
`time-change` | Array of Document | The last 10 messages in the system event-log regarding system time changes. The message text should contain details that permit determining the clock before and after the event.



### Changelog


## 1.5.3

 - Fixed boolean capitalization to use JSON symbols true/false, previously output the literals True/False

 
## 1.5.2

 - Fixed crash caused by dependency on .NET 3.5 for time zone information (TSPROJ-386), script should be compliant back to .NET 2.0 again
 - Fixed all ISO dates field, had a typo in the key "$date:" (included the colon in the name) which meant it didn't match strict JSON dates used by MongoDB
 - Added millisecond indicator to all ISO dates, because it will be important for time-series


## 1.5.1

 - Added command-line option -DoNotElevate to prevent the script from attempting to elevate to Administrative privilege
 - Added command-line option -Verbose to print some extra diagnostic info to the shell running the script (largely for debugging)
 - Changed "ts" field now only contains a single date for non-time-based probes (inline with mdiag *nix)
 - Partial fix TSPROJ-386, JSON formatted dates:
   + dates now indicate timezone information (correct ISO-8601 format)
   + all DateTime object fields use the strict JSON date output format (some string command-line outputs still don't yet)
 - Minor JSON layout tweaks (mainly fixing some incorrect indentation)
 - Fixed TSPROJ-476, ConvertTo-JSON is no longer used even when available
   + the startup check is still present because if ConvertTo-JSON is present so is ConvertFrom-CSV (same PS patch) and that cmdlet is handy (and works fine thus far)


## 1.5.0
 - Automatic Administrator elevation, script detects if not admin and tries to relaunch itself requesting promotion by UAC, will fallback to user-mode if denied
 - Removed erroneous use of start/end timestamps for scalar probes (all of them at the moment)
 - Environment output is now a single document, pure key/value rather than sub-docs (because env variables cannot repeat and are JSON compatible keys)
 - Services lists everything now (was previously constrained to just those services which had "mongo" in the name)
 - added network-tcp-active shows current TCP connected/listening ports with associated PID

## 1.4.1
 - Fixed fallback JSON output

 
:construction_worker:
