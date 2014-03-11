// ==UserScript==
// @id             jira.mongodb.org-show-priority
// @name           MongoDB Jira show priority
// @version        1.0
// @namespace      https://jira.mongodb.org/
// @author         Kevin Pulo
// @description    Stop making me scroll up to check ticket priority all the time
// @include        https://jira.mongodb.org/browse/*
// @run-at         document-idle
// ==/UserScript==

var summary_val = document.getElementById("summary-val");

var priority_val = document.getElementById("priority-val");
var status_val = document.getElementById("status-val");

if (summary_val && priority_val) {
	var priority_img = priority_val.children[0];
	if (priority_img && priority_img.tagName == "IMG") {
		var new_priority_img = priority_img.cloneNode(true);
		new_priority_img.style.verticalAlign = "baseline";
		summary_val.style.verticalAlign = "baseline";
		summary_val.parentNode.insertBefore(new_priority_img, summary_val);
	}
}

if (summary_val && status_val) {
	var status_img = status_val.children[0];
	if (status_img && status_img.tagName == "IMG") {
		var new_status_img = status_img.cloneNode(true);
		new_status_img.style.verticalAlign = "baseline";
		new_status_img.style.marginRight = "1em";
		summary_val.style.verticalAlign = "baseline";
		summary_val.parentNode.insertBefore(new_status_img, summary_val);
		summary_val.parentNode.insertBefore("&nbsp;&nbsp;", summary_val);
	}
}

