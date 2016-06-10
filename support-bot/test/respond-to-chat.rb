require 'jira'
require 'yajl'
require 'time'
require 'thread'
require 'time-lord'

#require_relative '../lib/jira-functions.rb'
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
  puts var
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

puts respondToChat('#!RENAME SirBotsALot');
