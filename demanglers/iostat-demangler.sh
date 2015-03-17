#!/bin/bash

remove_pattern="$1"
shift

cat "$@" \
	| grep -v "$remove_pattern" \
	| awk '
		NR == 1 {
			date = $4;
			dayadj = 0;
		}

		NR > 2 {
			num_devices = 0;
			if ($1 == "Time:") {
				$1 = date;
				if ($2 == "12:00:00" && $3 == "AM") {
					# ARGH. Woeful.
					dayadj++;
				}
			}
			split($1, datebits, "/");
			D = datebits[2] + dayadj;
			M = datebits[1];  # ARGH. Also, is this locale dependent?
			Y = datebits[3];
			split($2, timebits, ":");
			h = timebits[1];
			if ($3 == "PM" && h < 12) {
				h += 12;
			}
			if ($3 == "AM" && h == 12) {
				h = "00";
			}
			m = timebits[2];
			s = timebits[3];
			getline;
			cpu_heading = gensub("avg-cpu: *", "", "", $0);
			getline;
			cpu_values = $0;
			getline;
			getline;
			device_heading = gensub("Device: *", "", "", $0);
			getline;
			while (NF > 0) {
				device_name[num_devices] = $1;
				num_devices++;
				device_values[$1] = gensub("^[a-z0-9]* *", "", "", $0);
				getline;
			}
			if (lines == 30) {
				lines = 0;
			}
			if (lines == 0) {
				num_cpu_headings = split(cpu_heading, dummy);
				num_device_headings = split(device_heading, dummy);
				final = 1 + num_cpu_headings + num_devices * num_device_headings;
				for (i = 1; i <= final; i++) {
					printf("%s(%d)%s", (i==1)?"#":"", i, (i==final)?"\n":" ");
				}
				printf("#date-time ");
				for (j = 0; j < num_cpu_headings; j++) {
					printf("avg ");
				}
				for (i = 0; i < num_devices; i++) {
					for (j = 0; j < num_device_headings; j++) {
						printf("%s ", device_name[i]);
					}
				}
				printf("\n");
				printf("#date-time %s ", cpu_heading);
				final = num_devices;
				for (i = 1; i <= final; i++) {
					printf("%s%s", device_heading, (i==final)?"\n":" ");
				}
			}
			printf("%s-%s-%s-%s:%s:%s  %s ", Y, M, D, h, m, s, cpu_values);
			for (i = 0; i < num_devices; i++) {
				printf("%s%s", device_values[device_name[i]], (i==num_devices-1)?"\n":" ");
			}
			lines++;
		}
		' \
	| column -t

