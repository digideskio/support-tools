import json
import sys

for line in sys.stdin:
    line = json.loads(line)
    print json.dumps(line['serverStatus'])

    
