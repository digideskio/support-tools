###################
# mdiag.ps1 - Windows Diagnostic Script for MongoDB

param(
	[string] $JiraTicketNumber,
	[switch] $DoNotElevate,
	[switch] $Verbose,
	[switch] $Experimental
)

# FingerprintOutputDocument
# this is the output field of the fingerprint probe
# should be kept at the top of the file for ease of access
#
Set-Variable FingerprintOutputDocument -option Constant @{
	os = "Windows";
	shell = "powershell";
	script = "mdiag";
	version = "1.6.0";
	revdate = "2016-03-19";
}

# 
# checking stuff...
#
if( $Verbose ) {
	$VerbosePreference="Continue"
}

Write-Verbose "`$PSCommandPath: $PSCommandPath"
Write-Verbose "$( $FingerprintOutputDocument | Out-String )"

if( $Experimental ) {
	Write-Verbose "Experimental probes are enabled"
}

# get a Jira ticket number if we don't already have one
if( "" -Eq $JiraTicketNumber ) {
	Write-Host ""
	$JiraTicketNumber = Read-Host "Please provide a Jira ticket reference number"
}

Write-Verbose "`$JiraTicketNumber: $JiraTicketNumber"
Write-Verbose "Checking permissions"

# check if we are admin
if( -Not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator") ) {
	Write-Verbose "Script is not run with administrative user"

	# see if we can elevate
	if( $DoNotElevate ) {
		# user expressly asked to avoid privilege elevation (or the script has already been here)
		Write-Verbose "Instructed not to elevate or we're in a hall of mirrors.. aborting elevation"
		Write-Warning "Not running as administrative user but instructed not to elevate. Some health checks may fail."
	}
	elseif( ( Get-WmiObject Win32_OperatingSystem | select BuildNumber ).BuildNumber -ge 6000 ) {
		Write-Verbose "Found UAC-enabled system. Attempting to elevate ..."

		# when elevating we need to twiddle the command-line a little to be more robust
		$CommandLine = "powershell -ExecutionPolicy Unrestricted -File `"$PSCommandPath`" $JiraTicketNumber"

		# do not attempt elevation again on relaunch, in case some bizarro world DC policy causes Runas to fake us out (because that would cause an infinite loop)
		$CommandLine += " -DoNotElevate"

		if( $Verbose ) {
			$CommandLine += " -Verbose"
		}

		if( $Experimental ) {
			$CommandLine += " -Experimental"
		}
		
		Write-Verbose "`$CommandLine: $CommandLine"

		try {
			Start-Process -FilePath PowerShell.exe -Verb Runas -ArgumentList "$CommandLine"
			Write-Host ""
			Write-Host "Script will run in a new window, please check there for further instructions."
			Write-Host ""
			break;
			# shouldn't get here
		}
		catch {
			Write-Warning "Elevation attempt by relaunch failed. Will continue without administrative privileges."
		}
	}
	else {
		# Server 2003 ? (it is theoretically possible to install powershell there)
		Write-Verbose "Wow, really?! You got powershell running on a pre-6 kernel.. I salute you sir, good job old chap!"
		Write-Warning "System does not support UAC."
	}
}

$diagfile = Join-Path @([Environment]::GetFolderPath('Personal')) $("mdiag-" + $(hostname) + ".txt")

Write-Verbose "`$diagfile: $diagfile"

# check for ConvertTo-JSON
$script:csv_available = Get-Command "ConvertFrom-Csv" -errorAction SilentlyContinue -CommandType Cmdlet;

Write-Verbose "`$script:csv_available: $csv_available"


##################
# Public API
#
# The functions in this section constitute the public API of mdiag.ps1
# Use these in the script portion below. Please don't directly call other functions; the
#	interfaces there are not guaranteed to be constant between versions of this script.

