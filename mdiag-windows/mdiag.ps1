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
	# TODO: Setup data structures for this section. Maybe output beginning of the JSON paragraph
	}

Function endsection
	{
	echo "Finished with section [$thissection]. Closing`n"
	$script:thissection = $Null # Only real way to clear this; Remove-Variable didn't work right
	# TODO: Clean (flush?) data structures for this section. Maybe output end of JSON paragraph
	}

Function subsection($ssname)
	{
	if(_in_subsection) {throw "Internal error: starting new subsection [$ssname] when already in subsection [$subsection]";}
	$script:subsection = $ssname
	echo "Gathering subsection [$script:subsection]"
	# TODO: Setup data structures for this section. Maybe output beginning of the JSON subparagraph
	}

Function endsubsection
	{
	echo "Finished with subsection [$subsection]. Closing`n"
	$script:subsection = $Null
	# TODO: Clean (flush?) data structures for this section. Maybe output end of JSON subparagraph
	}

Function runcommand
	{
	$ok, $txt = _docmd "$args" # Quotes stringify the object
	if($ok)
		{
		echo "Result of [$args]: $txt`n"
		}
	else	{
		echo "Result of [$args]: COMMAND FAILED`n"
		}
	}
Function getfiles
	{
	foreach ($filename in $args)
		{
		if(_file_exists $filename)
			{
			$contents 	= _readfile $filename
			$stat		= _statfile $filename
			echo $("File [$filename]: First 2 lines:`n" + $contents[0] + "`n" + $contents[1] + "`n")
			echo $("File has mode " + $stat[0] + "`n`n")
			}
		else
			{
			echo "File [$filename]: Does not exist`n"
			}
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
Function _docmd
	{
	#Write-Error "Passed arguments [$args]`n"
	$ret = ""
	$text = ""
	$ok = 1;
	Try 	{
		$text = $(Invoke-Expression "$args -ErrorAction Stop")
		}
	Catch	{$ok = 0}
	if($ok) {$ret = $text}
	return $ok,$ret
	}
Function _file_exists($filename)
	{
	if(Test-Path $filename) {return 1;}
	return 0;
	}
Function _statfile($filename)
	{
	# Not sure what the best way to emulate this is.
	# There is a family of methods that exist as follows:
	# (Get-ChildItem $filename).methodname
	# If I can't find a better way to get at this kind of info, I'll build a suitable list that way
	$fo = Get-ChildItem $filename
	return $fo.Mode,$fo.IsReadOnly,$fo.CreationTimeUTC,$fo.LastAccessTimeUTC,$fo.LastWriteTimeUTC,$fo.Length
	}
Function _readfile($filename)
	{
	return(Get-Content $filename);
	}
###############
# JSON functions
#
# Please don't call these in the script portion of the code. The API here will never freeze.

# TODO - actually figure out the right abstraction for this.

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
		runcommand stuff
	endsubsection
endsection

section stuff4
	getfiles mdiag.ps1
	getfiles /etc/*release*
endsection
