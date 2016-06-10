require 'jira'
require 'yajl'
require 'time'
require 'thread'
require 'time-lord'

Encoding.default_external = Encoding::UTF_8

require_relative '../lib/jira-functions.rb'
require_relative '../lib/chat-functions.rb'
require_relative '../lib/init-functions.rb'

@jiraserver = 'https://jira.mongodb.org/'

def logOut(msg)
  puts "logOut #{msg}"
end

readSteeringFile('../conf/trafficbot.conf')

#Setup Jira
options = {
    :username => @jirausername,
    :password => @jirapassword,
    :site     => @jiraserver,
    :context_path => '',
    :auth_type => :basic,
    :ssl_verify_mode => OpenSSL::SSL::VERIFY_NONE
}

mode = "mongo"
if mode == 'api'
  require_relative '../lib/jira-functions.rb'
  @ftsWFC = 'filter = "Commercial Support, \"Follow the Sun\" (FS label), Waiting for Customer"'
  @ftsActive = 'filter = "Commercial Support, \"Follow the Sun\" (FS label), Needs 10gen Response"'
  @wfcPerson = "(Owner = \"USERNAME\" or assignee = \"USERNAME\") and (project = \"Commercial Support\" OR project = \"Community Private\") and status = \"Waiting for Customer\""
  @wfcGeneral = "(project = \"Commercial Support\" OR project = \"Community Private\") and status = \"Waiting for Customer\""
  client = JIRA::Client.new(options)
else
  require 'mongo'
  require_relative '../lib/support-jira-functions.rb'
  @ftsActive = { "fields.labels" => "fs", "fields.status.id" => {"$nin" => [ "5", "6", "10007", "10006" ]} }
  @ftsWFC = { "fields.labels" => "fs", "fields.status.id" => {"$in" => [ "10007", "10006" ]} }
  @wfcGeneral = { "fields.project.key" => { "$in" => ["CS", "Partner", "Community Private"] }, "fields.status.id" => "10006" }
  client = Mongo::MongoClient.from_uri("mongodb://localhost:27017/jira", {:pool_size => 5}).db('jira')
end
@issues = {}
@ipcqueue = Queue.new
@chatRequests = Queue.new
@stateFile = 'trafficbot.sav'
@jiraInterval = 30
@roomName = "support-bot@10genchat.appspotchat.com"

respondToPartyChat("[nobody] #!REVIEW CS-1234 ", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[nobody] #!REVIEW CS-6480 ", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[nobody] #!REVIEW CS-9003 ", "support-bot@10genchat.appspotchat.com");

respondToPartyChat("[nobody] #!REVIEW SUPPORT-831 ", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[nobody] #!REVIEW CS-10034 ", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[nobody] #!REVIEW CS-10034-1 ", "support-bot@10genchat.appspotchat.com");
@chatRequests.push('nobody LIST')
doQueueRead(client)
puts @ipcqueue.pop["msg"] until @ipcqueue.empty?
checkForFinalized(client)
@chatRequests.push('nobody LIST')
doQueueRead(client)
puts @ipcqueue.pop["msg"] until @ipcqueue.empty?
checkForFinalized(client)
doQueueRead(client)
puts @ipcqueue.pop until @ipcqueue.empty?



