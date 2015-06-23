# Description:
#   Linkify MongoDB JIRA links
#
module.exports = (robot) ->
    robot.hear /\bCS-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [CS-#{msg.match[1]}](https://jira.mongodb.org/browse/CS-#{msg.match[1]})"

    robot.hear /\bCDRIVER-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [CDRIVER-#{msg.match[1]}](https://jira.mongodb.org/browse/CDRIVER-#{msg.match[1]})"

    robot.hear /\bCSHARP-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [CSHARP-#{msg.match[1]}](https://jira.mongodb.org/browse/CSHARP-#{msg.match[1]})"

    robot.hear /\bJAVA-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [JAVA-#{msg.match[1]}](https://jira.mongodb.org/browse/JAVA-#{msg.match[1]})"

    robot.hear /\bHELP-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [HELP-#{msg.match[1]}](https://jira.mongodb.org/browse/HELP-#{msg.match[1]})"

    robot.hear /\bMMS-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [MMS-#{msg.match[1]}](https://jira.mongodb.org/browse/MMS-#{msg.match[1]})"

    robot.hear /\bCM-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [CM-#{msg.match[1]}](https://jira.mongodb.org/browse/CM-#{msg.match[1]})"

    robot.hear /\bBRS-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [BRS-#{msg.match[1]}](https://jira.mongodb.org/browse/BRS-#{msg.match[1]})"

    robot.hear /\bMMSP-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [MMSP-#{msg.match[1]}](https://jira.mongodb.org/browse/MMSP-#{msg.match[1]})"

    robot.hear /\bFACILITIES-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [FACILITIES-#{msg.match[1]}](https://jira.mongodb.org/browse/FACILITIES-#{msg.match[1]})"

    robot.hear /\bOFFICEIT-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [OFFICEIT-#{msg.match[1]}](https://jira.mongodb.org/browse/OFFICEIT-#{msg.match[1]})"

    robot.hear /\bSUPPORT-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [SUPPORT-#{msg.match[1]}](https://jira.mongodb.org/browse/SUPPORT-#{msg.match[1]})"

    robot.hear /\bFREE-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [FREE-#{msg.match[1]}](https://jira.mongodb.org/browse/FREE-#{msg.match[1]})"

    robot.hear /\bMMSSUPPORT-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [MMSSUPPORT-#{msg.match[1]}](https://jira.mongodb.org/browse/MMSSUPPORT-#{msg.match[1]})"

    robot.hear /\bPARTNER-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [PARTNER-#{msg.match[1]}](https://jira.mongodb.org/browse/PARTNER-#{msg.match[1]})"

    robot.hear /\bTSPROJ-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [TSPROJ-#{msg.match[1]}](https://jira.mongodb.org/browse/TSPROJ-#{msg.match[1]})"

    robot.hear /\bFIELD-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [FIELD-#{msg.match[1]}](https://jira.mongodb.org/browse/FIELD-#{msg.match[1]})"

    robot.hear /\bSERVER-(\d+)/i, (msg) ->
        msg.envelope.newMessage = true
        msg.send "#{msg.message.user.name} is sharing [SERVER-#{msg.match[1]}](https://jira.mongodb.org/browse/SERVER-#{msg.match[1]})"
