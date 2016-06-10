function repro(thread) {

    var seed = thread + 1;
    function randomString(len) {
        var rv = '';
        while (len > 0) {
            var x = Math.sin(seed++) * 10000;
            rv += (x - Math.floor(x));
            len -= 20;
        }
        return rv;
    }
    
    count = 500000
    every = 10000
    for (var i=0; i<count; ) {
        var bulk = db.c.initializeUnorderedBulkOp();
        for (var j=0; j<every; j++, i++)
            bulk.insert({'_id': randomString(100), 'payload': randomString(1000)});
        try {
            bulk.execute();
            print(i)
        } catch (e) {}
    }
}
