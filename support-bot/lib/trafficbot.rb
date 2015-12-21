#!/usr/bin/ruby
#encoding: utf-8
#Traffic Light
# Basic Data Model is that the Jira thread will produce messages
# Messages are passed to the chat thread via an IPC threadsafe queue

Encoding.default_external = Encoding::UTF_8

require 'jira'
require 'yajl'
require 'time'
require 'thread'
require 'time-lord'
require 'mongo'

require_relative 'xmpp4r-simple.rb'
require_relative 'chat-functions.rb'
require_relative 'init-functions.rb'
require_relative 'chat-rec.rb'
require_relative 'support-issue-functions.rb'

# SGH, flag to turn on local execution of bot.
@test = false

# @issuesQuery = {"jira.fields.project.key" => { "$in" => ["CS", "PARTNER", "SUPPORT", "MMSSUPPORT"] }, "jira.fields.issuetype.id" => {"$ne" => "23"} }
@issuesQuery = {:$or =>
                    [
                        {
                            "jira.fields.project.key" => {"$in" => ["CS", "PARTNER", "SUPPORT", "MMSSUPPORT"] },
                            "jira.fields.issuetype.id" => {"$ne" => "23"}
                        },
                        {
                            "sfdc" => {"$exists" => true},
                            :$or =>
                                [
                                    {"sfdc.Jira_Number__c" => {"$exists" => false}},
                                    {"sfdc.Jira_Number__c" => ''}
                                ]
                        }
                    ]
               }


#Global Top Level variables
@jirausername = nil
@jirapassword = nil
@jabberusername = nil
@jabberpassword = nil
@jabberserver = 'talk.google.com'
@partychatdomain = '10genchat.appspotchat.com'

@roomName = { 'recip' => 'support-bot@10genchat.appspotchat.com', 'prot' => 'XMPP' }
@ircRoomName = { 'recip' => "#10gen/supportbot", 'prot' => 'IRC' }
@defaultXMPPRoom = 'support-bot@10genchat.appspotchat.com'

@roomNameNewIssue = { 'recip' => 'support-triage@10genchat.appspotchat.com', 'prot' => 'XMPP' }
  
if @test
  # SGH; change ircNameNewIssue to temporary flow
  @ircNameNewIssue = { 'recip' => '#10gen/commercial-support-test', 'prot' => 'IRC' }
else
  @ircNameNewIssue = { 'recip' => '#10gen/commercial-support', 'prot' => 'IRC' }
end
  
@jiraserver = 'https://jira.mongodb.org/'
@jiraInterval = 30

@ircServer = "irc.flowdock.com"
@ircPort = 6697
@ircuser = "trafficbot@10gen.com"
@ircpassword = "ONYjemt5MqgcpL0EnaVh"
if @test
  # SGH added another flow just for interacting with local supportbot
  @ircnick = "TrafficBot-test"
else
  @ircnick = "TrafficBot"
end
@ircchan = "#10gen/supportbot"

#@supportIRCChan = "#10gen/commercial-support"
@supportIRCChan = "#10gen/supportbot"

@loggingQueue = Queue.new

if @test
  # SGH; changed dbURI to local server for testing
  @dbURI = "mongodb://localhost:27017/support"
else # use production
  @dbURI = "mongodb://sdash-1.10gen.cc:27017,support-db-1.vpc3.10gen.cc:27017,support-db-2.vpc3.10gen.cc:27017/support?replicaSet=sdash"
end

@dbConnOpts = {:pool_size => 5}
@silent = false

@ftsActive = { "jira.fields.labels" => "fs", "jira.fields.status.id" => {"$nin" => [ "5", "6", "10007", "10006" ]} }
@ftsWFC = { "jira.fields.labels" => "fs", "jira.fields.status.id" => {"$in" => [ "10007", "10006" ]} }
@wfcGeneral = { "jira.fields.project.key" => { "$in" => ["CS", "PARTNER", "SUPPORT", "MMSSUPPORT"] }, "jira.fields.status.id" => "10006" }

@stateFile = 'trafficbot.sav'
@soundOnlyMode = true
@soundOn = true
@startTime = Time.now
@excludedAddresses = [ 'support-triage@10genchat.appspotchat.com' ]

@logLevel = 0

readSteeringFile(ARGV[0])

#Setup Jira
options = {
    :username => @jirausername,
    :password => @jirapassword,
    :site     => @jiraserver,
    :context_path => '',
    :auth_type => :basic,
    :ssl_verify_mode => OpenSSL::SSL::VERIFY_NONE
}

#Hash of Issues in Jira
@issues = {}

#Time of each check is tracked
@lastChecked = BSON::ObjectId.from_time(Time.now-1)

#List of items we have failed to auto complete
@autoCompleteFails = []

#IPC Thread
@ipcqueue = Queue.new
@chatRequests = Queue.new
@xmppQueue = Queue.new
@ircQueue = Queue.new

#Function Main
#Start a Basic Jira connection
client = Mongo::Client.new(@dbURI,@dbConnOpts)

#Fork Threads
if @soundOnlyMode == false
  @soundOn = false
  thr = Thread.new { mainChatThread() }
else
  logOut 'Running in sound only mode'
end
@botReboot = false
jthr = Thread.new { mainJiraThread(client) }
logThr = Thread.new { loggingThread() }
xmppThr = Thread.new { recXMPP() }
ircThr = Thread.new { recIRC() }

#Check the statefile on boot
@chatRequests.push("nobody XMPP LOADSTATE")

#Start Main Loop
while true

  if @soundOnlyMode == false
    if thr.status == 'aborting' || thr.status == nil
      logOut 'Chat Thread died, re-forking'
      thr = Thread.new { mainChatThread() }
    end
  else
    #If we are in sound only mode clean out our queues so we dont just consume memory forever
    @ipcqueue.clear
    @chatRequests.clear
  end
  if jthr.status == 'aborting' || jthr.status == nil
    logOut 'JiraThread died, re-forking'
    jthr = Thread.new { mainJiraThread(client) }
  else
    if @botReboot
      Thread.kill(jthr)
      client = Mongo::Client.new(@dbURI,@dbConnOpts)
      jthr = Thread.new { mainJiraThread(client) }
      @botReboot = false
      logOut "Just rebooted the Jira thread at user request"
    end
  end
  if logThr.status == 'aborting' || logThr.status == nil
    logOut 'Logger Thread died, re-forking'
    logThr = Thread.new { loggingThread() }
  end
  if xmppThr.status == 'aborting' || xmppThr.status == nil
    logOut 'Logger Thread died, re-forking'
    xmppThr = Thread.new { recXMPP() }
  end
  if ircThr.status == 'aborting' || ircThr.status == nil
    logOut 'Logger Thread died, re-forking'
    ircThr = Thread.new { recIRC() }
  end
  sleep 5
end

