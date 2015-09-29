function create() {
    db.c.ensureIndex({i:1})
    for (var i=0; i<5; i++)
        db.c.insert({_id:i, i:i})
}

function check() {
    printjson(db.c.find().hint({$natural:1}).toArray())
    printjson(db.c.find().hint({i:1}).toArray())
}


