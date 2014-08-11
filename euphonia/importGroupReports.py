import csv
import pymongo
import sys

from datetime import datetime
from groupreport import GroupReport
from pprint import pprint


def usage():
    print("usage: "+sys.argv[0]+" mms_group_report.csv [TAG]")
    sys.exit(1)

# Get CSV file from command line
if len(sys.argv) < 2 or len(sys.argv) > 3:
    usage()
elif len(sys.argv) == 3:
    tag = sys.argv[2]
else:
    # If tag not specified use filename sans path
    starti = sys.argv[1].rfind("/")
    tag = sys.argv[1][starti+1:]

conn = pymongo.MongoClient()
db = conn.euphonia
coll_mmsgroupreports = db.mmsgroupreports

csvfile = open(sys.argv[1])
cvsdict = csv.DictReader(csvfile)

for group in cvsdict:
    for key in group.keys():
        if not key:
            group.pop(key)
            continue
        if key not in GroupReport.fields:
            print "Error: '" + key + "' not a recognized field"
            sys.exit(1)

        val = group[key]

        # Normalize values
        try:
            tmp = float(val)
            val = tmp
            if val.is_integer():
                tmp = int(val)
                if tmp.bit_length() <= 64:
                    val = tmp
                else:
                    val = -1
        except:
            if val == "":
                val = None
            elif val == "True":
                val = True
            elif val == "False":
                val = False

        group[key] = val

        if key == "LastActiveAgentTime":
            try:
                lastActiveAgentTime = datetime.strptime(val,
                                                        "%Y-%m-%d %H:%M:%S.%f")
            except:
                lastActiveAgentTime = None
            group[key] = lastActiveAgentTime

        if key == "LastPageView":
            try:
                lastPageView = datetime.strptime(val, "%Y-%m-%d")
            except:
                lastPageView = None
            group[key] = lastPageView

    group["tag"] = tag

    try:
        coll_mmsgroupreports.insert(group)
    except Exception as e:
        print "Error: ", e
        pprint(group)
