# jira2txt

A small Python script to query the mongodb.org JIRA instance for issues and to print out the
specified field values in table format.

### Usage

The script has two modes to query for tickets, by key directly, or via the JIRA query language.

#### Querying by key(s)

Usage examples:

> Query for single key
> 
>     python jira2txt.py --key SERVER-12345
> 
> would print the following output:
> 
>     KEY             SUMMARY
>     
>     SERVER-12345    Validate write command documents in the server

<br> 

> Query for multiple keys, short version
> 
>     python jira2txt.py -k SERVER-12345 SERVER-9998 SERVER-4455
> 
> would print the following output:
> 
>     KEY             SUMMARY
>         
>     SERVER-12345    Validate write command documents in the server
>     SERVER-9998     mongod crash
>     SERVER-4455     replSetGetStatus errmsg isn't being set correctly for self

#### Querying via JQL (Jira Query Language)

Usage example:


> Query for the 10 SERVER tickets fixed for version 2.6.1 with highest priority
> 
>     python jira2txt.py --query 'project=SERVER and fixVersion="2.6.1" order by priority DESC' --limit 10
> 
> would print the following output:
> 
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

#### Specifying fields

Usage example: 

> Query for the 5 most recently created SERVER tickets assigned to a user and print the priorty, planned fixVersion 
> and components.
> 
>     python jira2txt.py -q 'project=SERVER and assignee=thomasr order by created DESC' -l 5 --fields key priority 
>     fixVersions components
> 
> would print out the following:
> 
>     KEY             PRIORITY        FIXVERSIONS                 COMPONENTS
>     
>     SERVER-13654    Major - P3      debugging with submitter    Replication/Pairing
>     SERVER-13605    Blocker - P1    debugging with submitter    Write Ops
>     SERVER-13574    Major - P3      debugging with submitter    Concurrency, Performance, Querying
>     SERVER-13568    Major - P3      debugging with submitter    Geo
>     SERVER-13526    Major - P3      debugging with submitter    Sharding
