// ==UserScript==
// @name       MongoDB Jira - Compact Dashboard
// @namespace  https://jira.mongodb.org/
// @version    0.30
// @description  Moar compact Jira dashboard
// @match      https://jira.mongodb.org/secure/Dashboard.jspa*
// @copyright  2013, stennie@10gen.com
// ==/UserScript==

// Custom CSS
var css = [];
function addStyle(style) {
    css[css.length] = style;
}

// Reduce height of masthead & logo strap from 90px to 30px
addStyle(".aui-theme-default #header #logo a img { height: 30px; width:90px }");
addStyle(".aui-theme-default #header .global { height: 30px }");
addStyle("#announcement-banner { padding: 0px }");

// Highlight current dashboard tab
addStyle("ul.tabs li.active strong { font-size:16px; background-color: lightgreen; }");

// Change tabs from vertical to horizontal
function useHorizontalTabs () {
    var dashBoard = document.getElementById("dashboard");
    dashBoard.className = dashBoard.className.replace(/v-tabs/, 'h-tabs');
    dashBoard.getElementsByTagName('ul')[0].className = 'horizontal tabs';

    // Reclaim some vertical space
    addStyle("#dashboard-content { margin-top: -15px }");
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