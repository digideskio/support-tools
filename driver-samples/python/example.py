from pymongo import MongoClient

# before running, make sure a mongod is running locally on port 27017
# run with: "python example.py"

# create MongoClient object
mc = MongoClient("localhost:27017")

# pick database
database = mc['test']

# pick collection and drop it
collection = database['mycollection']
collection.drop()

# insert a sample document
_id = collection.insert({'foo': 'bar', 'number': 5})

# find the document again and print it
print collection.find_one({'_id': _id})

# number of docs
print "collection has %i document(s)." % collection.count()