$('#myTab a').click(function (e) {
      e.preventDefault()
      $(this).tab('show')
})


addToTicket = function(button, testSrc, testName) {
    console.log("addToTicket");
    header = $("#div_failedTests_"+testSrc+"_"+testName+" div.header").text();
    comment = $("#div_failedTests_"+testSrc+"_"+testName+" div.comment").text();
    console.log(header);
    console.log(comment);
    // new div
    ticketBody = document.getElementById("div_ticketDescription_mainBody");
    console.log(ticketBody);
    div = document.createElement("div");
    div.id = "div_ticketDescription_"+testSrc+"_"+testName;
    headerDiv = document.createElement("div");
    $(headerDiv).addClass("header");
    $(headerDiv).addClass("editable");
    headerDiv.innerText = "h5. "+header;
    headerDiv.addEventListener("click", editableClickFunction);
    commentDiv = document.createElement("div");
    $(commentDiv).addClass("comment");
    $(commentDiv).addClass("editable");
    commentDiv.innerText = comment;
    commentDiv.addEventListener("click", editableClickFunction);
    div.appendChild(headerDiv);
    div.appendChild(commentDiv);
    ticketBody.appendChild(div);
    $(div).css('padding-bottom', '2em');

    // change button
    console.log(button);
    button.innerText = "Remove from ticket";
    button.onclick = function() {removeFromTicket(button, testSrc, testName)};
};

removeFromTicket = function(button, testSrc, testName) {
    console.log("removeFromTicket");
    console.log(testSrc+"_"+testName);
    div = document.getElementById("div_ticketDescription_"+testSrc+"_"+testName);
    if (div) {
        div.parentNode.removeChild(div);
        button.innerText = "Add to ticket";
        button.onclick = function() {addToTicket(button, testSrc, testName)};
    } else {
        console.log("div_ticketDescription_"+testSrc+"_"+testName+" dne!");
    }
};

saveStateAndSetToEditable = function() {
    console.log("beingedited -> editable");
    content = $("#beingedited textarea").val()
    $("#beingedited").html(content)
    $("#beingedited").attr('id', '');
};

editableClickFunction = function(e) {
    // User wants to edit the content in this div
    // Get div content and replace it with a textarea of the same content
    div = e.target;

    div.id = "beingedited";
    content = div.innerText;
    height = $(div).height();
    ta = document.createElement("textarea");
    ta.value = content;
    $(ta).css('height', height*1.1);
    div.innerHTML = null;
    div.appendChild(ta);
};

/*
$('div.editable').click(function(e) {
    return editableClickFunction(e);
});
*/

document.addEventListener("click", function(e) {
    // If the user clicks on an editable element not being edited, save the
    // state and move it back to editable
    if (e.target.parentNode.id !== "beingedited" && document.getElementById("beingedited")) {
        saveStateAndSetToEditable();
    }
    if (($(e.target).hasClass("editable"))) {
        editableClickFunction(e);
    }
});
