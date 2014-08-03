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
	# DEFENSIVE: Make sure $thissection is not defined, or return an error
	$thissection = $sname
	echo "Gathering section $section"
	# TODO: Setup data structures for this section. Maybe output beginning of the JSON paragraph
	}

Function endsection
	{
	echo "Finished with section $thissection. Closing`n"
	# TODO: undefine $thissection
	# TODO: Clean (flush?) data structures for this section. Maybe output end of JSON paragraph
	}

Function subsection($ssname)
	{
	# DEFENSIVE: Make sure $subsection is not defined, or return an error
	$subsection = $ssname
	echo "Gathering subsection $ssname"
	# TODO: Setup data structures for this section. Maybe output beginning of the JSON subparagraph
	}

Function endsubsection
	{
	echo "Finished with subsection $subsection. Closing`n"
	# TODO: undefine $subsection
	# TODO: Clean (flush?) data structures for this section. Maybe output end of JSON subparagraph
	}

Function runcommand
	{
	}
Function getfiles
	{
	}
###############
# Generic internal functions
#
# Please don't call these in the script portion of the code. The API here will never freeze.

Function _in_section
	{
	}
Function _in_subsection
	{
	}
Function _docmd
	{
	# TODO: Detect if Invoke-Expression succeeded, parse return code.
	$ret = ""
	$ret += $(Invoke-Expression($args))
	return $ret # If we want to change this to a list, prepend with a , to force list context
	}
Function _file_exists($filename)
	{

	}
Function _statfile($filename)
	{

	}
Function _readfile($filename)
	{

	}
###############
# JSON functions
#
# Please don't call these in the script portion of the code. The API here will never freeze.


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
	getfiles /etc/*release*
endsection

# Keeping this around as syntax reminder
#Function msection
#	$section, $cmd = $args
#	echo "Gathering $section info... "
#	$retval = "`n`n=========== start section $section ===========`n"
#	$retval = $($retval + $(Invoke-Expression($cmd)) + "`n")
#	$retval = $($retval + "============ end section $section ============`n")
#	Add-Content $diagfile $retval
#	echo "done"
#	}
#
#msection Time date
