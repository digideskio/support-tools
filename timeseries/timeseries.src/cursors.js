function event_x(e) {
    var evt = window.event
    return (evt.pageX - e.offsetLeft - e.offsetParent.offsetLeft) / e.offsetWidth
}

var svg_ns = "http://www.w3.org/2000/svg"

function set_attrs(e, attrs) {
    for (a in attrs)
        e.setAttribute(a, attrs[a])
}

function elt(ns, name, attrs) {
    var e = document.createElementNS(ns, name)
    set_attrs(e, attrs)
    return e
}

function del_id(id) {
    var e = document.getElementById(id)
}

function move(e) {
    var x = event_x(e)
    set_attrs(document.getElementById('lll'), {x1:x, x2:x})
}

function out(e) {
    set_attrs(document.getElementById('lll'), {x1:-1, x2:-1})
}

var width = %d;

function add(e) {
    var x = event_x(e)
    var cursor = elt(svg_ns, "line",
                     {x1:x, x2:x, y1:0, y2:1, class:"cursor"})
    var deleter = elt(svg_ns, "circle",
                      {cx:(x*100)+'%%', cy:'50%%', r:0.3, class:"deleter", onclick:"del(this)"})
    var letter = elt(svg_ns, "text",
                     {x:(x*100)+'%%', y:'80%%', 'text-anchor':'middle', 'class':'letter'})
    document.getElementById("cursors").appendChild(cursor)
    document.getElementById("deleters").appendChild(deleter)
    document.getElementById("letters").appendChild(letter)
    deleter.related = [deleter, cursor, letter]
    re_letter()
}

function del(deleter) {
    for (var i in deleter.related) {
        e = deleter.related[i]
        e.parentNode.removeChild(e)
    }
    re_letter()
}

function pos(e) {
    return Number(e.getAttribute('x').replace('%%',''))
}

function re_letter() {
    console.log('re_letter')
    ls = []
    letters = document.getElementById("letters")
    for (var i=0; i<letters.children.length; i++) {
        child = letters.children[i]
        if (child.classList.contains('letter')) {
            console.log(child.getAttribute('x') + ' ' + child.innerHTML)
            ls.push(child)
        }
    }
    ls = ls.sort(function(a,b) {return pos(a)-pos(b)})
    for (var i in ls)
        ls[i].innerHTML = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijlkmnopqrstuvwxyz'[i]
}
