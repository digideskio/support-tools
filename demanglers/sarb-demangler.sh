#!/bin/bash

cat "$@" \
	| awk '
		NR == 1 {
			split($4, datebits, "/");
			D = datebits[2];
			M = datebits[1];  # ARGH. Also, is this locale dependent?
			Y = datebits[3];
			date = sprintf("%s-%s-%s", Y, M, D);
		}

		NR == 2 {
		}

		NR == 3 {
			final = NF;
			for (i = 1; i <= final; i++) {
				printf("%s(%d)%s", (i==1)?"#":"", i, (i==final)?"\n":" ");
			}
			$1 = "#date-time";
			$2 = "";
			print;
		}

		NR > 3 {
			split($1, timebits, ":");
			h = timebits[1];
			if ($2 == "PM" && h < 12) {
				h += 12;
			}
			if ($2 == "AM" && h == 12) {
				h = "00";
			}
			m = timebits[2];
			s = timebits[3];

			# HACK ALERT
			# FIXME: increment the date properly
			if (h == "00" && m == "00" && s == "00") {
				D = sprintf("%02d", D+1);
			}

			$1 = sprintf("%s-%s-%s-%s:%s:%s", Y, M, D, h, m, s);
			$2 = "";

			print;
		}
		' \
	| column -t

