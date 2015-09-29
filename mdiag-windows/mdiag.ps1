###################
# mdiag.ps1 - Windows Diagnostic Script for MongoDB

param(
	[string] $JiraTicketNumber,
	[switch] $DoNotElevate,
	[switch] $Verbose
)

if( $Verbose ) {
	$VerbosePreference="Continue"
}

Write-Verbose "`$PSCommandPath: $PSCommandPath"

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
$json_available = Get-Command "ConvertTo-Json" -errorAction SilentlyContinue -CommandType Cmdlet;

Write-Verbose "`$json_available: $json_available"


##################
# Public API
#
# The functions in this section constitute the public API of mdiag.ps1
# Use these in the script portion below. Please don't directly call other functions; the
#	interfaces there are not guaranteed to be constant between versions of this script.

Function fingerprint {
	_emitdocument "fingerprint" $null @{
		command = $False;
		ok = $True;
		output = @{
			os = "Windows";
			shell = "powershell";
			script = "mdiag";
			version = "1.5.3";
			revdate = "2015-09-29";
		}
	}
}

Function probe( $doc ) {
	# $doc should be: @{ name = "section"; cmd = "invoke-cmd" ; alt = "alternative-invoke-cmd"; }

	if( !( $doc.name ) -or !( $doc.cmd ) ) {
		throw "assert: malformed section descriptor document, must have 'name' and 'cmd' members at least";
	}

	Write-Host "Gathering section [$($doc.name)]"

	# for now, disabling range timestamps until needed by temporally ranging probes (for example, disk statistics over time)
	#$startts = Get-Date
	$cmdobj = _docmd $doc.cmd

	if( !( $cmdobj.ok ) -and ( $null -ne $doc.alt ) ) {
		# preferred cmd failed and we have a fallback, so try that
		Write-Host " | Preference attempt failed, but have a fallback to try..."

		$fbcobj = _docmd $doc.alt

		if( $fbcobj.ok ) {
			Write-Host " | ... which succeeded!"
		}

		$fbcobj.fallback_from = @{
			command = $cmdobj.command;
			error = $cmdobj.error;
		}
		$cmdobj = $fbcobj;
	}

	_emitdocument $doc.name $null $cmdobj

	Write-Host "Finished with section [$($doc.name)]. Closing`n"
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

Function _tojson_date( $v ) {
	"{{ `"`$date`": `"{0}`" }}" -f $( _iso8601_string $v );
}

# following is used to JSON encode object outputs when ConvertTo-JSON (cmdlet) is not available
Function _tojson_value( $indent, $obj ) {
	if( $obj -eq $null ) {
		"null";
	}
	elseif( $indent.Length -gt 4 ) {
		# aborting recursion due to object depth; summarize the current object
		_tojson_string $obj.ToString()
	}
	else {
		switch ( $obj.GetType().Name ) {
			"Hashtable" {
				$ret = $( $obj.GetEnumerator() | ForEach-Object { "{0}`"{1}`": {2}," -f $indent, $_.Key, $( _tojson_value $( $indent + "`t" ) $_.Value ) } | Out-String )
				"{{`n{0}`n{1}}}" -f $ret.Trim("`r`n,"), $indent.Remove( $indent.Length - 1 )
				break
			}
			"Object[]" {
				$ret = $( $obj | ForEach-Object { "{0}{1}," -f $indent, $( _tojson_value $( $indent + "`t" ) $_ ) } | Out-String )
				"[`n{0}`n{1}]" -f $ret.Trim("`r`n,"), $indent.Remove( $indent.Length - 1 )
				break
			}
			"String" {
				_tojson_string $obj
				break
			}
			"Boolean" {
				@('false','true')[$obj -eq $true]
				break
			}
			{ "Int32","UInt32","Int64","UInt64"  -contains $_ } {
				# symbolic or integrals, write plainly
				$obj.ToString()
				break
			}
			"DateTime" {
				_tojson_date $obj
				break
			}
			default {
				if( $obj.GetType().IsClass ) {
					$ret = $( $obj.psobject.properties.GetEnumerator() | ForEach-Object { "{0}`"{1}`": {2}," -f $indent, $_.Name, $( _tojson_value $( $indent + "`t" ) $_.Value ) } | Out-String )
					"{{`n{0}`n{1}}}" -f $ret.Trim("`r`n,"), $indent.Remove( $indent.Length - 1 )
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
	#if( $json_available ) {
	#	return ConvertTo-Json $obj;
	#}
	#else {
		return _tojson_value "`t" $obj;
	#}
}

# _emitdocument (internal)
# re-format a probe document result into an output section document
#
Function _emitdocument( $section, $startts, $cmdobj ) {
	$cmdobj.ref = $JiraTicketNumber;
	$cmdobj.run = $script:rundate;
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

	$script:isfirstdocument = $False

	try {
		Add-Content $diagfile $(_tojson $cmdobj)
	}
	catch {
		$cmdobj.output = ""
		$cmdobj.error = "output conversion to JSON failed"
		$cmdobj.ok = $False

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
	$ok = $True;

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
			$ok = $False
			$ret.error = $error[0].Exception.Message	
		}
	}
	Catch {
		$ok = $False
		$ret.error = $error[0].Exception.Message
	}

	$simpleOk = $?

	if( !$simpleOk ) {
		$ok = $False;
	}

	$ret.ok = $ok

	return $ret
}

###############
# Script-scoped variables
$script:isfirstdocument = $True
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
if( $json_available ) {
	$focsv = " /FO CSV | ConvertFrom-CSV";
}

# not caring anymore
#if( -not $json_available ) {
#	Write-Host -ForegroundColor Red -BackgroundColor Yellow " !!! ";
#	Write-Host -ForegroundColor Red -BackgroundColor Yellow " ConvertTo-Json cmdlet is not available ";
#	Write-Host -ForegroundColor Red -BackgroundColor Yellow " using internal converter instead ";
#	Write-Host -ForegroundColor Red -BackgroundColor Yellow " !!! ";
#}

fingerprint

probe @{ name = "sysinfo";
	cmd = $( "systeminfo{0}" -f $focsv );
}

probe @{ name = "is_admin";
	cmd = "([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')"
}

probe @{ name = "tasklist";
	cmd = "Get-Process | Select Name,Handles,VirtualMemorySize64,WorkingSet64,PagedMemorySize64,NonpagedSystemMemorySize64,PagedSystemMemorySize64,PrivateMemorySize64,Path,Company,CPU,FileVersion,ProductVersion,Description,Product,Id,PriorityClass,TotalProcessorTime,BasePriority,PeakWorkingSet64,PeakVirtualMemorySize64,StartTime,@{Name='Threads';Expression={`$_.Threads.Count}}";
	alt = $( "tasklist{0}" -f $focsv );
}

probe @{ name = "network-adapter";
	cmd = "Get-NetAdapter | Select ifIndex,ifAlias,ifDesc,ifName,DriverVersion,MacAddress,Status,LinkSpeed,MediaType,MediaConnectionState,DriverInformation,DriverFileName,NdisVersion,DeviceName,DriverName,DriverVersionString,MtuSize";
	alt = "netsh wlan show interfaces";
}
probe @{ name = "network-interface";
	cmd = "Get-NetIPAddress | Select ifIndex,PrefixOrigin,SuffixOrigin,Type,AddressFamily,AddressState,Name,ProtocolIFType,IPv4Address,IPv6Address,IPVersionSupport,PrefixLength,SubnetMask,InterfaceAlias,PreferredLifetime,SkipAsSource,ValidLifetime";
	alt = "ipconfig /all";
}
probe @{ name = "network-route";
	cmd = "Get-NetRoute | Select DestinationPrefix,InterfaceAlias,InterfaceIndex,RouteMetric,TypeOfRoute";
	alt = "route print";
}
probe @{ name = "network-dns-cache";
	cmd = "Get-DnsClientCache | Get-Unique | Select Entry,Name,Data,DataLength,Section,Status,TimeToLive,Type";
}
# TODO: this is a bit pants, but Get-NetTCPConnection doesn't have the PID so netstat provides better data
$tcpcmd = "netstat -ano -p TCP";
if( $json_available ) {
	$tcpcmd += " | select -skip 3 | foreach {`$_.Substring(2) -replace `" {2,}`",`",`" } | ConvertFrom-Csv";
}
probe @{ name = "network-tcp-active";
	cmd = $tcpcmd;
}

probe @{ name = "services";
	cmd = "Get-Service | Select D*,Se*,@{Name='Status';Expression={`$_.Status.ToString()}},R* -Exclude ServiceHandle";
}

probe @{ name = "firewall";
	cmd = "Get-NetFirewallRule | Where-Object {`$_.DisplayName -like '*mongo*'} | Select Name,DisplayName,Enabled,@{Name='Profile';Expression={`$_.Profile.ToString()}},@{Name='Direction';Expression={`$_.Direction.ToString()}},@{Name='Action';Expression={`$_.Action.ToString()}},@{Name='PolicyStoreSourceType';Expression={`$_.PolicyStoreSourceType.ToString()}}";
}

probe @{ name = "storage-disk";
	cmd = "Get-Disk | Select PartitionStyle,ProvisioningType,OperationalStatus,HealthStatus,BusType,BootFromDisk,FirmwareVersion,FriendlyName,IsBoot,IsClustered,IsOffline,IsReadOnly,IsSystem,LogicalSectorSize,Manufacturer,Model,Number,NumberOfPartitions,Path,PhysicalSectorSize,SerialNumber,Size";
	alt = "Get-WmiObject Win32_DiskDrive | Select SystemName,BytesPerSector,Caption,CompressionMethod,Description,DeviceID,InterfaceType,Manufacturer,MediaType,Model,Name,Partitions,PNPDeviceID,SCSIBus,SCSILogicalUnit,SCSIPort,SCSITargetId,SectorsPerTrack,SerialNumber,Signature,Size,Status,TotalCylinders,TotalHeads,TotalSectors,TotalTracks,TracksPerCylinder";
}
probe @{ name = "storage-volume";
	cmd = "Get-Partition | Select OperationalStatus,Type,AccessPaths,DiskId,DiskNumber,DriveLetter,GptType,Guid,IsActive,IsBoot,IsHidden,IsOffline,IsReadOnly,IsShadowCopy,IsSystem,MbrType,NoDefaultDriveLetter,Offset,PartitionNumber,Size,TransitionState";
	alt = "Get-WmiObject Win32_LogicalDisk | Select Compressed,Description,DeviceID,DriveType,FileSystem,FreeSpace,MediaType,Name,Size,SystemName,VolumeSerialNumber";
}

probe @{ name = "environment";
	cmd = "Get-Childitem env: | ForEach-Object {`$j=@{}} {`$j.Add(`$_.Name,`$_.Value)} {`$j}";
}

probe @{ name = "user-list-local";
	cmd = "Get-WMIObject Win32_UserAccount | Where-Object {`$_.LocalAccount -eq `$true} | Select Caption,Name,Domain,Description,AccountType,Disabled,Lockout,SID,Status";
}
probe @{ name = "user-current";
	cmd = "[System.Security.Principal.WindowsIdentity]::GetCurrent()";
	alt = "whoami";
}

probe @{ name = "drivers";
	cmd = "Get-WmiObject -Class Win32_SystemDriver | Where-Object -FilterScript {`$_.State -eq 'Running'} | Select Name,Status,Description";
}

probe @{ name = "time-change";
	cmd = "Get-EventLog -LogName System -Source @('Microsoft-Windows-Kernel-General','Microsoft-Windows-Time-Service') | Select -first 10";
}

###############
# Final
# complete the JSON array, making the whole document a valid JSON value
#
Add-Content $diagfile "]`n"

Write-Host "Finished. Please attach '$diagfile' to the support case $JiraTicketNumber."

Write-Host "Press any key to continue ..."
$x = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
