###################
# mdiag.ps1 - Windows Diagnostic Script for MongoDB

param(
[string] $ticket
)

$diagfile = $("mdiag-" + $(hostname) + ".txt")

##################
# Public API
#
# The functions in this section constitute the public API of mdiag.ps1
# Use these in the script portion below. Please don't directly call other functions; the
#	interfaces there are not guaranteed to be constant between versions of this script.

Function section($sname) {
	if( _in_section ) {
		throw "Internal error: starting new section [$sname] when already in section [$thissection]";
	}

	$script:thissection = $sname
	echo "Gathering section [$script:thissection]"

	# make an array of section documents
	if( !( $isfirstsection ) ) {
		Add-Content $diagfile ","
	}

	$script:isfirstsection = $False
}

Function endsection {
	echo "Finished with section [$thissection]. Closing`n"
	$script:thissection = $Null # Only real way to clear this; Remove-Variable didn't work right
}

Function subsection($ssname) {
	if( _in_subsection ) {
		throw "Internal error: starting new subsection [$ssname] when already in subsection [$subsection]";
	}

	$script:subsection = $ssname
	echo "Gathering subsection [$script:subsection]"
}

Function endsubsection {
	echo "Finished with subsection [$subsection]. Closing`n"
	$script:subsection = $Null
}

Function runcommand {
	if( !( _in_section ) ) {
		throw "Internal error: Trying to run a command while not in a section";
	}

	$startts = _jsondate # { $date: seconds-since-epoch }
	$cmdobj = _docmd "$args" # Quotes stringify the object

	$cmdobj.ts = @{
		start = $startts;
		end = _jsondate
	}

	$cmdobj.ref = $ticket;
	$cmdobj.run = $script:rundate
	$cmdobj.section = $thissection

	if( _in_subsection ) {
		$cmdobj.subsection = $subsection
	}

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

Function runjsoncommand {
	if( !( _in_section ) ) {
		throw "Internal error: Trying to run a jsoncommand while not in a section";
	}

	$objout = _dojsoncmd "$args" # Quotes stringify the object
	$objout.ref = $ticket
	$objout.run = $script:rundate
	$objout.section = $thissection

	if( _in_subsection ) {
		$objout.subsection = $subsection
	}

	Add-Content $diagfile $(ConvertTo-Json $objout)
}

Function getfiles {
	if( !( _in_section ) ) {
		throw "Internal error: Trying to run getfiles while not in a section";
	}

	foreach( $filename in $args ) {
		$fileobj = _dofile "$filename"
		$fileobj.ref = $ticket
		$fileobj.run = $script:rundate
		$fileobj.section = $thissection
		if( _in_subsection ) {
			$fileobj.subsection = $subsection
		}

		Add-Content $diagfile $(ConvertTo-Json $fileobj)
	}
}

###############
# Generic internal functions
#
# Please don't call these in the script portion of the code. The API here will never freeze.

Function _in_section {
	if( $thissection -ne $Null ) {
		return 1;
	}
	return 0;
}

Function _in_subsection {
	if( $subsection -ne $Null ) {
		return 1;
	}
	return 0;
}

Function _jsondate {
	# ISO-8601
	return @{ "`$date" = Get-Date -Format s; }
	# Unix time
	#return @{ "`$date" = [int64]( New-TimeSpan -Start @(Get-Date -Date "01/01/1970") -End (Get-Date).ToUniversalTime() ).TotalSeconds; }
}

Function _dofile($fn) {
	if(_file_exists $fn) {
		$fobj = Get-ChildItem $fn
		return @{ 
			filename = $((Resolve-Path $fn).toString());
			exists = $True; # Needed to get boolean value
			ls = $((ls -l $fn).toString() );
			ctime = $fobj.CreationTimeUTC;
			atime = $fobj.LastAccessTimeUTC;
			mtime = $fobj.LastWriteTimeUTC;
			size = $fobj.Length;
			# There are other things we could add to this if we liked.
			output = $(_readfile $fn);
		}
	}

	return @{
		filename = "$fn"; # Note this will not expand any wildcards or paths
		exists = $False; # Needed to get boolean value
	}
}

Function _docmd {
	# Allow for conceptual differences between Unix and Windows here.
	#Write-Error "Passed arguments [$args]`n" # Reenable this for debugging if you need

	$ret = @{ command = "$args" }
	$text = ""
	$ok = $True;

	Try {
		#echo "Trying to run command [$args]`n"
		$ret.output = Invoke-Expression "$args" -ErrorAction Stop
		#Write-Host $text
	}
	Catch {
		$ok = $False
		$ret.error = "command execution failed"
	}

	$simpleOk = $?

	if( !$simpleOk ) {
		$ok = $False;
	}

	$ret.ok = $ok

	return $ret
}

Function _dojsoncmd {
	# This runs a statement that returns JSON, being careful not to stringify it!
	$ok = $True
	
	Try { # The redirect here is a special hack for systeminfo which is chatty.
		$val = Invoke-Expression "$args" 2>$null 3>$null
	}
	Catch {
		#$val = @{ output = "Error" } <- why was this here? it was never used
		$ok = $False
	}

	$ret = @{
		command = "$args";
		ok = $ok;
	}

	if( $ok ) {
		$ret.JSONOutput = $True
		$ret.JSONValue = $val
	}

	return $ret
}

###############
# File I/O operations (internal only)

Function _file_exists($filename) {
	if( Test-Path $filename ) {
		return 1;
	}
	return 0;
}

Function _readfile($filename) {
	$ret = Get-Content $filename | ForEach-Object {$_.toString()} # From Object list to list of strings
	return $ret;
}

###############
# Script-scoped variables
$script:isfirstsection = $True
$script:thissection = $Null
$script:subsection  = $Null
$script:rundate = _jsondate

Set-Content $diagfile "["

###############
# Script portion
#
# This is where you you define the tests you want to run, using the functions in the public API
# section above. 

#
#section stuff
#	runcommand date
#	runcommand uname -a
#	runcommand stuff
#endsection
#
#section stuff2
#	runcommand date +%s
#endsection
#
#section stuff3
#	subsection bit1
#		runcommand date
#	endsubsection
#	subsection bit2
#		runcommand uname -a
#	endsubsection
#	subsection bit3
#		runjsoncommand "systeminfo /fo csv | ConvertFrom-Csv"
#	endsubsection
#endsection
#
#section stuff4
#	getfiles sample.txt
#	getfiles /etc/*release*
#endsection
##>

section sysinfo
$cmd = "systeminfo /FO CSV | ConvertFrom-Csv"
runcommand $cmd
endsection

section tasklist
$cmd = "Get-Process | Select __NounName,Name,Handles,VM,WS,PM,NPM,Path,Company,CPU,FileVersion,ProductVersion,Description,Product,Id,PriorityClass,TotalProcessorTime,BasePriority,PeakWorkingSet64,PeakVirtualMemorySize64,StartTime,@{Name=`"Threads`";Expression={`$_.Threads.Count}}"
runcommand $cmd
endsection

