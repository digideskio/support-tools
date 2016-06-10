#!/bin/bash

cat "$@" \
	| sed \
		-e 's/^ *//' \
		-e 's/^r /#date-time &/' \
		-e 's/^\(.*\) ---timestamp---$/#date-time \1/' \
		-e 's/procs/procs procs/' \
		-e 's/-----------memory----------/mem mem mem mem/' \
		-e 's/---swap--/swp swp/' \
		-e 's/-----io----/io io/' \
		-e 's/--system--/syst syst/' \
		-e 's/-----cpu------/cpu cpu cpu cpu cpu/' \
	| awk \
		'
		{
			if (!/^#/) {
				$(NF-2) = $(NF-2) "-" $(NF-1);
				$(NF-1) = "";
				$NF = "";
				for (i = NF - 2; i <= NF; i++) {
					printf("%s ", $i);
				}
				for (i = 1; i <= NF - 3; i++) {
					printf("%s%s", $i, (i==NF - 3)?"\n":" ");
				}
			} else {
				print;
			}
		}
		' \
	| awk \
		'
		/^#/ && prev !~ /^#/ {
			for (i = 1; i <= NF; i++) {
				printf("%s(%d)%s", (i==1)?"#":"", i, (i==NF)?"\n":" ");
			}
		}
		{
			print;
			prev = $0;
		}
		' \
	| column -t

