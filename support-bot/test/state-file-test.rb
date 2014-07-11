require 'jira'
require 'yajl'
require 'time'
require 'thread'
require 'time-lord'

require_relative '../lib/jira-functions.rb'
require_relative '../lib/chat-functions.rb'

#Function readSteeringFile
# Reads a steering file to grab the username and password and other things need to know about
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

def readSteeringFile(file = 'trafficbot.conf')
  if file == nil || (! File.exists? file)
    file = '../conf/trafficbot.conf'
  end

  File.open(file).each_line do |line|
    arr = line.split /\s+=\s+/
    case arr[0]
      when 'jirausername'
        @jirausername = arr[1].chomp
      when 'jirapassword'
        @jirapassword = arr[1].chomp
      when 'jabberusername'
        @jabberusername = arr[1].chomp
      when 'jabberpassword'
        @jabberpassword = arr[1].chomp
    end
  end
end

def logOut(var)
  puts "log() #{var}"
end

readSteeringFile(ARGV[1])

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
respondToPartyChat("[nobody] #!REVIEW CS-222 @david @thomas @andre,kevin", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[nobody] #!REVIEW CS-111, please", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[nobody] #!REVIEW http://jira.mongodb.org/CS-1234 ", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[nobody] #!LGTM CS-1234 http://en.wikipedia.org/wiki/Australia", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[test] #!LGTM CS-1234", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[test] #!REVIEW CS-333", "support-bot@10genchat.appspotchat.com");
respondToPartyChat("[test] #!NEEDSWORK CS-333", "support-bot@10genchat.appspotchat.com");
@chatRequests.push('nobody LIST')
doQueueRead(client)
puts @ipcqueue.pop["msg"] until @ipcqueue.empty?

saveState
#p `cat #{@stateFile}`
@issues.clear
@chatRequests.push('nobody LIST')
doQueueRead(client)
puts @ipcqueue.pop["msg"] until @ipcqueue.empty?
loadState
@chatRequests.push('nobody LIST')
doQueueRead(client)
puts @ipcqueue.pop["msg"] until @ipcqueue.empty?
