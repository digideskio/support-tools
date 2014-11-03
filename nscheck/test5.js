function g(name, inxes, drop) {
    c = db[name]
    for (i=0; i<inxes; i++) {
        inx = {}
        inx['x'+i] = 1
        c.ensureIndex(inx)
    }
    c.insert({})
    if (drop)
        c.drop()
}

function generate() {
    g('c1', 0, false)
    g('c2', 3, false)
    g('c3', 10, false)
    g('d1', 0, true)
    g('d2', 3, true)
    g('d3', 10, true)
}

generate()
