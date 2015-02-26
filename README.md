support-tools
=============

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [[Jira Compact Dashboard](./scripts/tampermonkey/jira_compact_dashboard.js)](#jira-compact-dashboardscriptstampermonkeyjira_compact_dashboardjs)
- [[mdb](./mdb)](#mdbmdb)
- [[mdiag](./mdiag)](#mdiagmdiag)
- [[mongo-docker](./mongo-docker)](#mongo-dockermongo-docker)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

See this Wiki page:
https://wiki.mongodb.com/display/cs/Support+Tools

*PLEASE BE CAREFUL WHEN PUSHING TO THE 10gen/support-tools REPO*

*The safest way to work (especially if you're not a git guru) is to fork your own copy of this repo, work in there, and then submit pull requests.*

[Jira Compact Dashboard](./scripts/tampermonkey/jira_compact_dashboard.js)
--
Reclaims some Jira whitespace (65px height, 158px width) by resizing the header and moving the dashboard tabs horizontally. This effectively makes the dashboard use the full width of the screen.

- Owner: [Stephen Steneker](mailto:stennie@mongodb.com)

[mdb](./mdb)
--
Simple tool to dump parts of mongo databases to debug corruption issues

- Owner: [Bruce Lucas](mailto:bruce.lucas@@mongodb.com)

[mdiag](./mdiag)
--
Script to give to users/customers, to gather a wide variety of Linux system-level diagnostic information.
[More information](./mdiag#readme)

- Owner: [Kevin Pulo](mailto:kevin.pulo@mongodb.com)

[mongo-docker](./mongo-docker)
--
Mongo-docker is a docker-based framework for testing complicated setups

- Owner: [Alex Komyagin](mailto:alex@mongodb.com)