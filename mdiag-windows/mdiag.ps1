###################
# mdiag.ps1 - Windows Diagnostic Script for MongoDB
# Author: "Pat Gunn" <pgunn@mongodb.com>
# Copyright MongoDB 2014. All rights reserved.
$diagfile = $("mdiag-" + $(hostname) + ".txt")

Function msection
	{
	$section, $cmd = $args
	echo "Gathering $section info... "
	$retval = "`n`n=========== start section $section ===========`n"
	$retval = $($retval + $(Invoke-Expression($cmd)) + "`n")
	$retval = $($retval + "============ end section $section ============`n")
	Add-Content $diagfile $retval
	echo "done"
	}

msection Time date