Function probe( $doc ) {
	# $doc should be: @{
	#  name = "section title";
	#  cmd = "invoke-cmd";
	#  (opt) alt = "alternative-invoke-cmd";
	#  (opt) samples = number of times to run the command (default 1)
	#  (opt) period = milliseconds between runs (default 1000), only applicable when samples > 1
	# }

	if( !( $doc.name ) -or !( $doc.cmd ) ) {
		throw "assert: malformed section descriptor document, must have 'name' and 'cmd' members at least";
	}

	Write-Verbose "Gathering section [$($doc.name)]"

	# record startts if likely to be needed
	$startts = $null
	if( $doc.samples -gt 1 ) {
		$startts = Get-Date

		# determine sleep time
		$period = @( 1000, $doc.period )[$doc.period -ne $null];

		if( ( $period -gt 5000 ) -or ( $period -lt 100 ) ) {
			# clamp
			Write-Warning "probe period $($doc.name) outside range of 100 to 5000, defaulting to 1000";
			$period = 1000;
		}

		Write-Progress $doc.name -ParentId 1 -Status "sampling" -PercentComplete 0 -SecondsRemaining $( $period * $doc.samples / 1000 )
	}

	# run the probe once
	$cmdobj = _docmd $doc.cmd

	if( $cmdobj.ok ) {
		# check to see if it should repeat
		if( $doc.samples -gt 1 ) {
			# reformat output member to an array - thank you microsoft for making this ludicrously difficult
			$oco = $cmdobj.output;
			$cmdobj.output = $null;

			for( $j = 1 ; $j -lt $doc.samples ; $j++ ) {
				Write-Progress $doc.name -ParentId 1 -Status "sampling" -PercentComplete $( $j * 100 / $doc.samples ) -SecondsRemaining $( $period * ( $doc.samples - $j ) / 1000 );
				
				# calculate burn time remaining before the start of the next run
				$burn = ( $period * $j ) - ( $(Get-Date) - $startts ).TotalMilliseconds;
				Write-Verbose "calculated burn $burn"
				if( $burn -gt 0 ) {
					# if this is less than zero, then the test takes longer than a period cycle
					Sleep -m $burn
				}
				else {
					# hmm.. should this warning be drifted too to only log if it's getting worse?
					Write-Warning "probe period $($doc.name) took too long to run and is falling behind desired cadence"
				}
				
				# run the probe again
				$coredux = _docmd $doc.cmd
				
				if( $cmdobj.output ) {
					$cmdobj.output += ,$coredux.output;
				}
				else {
					# fun little dance required because creating an array with a single member ALWAYS unwinds it - powershell cannot be overruled
					$cmdobj.output = @($oco,$coredux.output);
				}
			}
			
			Write-Progress $doc.name -ParentId 1 -Completed
		}
	}
	else {
		$startts = $null

		if( $null -ne $doc.alt ) {
			# preferred cmd failed and we have a fallback, so try that
			# @todo: time-series is not really compatible with fallback yet
			Write-Verbose " | Preference attempt failed, but have a fallback to try..."

			$fbcobj = _docmd $doc.alt

			if( $fbcobj.ok ) {
				Write-Verbose " | ... which succeeded!"
			}

			$fbcobj.fallback_from = @{
				command = $cmdobj.command;
				error = $cmdobj.error;
			}
			$cmdobj = $fbcobj;
		}
	}

	_emitdocument $doc.name $startts $cmdobj

	Write-Verbose "Finished with section [$($doc.name)]. Closing`n"
}

###############
# Generic internal functions
#
# Please don't call these in the script portion of the code. The API here will never freeze.

Function _tojson_string( $v ) {
	# @todo: any other escapes?
	$v = $v.Replace("`"","\`"");
	$v = $v.Replace("\","\\");
	"`"{0}`"" -f $v
}

# _tojson_date
# provide a JSON encoded date
Function _tojson_date( $v ) {
	"{{ `"`$date`": `"{0}`" }}" -f $( _iso8601_string $v );
}

# _tojson_object
# pipe in a stream of @{Name="",Value=*} for the properties of the object
function _tojson_object( $indent ) {
	$ret = $( $input | ForEach-Object { "{0}`t`"{1}`": {2}," -f $indent, $_.Name, $( _tojson_value $( $indent + "`t" ) $_.Value ) } | Out-String )
	"{{`n{0}`n{1}}}" -f $ret.Trim("`r`n,"), $indent
}

# _tojson_array
# pipe in a stream of objects for the elements of the array
function _tojson_array( $indent ) {
	if( @($input).Count -eq 0 ) {
		"[]"
	}
	else {
		$input.Reset()
		$ret = $( $input | ForEach-Object { "{0}`t{1}," -f $indent, $( _tojson_value $( $indent + "`t" ) $_ ) } | Out-String )
		"[`n{0}`n{1}]" -f $ret.Trim("`r`n,"), $indent
	}
}

