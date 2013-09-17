// ==UserScript==
// @name       MongoDB Jira - Compact Dashboard
// @namespace  https://jira.mongodb.org/
// @version    0.40
// @description  Moar compact Jira dashboard
// @match      https://jira.mongodb.org/secure/Dashboard.jspa*
// @match      https://jira.mongodb.org/browse/*
// @copyright  2013, stennie@mongodb.com
// ==/UserScript==

// Custom CSS
var css = [];
function addStyle(style) {
    css[css.length] = style;
}

// Reclaim some space from header area
addStyle(".aui-avatar-project img { width: 40px; height: 40px }");
addStyle(".issue-header .issue-header-content .aui-page-header { padding: 0px }");
addStyle(".issue-header .issue-header-content .command-bar { padding: 0px }");;

// Add background colour to highlight warnings and CS info
addStyle("#announcement-banner { padding: 5px; background-color: #ffffcc; }");
addStyle("#watchersDialog { background-color: #9ec05a }");
addStyle("div#reporter { color: #9ec05a }");

// Change tabs from vertical to horizontal
function useHorizontalTabs () {
    var dashBoard = document.getElementById("dashboard");
    if (dashBoard) {
        dashBoard.className = dashBoard.className.replace(/v-tabs/, 'h-tabs');
        dashBoard.getElementsByTagName('ul')[0].className = 'horizontal tabs';

        // Add horizontal tab style
        addStyle("ul.horizontal{overflow:hidden;position:relative;top:1px;}");
        addStyle("ul.horizontal li{float:left;margin:0 -1px 0 0;width:auto;white-space:nowrap;}");
        addStyle("ul.horizontal li strong,ul.horizontal li.tab-title{padding:.2em .5em .1em;}");
        addStyle("ul.horizontal li.first{margin-left:1em;}");
        addStyle("ul.horizontal li.active{border-bottom-color:#fff;color:#000;text-decoration:underline}");

        addStyle("ul.tabs { list-style-type: none; margin: 0; padding: 0; z-index: 5;}");

        // Highlight current dashboard title
        addStyle(".aui-page-header-main h1 { color: #9ec05a }");

        // Reclaim some vertical space
        addStyle("#dashboard-content { margin-top: -15px }");
    }
}

// Append custom styles
function writeStyles () {
    var newStyle = document.createElement('style');
    newStyle.type = 'text/css';
    if (document.getElementsByTagName) {
        document.getElementsByTagName('head')[0].appendChild(newStyle);
        if (newStyle.sheet && newStyle.sheet.insertRule) {
            for (var i = 0; i < css.length; i++) {
                newStyle.sheet.insertRule(css[i], 0);
            }
        }
    }
}

// 1. Apply JavaScript fixups 
useHorizontalTabs();

// 2. Inject custom styles
writeStyles();