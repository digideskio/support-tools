require 'jira'
require 'yajl'
require 'time'
require 'thread'
require 'time-lord'

require_relative '../lib/chat-functions.rb'
require_relative '../lib/init-functions.rb'

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

#Function readSteeringFile
# Reads a steering file to grab the username and password and other things need to know about
@jiraserver = 'https://jira.mongodb.org/'
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
@lastMsgForMe = ""
@chatRequests = Queue.new
@ipcqueue = Queue.new
@partychatdomain = "10genchat.appspotchat.com"


respondToPartyChat("[nobody] #!FTS", "support-bot@10genchat.appspotchat.com");
doQueueRead(client)
sleep 2
respondToChat("#!FTS", "nobody", "nobody" );
doQueueRead(client)
done = 0
until done == 3
	msg = @ipcqueue.pop["msg"] until @ipcqueue.empty?
	if msg != nil
		puts msg
		done += 1
		msg = nil
	end
end