# _tojson_value
# JSON encode object value, not using ConvertTo-JSON due to TSPROJ-476
Function _tojson_value( $indent, $obj ) {
	if( $obj -eq $null ) {
		"null";
	}
	elseif( $indent.Length -gt 4 ) {
		# aborting recursion due to object depth; summarize the current object
		# if it's an array we put in the count, anything else ToString()
		if( $obj.GetType().IsArray ) {
			$obj.Length
		}
		else {
			_tojson_string $obj.ToString()
		}
	}
	elseif( $obj.GetType().IsArray ) {
		$obj | _tojson_array( $indent )
	}
	else {
		switch ( $obj.GetType().Name ) {
			"Hashtable" {
				$obj.GetEnumerator() | Select @{Name='Name';Expression={$_.Key}},Value | _tojson_object( $indent )
				break
			}
			"String" {
				_tojson_string $obj
				break
			}
			"DateTime" {
				_tojson_date $obj
				break
			}
			"Boolean" {
				@('false','true')[$obj -eq $true]
				break
			}
			{ "Int32","UInt32","Int64","UInt64" -contains $_ } {
				# symbolic or integrals, write plainly
				$obj.ToString()
				break
			}
			default {
				if( $obj.GetType().IsClass ) {
					$obj.psobject.properties.GetEnumerator() | _tojson_object( $indent )
				}
				else {
					# dunno, just represent as simple as possible
					_tojson_string $obj.ToString()
				}
			}
		}
	}
}

# _tojson (internal)
# emit to file the JSON encoding of supplied obj using whatever means is available
#
Function _tojson( $obj ) {
	# TSPROJ-476 ConvertTo-JSON dies on some data eg: Get-NetFirewallRule | ConvertTo-Json = "The converted JSON string is in bad format."
	# using internal only now, probably forever
	return _tojson_value "" $obj;
}

# _emitdocument (internal)
# re-format a probe document result into an output section document
#
Function _emitdocument( $section, $startts, $cmdobj ) {
	$cmdobj.ref = $JiraTicketNumber;
	$cmdobj.tag = $script:rundate;
	$cmdobj.section = $section;

	if( $startts -Eq $null ) {
		$cmdobj.ts = Get-Date;
	}
	else {
		$cmdobj.ts = @{
			start = $startts;
			end = Get-Date;
		};
	}

	# make an array of  documents
	if( !( $isfirstdocument ) ) {
		Add-Content $diagfile ","
	}

	$script:isfirstdocument = $false

	try {
		Add-Content $diagfile $(_tojson $cmdobj)
	}
	catch {
		$cmdobj.output = ""
		$cmdobj.error = "output conversion to JSON failed"
		$cmdobj.ok = $false

		# give it another shot without the output, just let it die if it still has an issue
		Add-Content $diagfile $(_tojson $cmdobj)
	}
}

# _iso8601_string
# get current (or supplied) DateTime formatted as ISO-8601 localtime (with TZ indicator)
#
function _iso8601_string( [DateTime] $date ) {
	# TSPROJ-386 timestamp formats
	# turns out the "-s" format of windows is ISO-8601 with the TZ indicator stripped off (it's in localtime)
	# so... we just need to append the TZ that was used in the conversion thusly:
	if( $date -eq $null ) {
		$date = Get-Date;
	}
	if( !( $script:tzstring ) ) {
		# [System.TimeZoneInfo]::Local.BaseUtcOffset; <- should use this "whenever possible" which is .NET 3.5+
		# using the legacy method instead for maximum compatibility
		$tzo = [System.TimeZone]::CurrentTimeZone.GetUtcOffset( $date );
		$script:tzstring = "{0}{1}:{2:00}" -f @("+","")[$tzo.Hours -lt 0], $tzo.Hours, $tzo.Minutes
	}
	# ISO-8601
	return "{0}.{1:000}{2}" -f $( Get-Date -Format s -Date $date ), $date.Millisecond, $script:tzstring;
}

Function _docmd {
	# Allow for conceptual differences between Unix and Windows here.
	#Write-Error "Passed arguments [$args]`n" # Reenable this for debugging if you need

	# selecting only the first arg in the stream now due to possible mongoimport killers like ' " etc (which come out as \u00XX
	$ret = @{ command = ("$args").Split("|")[0].Trim() }
	$text = ""
	$ok = $true;

	Try {
		#Write-Host "Trying to run command [$args]`n"
		# -ErrorVariable has no effect on Invoke-Expression, errors always pipe to STDERR
		# $LASTEXITCODE is always zero (success!)
		# $? is always True (success!)
		# on failure the return value is always null though (thus far), so there's that
		# $error seems to be the last definitive authority but is difficult to work with
		$preerrcount = $error.Length.Length  # wtf?
		$ret.output = Invoke-Expression "$args"

		if( $preerrcount -ne $error.Length.Length ) {
			# there was an error that Invoke-Expression desperately tried to hide
			# yes, Invoke-Expression is really this broken - it is difficult to detect if the command had a problem
			$ok = $false
			$ret.error = $error[0].Exception.Message	
		}
	}
	Catch {
		$ok = $false
		$ret.error = $error[0].Exception.Message
	}

	$simpleOk = $?

	if( !$simpleOk ) {
		$ok = $false;
	}

	$ret.ok = $ok

	return $ret
}

