# jira2txt

A small Python script to query the `mongod.org` JIRA instance for certain keys and to print out the
specified field values in table format.

### Usage

The script has two modes to query for tickets, by key directly, or via the JIRA query language.

##### 1. Querying by key(s)

Usage examples:

> Query for single key
> 
>     ```
>     python jira2txt.py --key SERVER-12345
>     ```
> 
> would print the following output:
> 
>     ```
>     KEY             SUMMARY
>     
>     SERVER-12345    Validate write command documents in the server
>     ```

<br>

> Query for multiple keys, short version
> 
>     ```
>     python jira2txt.py -k SERVER-12345 SERVER-9998 SERVER-4455
>     ```
> 
> would print the following output:
> 
>     ```
>     KEY             SUMMARY
>     
>     SERVER-12345    Validate write command documents in the server
>     SERVER-9998     mongod crash
>     SERVER-4455     replSetGetStatus errmsg isn't being set correctly for self
>     ```

##### 2. Querying via JQL (Jira Query Language)

Usage examples:


> Query for all SERVER tickets closed for version 2.6.1
> 
>     ```
>     python jira2txt.py --query 'project=SERVER and fixVersion="2.6.1" order by priority DESC' --limit 10
>     ```
> 
> would print the following output:
> 
>     ```
>     KEY             SUMMARY
>     
>     SERVER-13495    Concurrent GETMORE and KILLCURSORS operations can cause race condition and server crash
>     SERVER-13500    Changing replica set configuration can crash running members
>     SERVER-13515    Cannot install MongoDB as a service on Windows
>     SERVER-13516    Array updates on documents with more than 128 BSON elements may crash mongod
>     SERVER-13589    Background index builds from a 2.6.0 primary fail to complete on 2.4.x secondaries
>     SERVER-13566    Using the OplogReplay flag with extra predicates can yield incorrect results
>     SERVER-13620    Replicated data definition commands will fail on secondaries during background index build
>     SERVER-13644    Sensitive credentials in startup options are not redacted and may be exposed
>     SERVER-13563    Upgrading from 2.4.x to 2.6.0 via yum clobbers configuration file
>     SERVER-13518    mongos does not generate _id for insert documents that are missing it
>     ```

<br>
