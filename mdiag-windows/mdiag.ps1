###################
# mdiag.ps1 - Windows Diagnostic Script for MongoDB

param(
	[Parameter(Mandatory=$true)]
	[string] $jira_ticket_number
)

$diagfile = Join-Path @([Environment]::GetFolderPath('Personal')) $("mdiag-" + $(hostname) + ".txt")

##################
# Public API
#
# The functions in this section constitute the public API of mdiag.ps1
# Use these in the script portion below. Please don't directly call other functions; the
#	interfaces there are not guaranteed to be constant between versions of this script.

Function fingerprint {
	_emitdocument "fingerprint" $(_jsondate) @{
		command = $False;
		ok = $True;
		output = @{
			os = "Windows";
			shell = "powershell";
			script = "mdiag";
			version = "1.3";
			revdate = "2014-11-27";
		}
	}
}

Function probe( $doc ) {
	# $doc should be: @{ name = "section"; cmd = "invoke-cmd" ; alt = "alternative-invoke-cmd"; }

	if( !( $doc.name ) -or !( $doc.cmd ) ) {
		throw "assert: malformed section descriptor document, must have 'name' and 'cmd' members at least";
	}

	echo "Gathering section [$($doc.name)]"

	$startts = _jsondate # { $date: ISO-8601 }
	$cmdobj = _docmd $doc.cmd

	if( !( $cmdobj.ok ) -and ( $null -ne $doc.alt ) ) {
		# preferred cmd failed and we have a fallback, so try that
		echo " | Preference attempt failed, but have a fallback to try..."

		$fbcobj = _docmd $doc.alt

		if( $fbcobj.ok ) {
			echo " | ... which succeeded, bananarama!"
		}

		$fbcobj.fallback_from = @{
			command = $cmdobj.command;
			error = $cmdobj.error;
		}
		$cmdobj = $fbcobj;
	}

	_emitdocument $doc.name $startts $cmdobj

	echo "Finished with section [$($doc.name)]. Closing`n"
}

###############
# Generic internal functions
#
# Please don't call these in the script portion of the code. The API here will never freeze.


Function _emitdocument( $section, $startts, $cmdobj ) {

	$cmdobj.ref = $jira_ticket_number;
	$cmdobj.run = $script:rundate;
	$cmdobj.section = $section;
	$cmdobj.ts = @{
		start = $startts;
		end = _jsondate;
	};

	# make an array of  documents
	if( !( $isfirstdocument ) ) {
		Add-Content $diagfile ","
	}

	$script:isfirstdocument = $False
	
	try {
		Add-Content $diagfile $(ConvertTo-Json $cmdobj)
	}
	catch {
		$cmdobj.output = ""
		$cmdobj.error = "output conversion to JSON failed"
		$cmdobj.ok = $False

		# give it another shot without the output, just let it die if it still has an issue
		Add-Content $diagfile $(ConvertTo-Json $cmdobj)
	}
}

Function _jsondate {
	# ISO-8601
	return @{ "`$date" = Get-Date -Format s; }
	# Unix time
	#return @{ "`$date" = [int64]( New-TimeSpan -Start @(Get-Date -Date "01/01/1970") -End (Get-Date).ToUniversalTime() ).TotalSeconds; }
}

Function _docmd {
	# Allow for conceptual differences between Unix and Windows here.
	#Write-Error "Passed arguments [$args]`n" # Reenable this for debugging if you need

	# selecting only the first arg in the stream now due to possible mongoimport killers like ' " etc (which come out as \u00XX
	$ret = @{ command = ("$args").Split("|")[0].Trim() }
	$text = ""
	$ok = $True;

	Try {
		#echo "Trying to run command [$args]`n"
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
$script:rundate = _jsondate

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

fingerprint

probe @{ name = "sysinfo";
	cmd = "systeminfo /FO CSV | ConvertFrom-Csv";
}

probe @{ name = "is_admin";
	cmd = "([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')"
}

probe @{ name = "tasklist";
	cmd = "Get-Process | Select Name,Handles,VM,WS,PM,NPM,Path,Company,CPU,FileVersion,ProductVersion,Description,Product,Id,PriorityClass,TotalProcessorTime,BasePriority,PeakWorkingSet64,PeakVirtualMemorySize64,StartTime,@{Name='Threads';Expression={`$_.Threads.Count}}";
	alt = "tasklist /FO CSV | ConvertFrom-Csv"
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

probe @{ name = "services";
	cmd = "Get-Service | Where-Object {`$_.ServiceName -like '*Mongo*'}";
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
	cmd = "Get-Childitem env: | Select Key,Value";
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

echo "Finished. Please attach '$diagfile' to the support case $jira_ticket_number."

echo "Press any key to continue ..."
$x = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