###############
# Script-scoped variables
$script:isfirstdocument = $true
$script:rundate = Get-Date

###############
# Begin diag output

Set-Content $diagfile "["

# script relies on detecting changes in global error-state due to the uncatchable error behaviour of Invoke-Expression
# clearing this just ensures that it will have space to buffer any errors that occur
$error.Clear();

###############
# Script portion
#
# This is where  you define the tests you want to run, using the document structure definition provided

# probe @{ name = "", cmd = "", alt = "" }
# 
# name = verbatim content of the "section" value in the output for this probe result
# cmd = powershell command-line to execute and capture output from
# alt = alternative to cmd to try if 'cmd' reports any kind of error (stderr still goes to the console)
# 
##>

$focsv = [string]::Empty;
if( $script:csv_available ) {
	$focsv = " /FO CSV | ConvertFrom-Csv";
}

_emitdocument "fingerprint" $null @{ command = $false; ok = $true; output = $FingerprintOutputDocument; }

$probes = @();

$probes +=, @{ name = "sysinfo";
	# @todo: need to switch to this:
	#cmd = "Get-WmiObject Win32_OperatingSystem";
	cmd = $( "systeminfo{0}" -f $focsv );
}

$probes +=, @{ name = "is_admin";
	cmd = "([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')"
}

$probes +=, @{ name = "memory-virtual";
	cmd = "Get-WmiObject Win32_PerfRawData_PerfOS_Memory | Select A*,Cache*,Commit*,Pool*"
}

$probes +=, @{ name = "memory-physical";
	cmd = "Get-WmiObject Win32_PhysicalMemory | Select BankLabel,DeviceLocator,FormFactor,Capacity,Speed"
}

$probes +=, @{ name = "tasklist";
	cmd = "Get-Process | Select Name,Handles,VirtualMemorySize64,WorkingSet64,PagedMemorySize64,NonpagedSystemMemorySize64,PagedSystemMemorySize64,PrivateMemorySize64,Path,Company,CPU,FileVersion,ProductVersion,Description,Product,Id,PriorityClass,TotalProcessorTime,BasePriority,PeakWorkingSet64,PeakVirtualMemorySize64,StartTime,@{Name='Threads';Expression={`$_.Threads.Count}}";
	alt = $( "tasklist{0}" -f $focsv );
}

$probes +=, @{ name = "network-adapter";
	cmd = "Get-NetAdapter | Select ifIndex,ifAlias,ifDesc,ifName,DriverVersion,MacAddress,Status,LinkSpeed,MediaType,MediaConnectionState,DriverInformation,DriverFileName,NdisVersion,DeviceName,DriverName,DriverVersionString,MtuSize";
	alt = "netsh wlan show interfaces";
}
$probes +=, @{ name = "network-interface";
	cmd = "Get-NetIPAddress | Select ifIndex,PrefixOrigin,SuffixOrigin,Type,AddressFamily,AddressState,Name,ProtocolIFType,IPv4Address,IPv6Address,IPVersionSupport,PrefixLength,SubnetMask,InterfaceAlias,PreferredLifetime,SkipAsSource,ValidLifetime";
	alt = "ipconfig /all";
}
$probes +=, @{ name = "network-route";
	cmd = "Get-NetRoute | Select DestinationPrefix,InterfaceAlias,InterfaceIndex,RouteMetric,TypeOfRoute";
	alt = "route print";
}
$probes +=, @{ name = "network-dns-cache";
	cmd = "Get-DnsClientCache | Get-Unique | Select Entry,Name,Data,DataLength,Section,Status,TimeToLive,Type";
}
# @todo: this is a bit pants, but Get-NetTCPConnection doesn't have the PID so netstat provides better data
$tcpcmd = "netstat -ano -p TCP";
if( $script:csv_available ) {
	$tcpcmd += " | select -skip 3 | foreach {`$_.Substring(2) -replace `" {2,}`",`",`" } | ConvertFrom-Csv";
}
$probes +=, @{ name = "network-tcp-active";
	cmd = $tcpcmd;
}

$probes +=, @{ name = "services";
	cmd = "Get-Service | Select Di*,ServiceName,ServiceType,@{Name='Status';Expression={`$_.Status.ToString()}},@{Name='ServicesDependedOn';Expression={@(`$_.ServicesDependedOn.Name)}}";
}

