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
@jiraquery = 'filter = "Commercial Support, Unassigned, Needs 10gen Response"'
@ftsWFC = 'filter = "Commercial Support, \"Follow the Sun\" (FS label), Waiting for Customer"'
@ftsActive = 'filter = "Commercial Support, \"Follow the Sun\" (FS label), Needs 10gen Response"'
@issues = {}
@ipcqueue = Queue.new
@chatRequests = Queue.new
@stateFile = 'trafficbot.sav'
@jiraInterval = 30
@roomName = "support-bot@10genchat.appspotchat.com"

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

client = JIRA::Client.new(options)

soundEffect()
gets
soundEffect("CS-1234", "Blocker")
gets
soundEffect("MMSSUPPORT-123", "Blocker")
soundEffect("SUPPORT-123", "Trivial")
gets
