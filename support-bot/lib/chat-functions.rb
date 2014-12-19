#Function respondToChat
# Responds to chat requests
# Msg is the message body
# Username is the username of the requestor
# Room is the return address of this message, be it a user or a room
def respondToChat(msg, username = nil, protocol = 'XMPP', room = "nil")
  array = msg.split
  body = array.shift.chomp
  thisForMe = true
  response = nil
  begin
    case body.to_s.upcase
      when '#!HELP'
        response = "Currently the bot supports the following commands:\n"
        response+= "#!GREET - Have the bot greet you\n"
        response+= "#!LIST - List the items active in the bot queue\n"
        response+= "#!IGNORE <case> - Stop SLA Nags on this case\n"
        response+= "#!ACTIVE <case> - Start SLA Nags on this case again\n"
        response+= "#!LIST IGNORED - List the cases the bot is ignoring\n"
        response+= "#!REVIEW <case> [@reviewer(s)] - Add a nag for a review of a case and optionally supply reviewers\n"
        response+= "#!LGTM <case> - State that the response on a case is good (visible under #!LIST)\n"
        response+= "#!NEEDSWORK <case> - State that the response on a case is in need of work (visible under #!LIST)\n"
        response+= "#!FIN <case> - Mark a case as reviewed\n"
        response+= "#!FTS - Do the FTS email lookup (time consuming)\n"
        response+= "#!INVITE <email> Invite user to support-bot channel\n"
      when 'I'
        if array.join(' ').chomp.upcase == 'REQUEST THE HIGHEST OF FIVES'
          response = "/me gives #{username} the highest fives"
        end
      when '#!GREET'
        response = "Greetings #{username}"
      when '#!BOT5'
        response = "/me gives #{username} a high 5"
      when '#!BOTHUG'
        response = "/me gives #{username} a hug"
      when '#!UPTIME'
        response = "Uptime: #{Time.now - @startTime}"
      when '#!RENAME'
        response = "/alias #{array[0]}"
      when '#!SYN'
        response = "#!SYNACK"
      when '#!SAVESTATE'
        @chatRequests.push("#{room} #{protocol} SAVESTATE")
      when '#!LOADSTATE'
        @chatRequests.push("#{room} #{protocol} LOADSTATE")
      when '#!ACK'
        response = "Handshake Complete"
      when '#!IGNORE'
        @chatRequests.push("#{room} #{protocol} IGNORE #{array.join(' ').upcase}")
      when '#!ACTIVE'
        @chatRequests.push("#{@defaultXMPPRoom} #{protocol} ACTIVE #{array.join(' ').upcase}")
      when '#!REBOOT'
        @botReboot = true
        logOut "reboot called for by user #{username}"
        response = "Will do, please wait 10 seconds and try a #!LIST"
      when '#!LIST'
        if array.empty?
          @chatRequests.push("#{room} #{protocol} LIST")
        else
          @chatRequests.push("#{room} #{protocol} LIST #{array.join(' ').upcase}")
        end
      when '#!LISTIGNORED'
        @chatRequests.push("#{@defaultXMPPRoom} #{protocol} LIST IGNORED")
      when '#!REVIEW'
        @chatRequests.push("#{@defaultXMPPRoom} #{protocol} REVIEW #{array[0].upcase} #{username} #{array[1..-1].join(' ')}")
      when '#!FIN'
        @chatRequests.push("#{@defaultXMPPRoom} #{protocol} FIN #{array[0].upcase} #{username} #{array[1..-1].join(' ')}")
      when '#!LGTM'
        @chatRequests.push("#{@defaultXMPPRoom} #{protocol} LGTM #{array[0].upcase} #{username} #{array[1..-1].join(' ')}")
      when '#!NEEDSWORK'
        @chatRequests.push("#{@defaultXMPPRoom} #{protocol} NEEDSWORK #{array[0].upcase} #{username} #{array[1..-1].join(' ')}")
      when '#!PLAYTESTSOUND'
        @chatRequests.push('nil SOUNDCHECK')
      when '#!FTS'
        @chatRequests.push("#{room} #{protocol} FTS")
      when '#!WFC'
        @chatRequests.push("#{room} #{protocol} WFC #{array.join(' ').upcase}")
      when '#!LOGLEVEL'
        begin
          @logLevel = array[0].to_i
        rescue => e
          return "Failed to set log level with reason: #{e}"
        end
        return "Set logLevel to #{array[0].to_i}"
      when "#!INVITE"
        @ipcqueue.push({'msg'=>"/invite #{array[0]}", 'dst' => @roomName})
      when '#!ADDFRIEND'
        return "add #{array.join(' ')}"
      else
        thisForMe = false
        #logOut 'This message is not for me'
    end
  rescue
    return "#!BOTFAIL"
  end
  if thisForMe
    @lastMsgForMe = Time.now
  end
  return response
end

#Function respondToPartyChat
# Grabs the username from a partychat request then calls respondToChat
def respondToPartyChat(msg, room)
  array = msg.split
  #Username in partychat needs the leading "[" and trailing "]" removed
  username = array.shift[1..-2]
  return respondToChat(array.join(' '), username, 'XMPP', room)
end

def send(prot, msg, dst)
  case prot
    when "XMPP"
      @xmppQueue.push({'dst' => dst, 'msg' => msg})
      #When we are sending something to support-bot send it to IRC as well
    when "IRC"
      @ircQueue.push({'dst' => dst, 'msg' => msg})
    else
      logOut "Unknown protocol '#{prot}'. Msg was '#{msg}' and destination was '#{dst}'"
  end
end

# Function MainChatThread
# Thread for chat integration; opens a Jabber connection and enters the chatroom
# Passes messages from the IPC queue about new issues to the team.
def mainChatThread()
  @lastMsgForMe = Time.now
    go = true
    while go
      begin
        #Empty the Outbound Message Queue
        limit = 10
        until @ipcqueue.empty?
          popped = @ipcqueue.pop
          msg = popped["msg"]
          dst = popped["dst"]["recip"]
          prot = popped["dst"]["prot"]
          if msg.is_a? String
            send(prot, msg, dst)
            logOut "#{dst} say: '#{msg}'" unless msg.empty?
          elsif msg.is_a? Jabber::Message
            send(prot, msg, dst)
            logOut "#{dst} say: '#{msg}'"
          end
          if @ipcqueue.length > 10 || limit <= 0
            logOut "Holy shit we just cleared the queue. It was #{@ipcqueue.length} messages long and I had sent #{10 - limit} messages !"
            @ipcqueue.clear
            sleep 60
            return
          end
          sleep 0.25
          limit-=1
        end

        sleep 1
      rescue => e
        logOut 'error, rescue activated'
        logOut "error #{e}"
        logOut "backtrace #{e.backtrace}"
      end
    end

end #mainChatThread
