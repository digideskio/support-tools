db_support = db.getSisterDB("support")
coll_karakuri = db_support.karakuri
coll_issues = db_support.issues
db_karakuri = db.getSisterDB("karakuri")
coll_logs = db_karakuri.logs

coll_karakuri.find({}).forEach(function(d){
    jirakey = d['key'];
    id = coll_issues.findOne({'jira.key': jirakey}, {_id:1})['_id']

    n = coll_issues.count({'jira.key': jirakey})

    if (n !== 1) {
        print("Error: more than one " + jirakey);
        return;
    }

    if (d.hasOwnProperty("actions_wanted")) {
        delete d['actions_wanted'];
    }

    if (d.hasOwnProperty("actions_taken")) {
        workflows = [];

        for(i = 0; i < d['actions_taken'].length; i++){
            logId = ObjectId()
            workflow = d['actions_taken'][i];
            
            if (workflow == "ProactiveResp1") {
                workflow = "Proactive1"
                workflows.push({'name': workflow, 'log':logId});
            }
            if (workflow == "ProactiveResp2") {
                workflow = "Proactive2"
                workflows.push({'name': workflow, 'log':logId});
            }
            if (workflow == "ProactiveResp3") {
                workflow = "Proactive3"
                workflows.push({'name': workflow, 'log':logId});
            }

            coll_logs.save({'_id':logId, 'id':id, 'workflow': workflow})
        }

        d['workflows_performed'] = workflows;
    }

    if (d.hasOwnProperty('key')) {
        delete d['key'];
    }

    if (d.hasOwnProperty('_id')) {
        delete d['_id'];
    }

    if (d.hasOwnProperty('actions_taken')) {
        delete d['actions_taken'];
    }

    i = coll_issues.findOne({'jira.key': jirakey});
    i['karakuri'] = d;
    coll_issues.save(i);
})
