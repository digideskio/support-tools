###################
# mdiag.ps1 - Windows Diagnostic Script for MongoDB


$diagfile = $("mdiag-" + $(hostname) + ".txt")
##################
# Public API
#
# The functions in this section constitute the public API of mdiag.ps1
# Use these in the script portion below. Please don't directly call other functions; the
#	interfaces there are not guaranteed to be constant between versions of this script.

Function section($sname)
	{
	if(_in_section) {throw "Internal error: starting new section [$sname] when already in section [$thissection]";}
	$script:thissection = $sname
	echo "Gathering section [$script:thissection]"
	}

Function endsection
	{
	echo "Finished with section [$thissection]. Closing`n"
	$script:thissection = $Null # Only real way to clear this; Remove-Variable didn't work right
	}

Function subsection($ssname)
	{
	if(_in_subsection) {throw "Internal error: starting new subsection [$ssname] when already in subsection [$subsection]";}
	$script:subsection = $ssname
	echo "Gathering subsection [$script:subsection]"
	}

Function endsubsection
	{
	echo "Finished with subsection [$subsection]. Closing`n"
	$script:subsection = $Null
	}

Function runcommand
	{
	if(! (_in_section) ) {throw "Internal error: Trying to run a command while not in a section";}
	$cmdobj = _docmd "$args" # Quotes stringify the object
	Add-Member -InputObject $cmdobj NoteProperty section $thissection
	if(_in_subsection)
		{
		Add-Member -InputObject $cmdobj NoteProperty subsection $subsection
		}

	Add-Content $diagfile $(ConvertTo-Json $cmdobj)
	}

Function runjsoncommand
	{
	if(! (_in_section)) {throw "Internal error: Trying to run a jsoncommand while not in a section";}
	$objout = _dojsoncmd "$args" # Quotes stringify the object
	Add-Member -InputObject $objout NoteProperty section $thissection
	if(_in_subsection)
		{
		Add-Member -InputObject $objout NoteProperty subsection $subsection
		}
	Add-Content $diagfile $(ConvertTo-Json $objout)
	}

Function getfiles
	{
	if(! (_in_section)) {throw "Internal error: Trying to run getfiles while not in a section";}
	foreach ($filename in $args)
		{
		$fileobj = _dofile "$filename"
		Add-Member -InputObject $fileobj NoteProperty section $thissection
		if(_in_subsection)
			{
			Add-Member -InputObject $fileobj NoteProperty subsection $subsection
			}
		Add-Content $diagfile $(ConvertTo-Json $fileobj)
		}
	}

###############
# Generic internal functions
#
# Please don't call these in the script portion of the code. The API here will never freeze.

Function _in_section
	{
	if($thissection -ne $Null) {return 1;}
	return 0;
	}

Function _in_subsection
	{
	if($subsection -ne $Null) {return 1;}
	return 0;
	}

Function _dofile($fn)
	{
	$ret = New-Object PSObject

	if(_file_exists $fn)
		{
		$fobj = Get-ChildItem $fn
		Add-Member -InputObject $ret NoteProperty filename $((Resolve-Path $fn).toString())
		Add-Member -InputObject $ret NoteProperty exists $True # Needed to get boolean value
		Add-Member -InputObject $ret NoteProperty ls $((ls -l $fn).toString() )
		Add-Member -InputObject $ret NoteProperty ctime $fobj.CreationTimeUTC
		Add-Member -InputObject $ret NoteProperty atime $fobj.LastAccessTimeUTC
		Add-Member -InputObject $ret NoteProperty mtime $fobj.LastWriteTimeUTC
		Add-Member -InputObject $ret NoteProperty size $fobj.Length
			# There are other things we could add to this if we liked.
		Add-Member -InputObject $ret NoteProperty output $(_readfile $fn)
		}
	else
		{
		Add-Member -InputObject $ret NoteProperty filename "$fn" # Note this will not expand any wildcards or paths
		Add-Member -InputObject $ret NoteProperty exists $False # Needed to get boolean value
		}
	return $ret
	}

Function _docmd
	{
	# Allow for conceptual differences between Unix and Windows here.
	#Write-Error "Passed arguments [$args]`n" # Reenable this for debugging if you need
	$ret = New-Object PSObject
	$ts = @{}

	Add-Member -InputObject $ret NoteProperty command "$args"
	$retString = ""
	$text = ""
	$ok = 1;
#	$ts['start'] = $(Invoke-Expression date).toString() # This just gave a human string in the output.
	$ts['start'] = Get-Date # This gives a structured object including a JSON-friendly string.

	Try 	{
		#echo "Trying to run command [$args]`n"
		$text = $(Invoke-Expression "$args -ErrorAction Stop")
		}
	Catch	{$ok = 0}
	$simpleOk = $?

	$ts['end'] = Get-Date
	if(! $simpleOk)
		{$ok = 0;}

	Add-Member -InputObject $ret NoteProperty ts $ts
	Add-Member -InputObject $ret NoteProperty ok $ok
	Add-Member -InputObject $ret NoteProperty retcode $retCode # Won't get a meaningful value if cmd did not launch

	if($ok)
		{
		Add-Member -InputObject $ret NoteProperty output "$text"
		}
	return $ret
	}

Function _dojsoncmd
	{
	# This runs a statement that returns JSON, being careful not to stringify it!
	$ret = New-Object PSObject
	$ok = $True
	Try 	{ # The redirect here is a special hack for systeminfo which is chatty.
		$val = Invoke-Expression "$args" 2>$null 3>$null
		}
	Catch	{
		$val = New-Object PSObject
		Add-Member -InputObject $val NoteProperty output "Error"
		$ok = $False
		}
	Add-Member -InputObject $ret NoteProperty command "$args"
	Add-Member -InputObject $ret NoteProperty ok $ok
	if($ok)
		{
		Add-Member -InputObject $ret NoteProperty JSONOutput $True
		Add-Member -InputObject $ret NoteProperty JSONValue $val
		}
	return $ret
	}

###############
# File I/O operations (internal only)

Function _file_exists($filename)
	{
	if(Test-Path $filename) {return 1;}
	return 0;
	}

Function _readfile($filename)
	{
	$ret = Get-Content $filename | ForEach-Object {$_.toString()} # From Object list to list of strings
	return $ret;
	}

###############
# Script-scoped variables
$script:thissection = $Null
$script:subsection  = $Null

###############
# Script portion
#
# This is where you you define the tests you want to run, using the functions in the public API
# section above. 


section stuff
	runcommand date
	runcommand uname -a
	runcommand stuff
endsection

section stuff2
	runcommand date +%s
endsection

section stuff3
	subsection bit1
		runcommand date
	endsubsection
	subsection bit2
		runcommand uname -a
	endsubsection
	subsection bit3
		runjsoncommand "systeminfo /fo csv | ConvertFrom-Csv"
	endsubsection
endsection

section stuff4
	getfiles sample.txt
	getfiles /etc/*release*
endsection
