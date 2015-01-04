function repro() {

    var every = 10000
    var duration = 120
    
    db.c.drop();
    db.c.ensureIndex({ttl: 1}, {expireAfterSeconds: 30});
    
    t0 = new Date()
    var i = 0;
    while (new Date() - t0 < duration*1000) {
        var bulk = db.c.initializeUnorderedBulkOp();
        for (var j=0; j<every; i++, j++)
            bulk.insert({ttl: new Date()})
        bulk.execute();
        print(i)
    }
}
