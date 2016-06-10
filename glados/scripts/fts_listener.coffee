TODO: Add help text and docs

module.exports = (robot) ->
  robot.router.post '/glados/fts-tickets', (req, res) ->
    console.dir("#{new Date()} jira webhook post_received")
    console.dir(req.body.payload)
    console.dir(req.body)
    data = if req.body.payload? then JSON.parse req.body.payload else req.body
    console.dir(JSON.stringify(data.issue.fields.label))
    console.dir(data.user.emailAddress)
    console.dir(data.issue.fields.customfield_10030.name)
    console.dir(typeof data.issue.fields.customfield_10030.name)
    shortened_subject = if data.issue.fields.summary.length >= 20 then data.issue.fields.summary.substring(0, 20) + ' ...' else data.issue.fields.summary
    if data.comment? and data.comment.body?
        shortened_body = if data.comment.body.length >= 100 then data.comment.body.substring(0, 100).replace(/\r?\n|\r/g, " ") + "..." else data.comment.body.replace(/\r?\n|\r/g, " ")
    else
        shortened_body = "Non-comment update to ticket."
    if data.user.emailAddress.indexOf('@mongodb.com') != -1 || data.user.emailAddress.indexOf('@10gen.com') != -1
        console.dir('MongoDB user - not pasting update')
        console.dir("FTS comment [#{data.user.name} | https://jira.mongodb.org/browse/#{data.issue.key} | #{shortened_subject}]: #{shortened_body}")
    else
        console.dir('Not a MongoDB user - pasting the update')
        console.dir("FTS comment [#{data.user.name} | https://jira.mongodb.org/browse/#{data.issue.key} | #{shortened_subject}]: #{shortened_body}")
        robot.messageRoom "glados-test", "FTS comment [#{data.user.name} | https://jira.mongodb.org/browse/#{data.issue.key} | #{shortened_subject}]: #{shortened_body}"
    res.send 'OK'
