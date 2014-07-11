#!/usr/bin/ruby

require 'jira'
require 'yajl'
require 'time'
require 'thread'
require 'time-lord'

require_relative '../lib/jira-functions.rb'
require_relative '../lib/chat-functions.rb'
require_relative '../lib/init-functions.rb'

#Function readSteeringFile
# Reads a steering file to grab the username and password and other things need to know about
@jiraserver = 'https://jira.mongodb.org/'
@wfcPerson = "(Owner = \"USERNAME\" or assignee = \"USERNAME\") and (project = \"Commercial Support\" OR project = \"Community Private\") and status = \"Waiting for Customer\""
@wfcGeneral = "(project = \"Commercial Support\" OR project = \"Community Private\") and status = \"Waiting for Customer\""
@lastMsgForMe = ""
@chatRequests = Queue.new
@ipcqueue = Queue.new
@partychatdomain = "10genchat.appspotchat.com"
@soundOnlyMode = false

def logOut(msg)
        puts "logOut #{msg}"
end

readSteeringFile("../conf/trafficbot.conf")

#Setup Jira
options = {
    :username => @jirausername,
    :password => @jirapassword,
    :site     => @jiraserver,
    :context_path => '',
    :auth_type => :basic,
    :ssl_verify_mode => OpenSSL::SSL::VERIFY_NONE
}

myusername = 'david.hows'
client = JIRA::Client.new(options)
respondToPartyChat("[nobody] #!WFC", "support-triage@10genchat.appspotchat.com");
doQueueRead(client)
sleep 2
respondToChat("#!WFC #{myusername}", "nobody", "nobody");
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