section network
$cmd = "Get-NetAdapter | Select ifIndex,ifAlias,ifDesc,ifName,DriverVersion,MacAddress,Status,LinkSpeed,MediaType,MediaConnectionState,DriverInformation,DriverFileName,NdisVersion,DeviceName,DriverName,DriverVersionString,MtuSize"
runcommand $cmd
$cmd = "Get-NetIPAddress | Select ifIndex,PrefixOrigin,SuffixOrigin,Type,AddressFamily,AddressState,Name,ProtocolIFType,IPv4Address,IPv6Address,IPVersionSupport,PrefixLength,SubnetMask,InterfaceAlias,PreferredLifetime,SkipAsSource,ValidLifetime"
runcommand $cmd
endsection

section services
$cmd = "Get-Service | Where-Object {`$_.ServiceName -like `"*Mongo*`"}"
runcommand $cmd
$cmd = "Get-NetFirewallRule | Where-Object {`$_.DisplayName -like '*mongo*'} | Select Name,DisplayName,Enabled,@{Name='Profile';Expression={`$_.Profile.ToString()}},@{Name='Direction';Expression={`$_.Direction.ToString()}},@{Name='Action';Expression={`$_.Action.ToString()}},@{Name='PolicyStoreSourceType';Expression={`$_.PolicyStoreSourceType.ToString()}}"
runcommand $cmd
endsection


###############
# Final
# complete the JSON array, making the whole document a valid JSON value
#
Add-Content $diagfile "]`n"