$probes +=, @{ name = "firewall";
	cmd = "Get-NetFirewallRule | Where-Object {`$_.DisplayName -like '*mongo*'} | Select Name,DisplayName,Enabled,@{Name='Profile';Expression={`$_.Profile.ToString()}},@{Name='Direction';Expression={`$_.Direction.ToString()}},@{Name='Action';Expression={`$_.Action.ToString()}},@{Name='PolicyStoreSourceType';Expression={`$_.PolicyStoreSourceType.ToString()}}";
}

$probes +=, @{ name = "storage-disk";
	cmd = "Get-Disk | Select PartitionStyle,ProvisioningType,OperationalStatus,HealthStatus,BusType,BootFromDisk,FirmwareVersion,FriendlyName,IsBoot,IsClustered,IsOffline,IsReadOnly,IsSystem,LogicalSectorSize,Manufacturer,Model,Number,NumberOfPartitions,Path,PhysicalSectorSize,SerialNumber,Size";
	alt = "Get-WmiObject Win32_DiskDrive | Select SystemName,BytesPerSector,Caption,CompressionMethod,Description,DeviceID,InterfaceType,Manufacturer,MediaType,Model,Name,Partitions,PNPDeviceID,SCSIBus,SCSILogicalUnit,SCSIPort,SCSITargetId,SectorsPerTrack,SerialNumber,Signature,Size,Status,TotalCylinders,TotalHeads,TotalSectors,TotalTracks,TracksPerCylinder";
}
$probes +=, @{ name = "storage-partition";
	# DriverLetter is borked, need to detect the nul byte included in the length for non-mapped partitions (..yeah)
	cmd = "Get-Partition | Select OperationalStatus,Type,AccessPaths,DiskId,DiskNumber,@{Name='DriveLetter';Expression={@(`$null,`$_.DriveLetter)[`$_.DriveLetter[0] -ge 'A']}},GptType,Guid,IsActive,IsBoot,IsHidden,IsOffline,IsReadOnly,IsShadowCopy,IsSystem,MbrType,NoDefaultDriveLetter,Offset,PartitionNumber,Size,TransitionState";
	alt = "Get-WmiObject Win32_DiskPartition"
}
$probes +=, @{ name = "storage-volume";
	cmd = "Get-Volume | Select * -Exclude P*,C*";
	alt = "Get-WmiObject Win32_LogicalDisk | Select Compressed,Description,DeviceID,DriveType,FileSystem,FreeSpace,MediaType,Name,Size,SystemName,VolumeSerialNumber";
}

$probes +=, @{ name = "environment";
	cmd = "Get-Childitem env: | ForEach-Object {`$j=@{}} {`$j.Add(`$_.Name,`$_.Value)} {`$j}";
}

$probes +=, @{ name = "user-list-local";
	cmd = "Get-WMIObject Win32_UserAccount | Where-Object {`$_.LocalAccount -eq `$true} | Select Caption,Name,Domain,Description,AccountType,Disabled,Lockout,SID,Status";
}
$probes +=, @{ name = "user-current";
	cmd = "[System.Security.Principal.WindowsIdentity]::GetCurrent()";
	alt = "whoami";
}

$probes +=, @{ name = "drivers";
	# @todo: Get-WindowsDriver -Online (with -All perhaps) though this provides somewhat different data
	cmd = "Get-WmiObject -Class Win32_SystemDriver | Where-Object -FilterScript {`$_.State -eq 'Running'} | Select Name,Status,Description";
}

$probes +=, @{ name = "time-change";
	cmd = "Get-EventLog -LogName System -Source @('Microsoft-Windows-Kernel-General','Microsoft-Windows-Time-Service') | Select -first 10";
}

if( $Experimental ) {
	$probes +=, @{ name = "performance-counters";
		cmd = "Get-Counter | select -expandproperty CounterSamples";
		period = 2000;
		samples = 30;
	}
}

Write-Host "Beginning collection...";
for( $j = 0 ; $j -lt $probes.Length ; $j++ ) {
	Write-Progress "Gathering diagnostic information" -Id 1 -Status $( $probes[$j].name ) -PercentComplete $( $j * 100 / $probes.Length );
	probe $probes[$j];
}
Write-Progress "Gathering diagnostic information" -Id 1 -Status "Done" -Completed;

###############
# Final
# complete the JSON array, making the whole document a valid JSON value
#
Add-Content $diagfile "]`n"

Write-Host "Finished."
Write-Host ""
Write-Host "Please attach '$diagfile' to the support case $JiraTicketNumber."
Write-Host ""
Write-Host "Press any key to continue ..."
$x = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
