def recXMPP
  im = Jabber::Simple.new(@jabberusername, @jabberpassword, nil, "Available", @jabberserver)
  logOut("Connected to XMPP server #{@jabberserver}")
  while true
    begin

      #Grab and format incoming messages
      im.received_messages { |msg|
        if msg.type == :chat
          incomingAddress = msg.from.to_s.split('/')[0]
          logOut msg.body
          ret = nil
          arr = incomingAddress.split("@")
          if arr[1] == @partychatdomain
            if @excludedAddresses.include? incomingAddress
              respondToPartyChat(msg.body, @defaultXMPPRoom )
              ret = nil
            else
              ret = respondToPartyChat(msg.body, incomingAddress)
            end
          else
            username = arr[0]
            ret = respondToChat(msg.body, username, 'XMPP', incomingAddress)
          end
          if ret
            if ret.start_with? 'add'
              user = ret.split(' ')[1]
              im.add(user)
              im.deliver(incomingAddress, "I added a friend: #{ret}")
              logOut "I added a friend: #{ret}", 1
            else
              im.deliver(incomingAddress, ret) unless ret.empty?
              logOut "I said: #{ret}" unless ret.empty?
            end
          end
        end
      }
      #Send all the outgoing XMPP messages
      until @xmppQueue.empty?
        pop = @xmppQueue.pop
        if pop["msg"].class == Jabber::Message
          im.deliver(pop["dst"], pop["msg"])
        else
          im.deliver(pop["dst"], pop["msg"]) unless pop["msg"] == ""
        end
      end
      if ! im.connected?
        im = Jabber::Simple.new(@jabberusername, @jabberpassword, nil, "Available", @jabberserver)
        logOut 'XMPP disconnected, reconnecting'
      end
      sleep 1
    rescue => e
      logOut 'error, rescue activated'
      logOut "error #{e}"
      logOut "backtrace #{e.backtrace}"
      im = Jabber::Simple.new(@jabberusername, @jabberpassword, nil, "Available", @jabberserver)
    end
  end
end

def connIrc
  socket = TCPSocket.new(@ircServer, @ircPort)
  ssl = OpenSSL::SSL::SSLSocket.new(socket)
  ssl.sync_close = true
  ssl.connect

  ssl.puts("CAP LS")
  ssl.puts("PASS #{@ircpassword}")
  ssl.puts("NICK #{@ircnick}")
  ssl.puts("USER #{@ircuser} 0 * :#{@ircnick}")

  msg = ssl.gets()
  until msg.include? "PING"
    msg = ssl.gets()
  end
  arr = msg.split
  resp = arr[1]
  ssl.puts("PONG #{resp}")
  ssl.puts("PRIVMSG NickServ :identify #{@ircuser} #{@ircpassword}")

  logOut("Connected to IRC #{@ircServer}")

  return ssl
end

def recIRC
  require "openssl"
  require "socket"
  ircConn = connIrc
  lastPing = Time.now()

  while true
    #Loop and read until get an assertion about 'blocking' assertion
    begin
      while true
        msg = ircConn.read_nonblock(1000000)
        # ":David!david.hows@10gen.com PRIVMSG #10gen/commercial-support :bot?\r\n"
        logOut("IRC got #{msg}")
        ret = nil
        incomingAddress = nil
        if msg.include? 'PRIVMSG'
          # Flowdock uses a special format for conversations that are bridged to IRC: [original message] << reply message.
          # examples: 
          # initial comment
          # [initial comment] << second comment in ceonversation
          # [initial comment] << third comment in conversation
          # Note there is no escape mechanism, but << will be URL-encoded on the conversation reply.
          # Note2 if a use type a message that 
          # [conversation that has brackets]
          # [[conversation that has brackets]] << reply to bracket conversation
          #
          # Note that if a user manually enters a message that looks like a conversation it won't be modified by the bridge.
          # This is a limitation of the bridge and a good reason to stop using it as soon as possible.
          # Kill the conversation portion so we can see the underlying command.
          arr = msg.sub(/:\[.*\] << /,'').split
          body = arr[3..-1].join(' ').gsub(/\\r\\n/, '')
          body.gsub!(/^:/,'')
          incomingAddress = arr[2].chomp
          username = arr[0].split('!')[0].sub!(/:/,'')
          if incomingAddress == @ircnick
            incomingAddress = username
          end
          ret = respondToChat(body, username, 'IRC', incomingAddress )
        end
        if ret
          ret.split("\n").each do |bodyLine|
            ircConn.puts("PRIVMSG #{incomingAddress} :#{bodyLine}")
            sleep 0.1
          end
          logOut "I said: #{ret}" unless ret.empty?
        end
      end
    rescue
      #do nothing here
    end

    #PingLogic
    if Time.now - lastPing > 120
      ircConn.puts("PING #{@ircServer}")
      sleep 0.5
      begin
        msg = ircConn.read_nonblock(1000000)
        logOut "Ping message #{msg}", 1
      rescue Exception => e
        logOut "Ping failed with #{e}"
        ircConn = connIrc
      end
      lastPing = Time.now
    end

    #Ping before we send
    until @ircQueue.empty?
      msgObj = @ircQueue.pop
      msgObj['msg'].split("\n").each do |bodyLine|
        ircConn.puts("PRIVMSG #{msgObj['dst']} :#{bodyLine}")
        sleep 0.1
      end
    end
    if ircConn.closed?
      ircConn = connIrc
    end
    sleep 1
  end

end
