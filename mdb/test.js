// bindata
bd = ""
for (var i=0; i<10000; i++)
    bd += (i%10)
bd = new BinData(0, bd)

// a doc
doc = {
    number: 1.7,
    hello: 'world',
    empty: { },
    'false': false,
    array: [
        bd,
        undefined,
        true,
        {
            nada: null,
        },
        /^hello world$/
            
    ],
    date: new Date(0)
}


// small collection
c = db.small
for (var i=0; i<10; i++)
    c.insert(doc)

// big collection
c = db.big
for (var i=0; i<5000; i++)
    c.insert(doc)

printjson(db.getLastError())
