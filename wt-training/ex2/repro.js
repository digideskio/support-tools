function repro() {

    db.c.drop()
    db.c.insert({_id:0, i:0})
 
    count = 1500000
    every = 10000
    for (var i=0; i<count; ) {
        var bulk = db.c.initializeOrderedBulkOp();
        for (var j=0; j<every; j++, i++)
            bulk.find({_id:0}).updateOne({_id:0, i:i})
        bulk.execute();
        print(i)
    }
}
