#!/usr/bin/ruby

require_relative '../lib/init-functions.rb'

@jirausername = "x"
@jirapassword = "x"
@jabberusername = "x"
@jabberpassword = "x"
@soundOnlyMode = false
@loggingQueue = Queue.new
filename = '../conf/trafficbot.conf-orig'

readSteeringFile(filename)

if @jirausername != 'my_jira_username'
	puts "FAIL on JIRA Username"
end
if @jirapassword != 'my_jira_password'
        puts "FAIL on JIRA Password"
end
if @jabberusername != 'my_jabber_username'
        puts "FAIL on Jabber Username"
end
if @jabberpassword != 'my_jabber_password'
        puts "FAIL on Jabber Password"
end
if @soundOnlyMode != true
	puts "Fail on Soundonly"
end

