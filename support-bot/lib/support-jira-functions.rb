require 'xmpp4r'
require 'xmpp4r/xhtml'

#Function escapeKey
# Used to escape the key so that the partyChat bot wont send the URL message
def escapeKey(key)
  return key.downcase
end
def escapeXML(msg)
  msg = msg.gsub("&","&amp;")
  msg = msg.gsub("<","&lt;")
  msg = msg.gsub(">","&gt;")
  #msg = msg.gsub('""',"&quot;")
  #msg = msg.gsub("'","&apos;")
end

#Function saveState
#Writes the current state (active and review issues) to the stateFile
def saveState
  #If a state file exists, delete it
  if File.exists? @stateFile
    File.delete @stateFile
  end
  msg = ""
  @issues.each_key do |key|
    unless @issues[key][:ex] ^ false
      msg += "#{key}\n"
    end
    if @issues[key][:rv] == 'r'
      msg += "Review #{key}"
      if @issues[key][:lgtms] != nil
        if @issues[key][:lgtms].size > 0
          msg += " #{@issues[key][:lgtms].join(',')}"
        end
      end
      msg+="\n"
    end
    if @issues[key][:rv] == 'n'
      msg += "NW #{key}\n"
    end
  end
  fh = File.open(@stateFile, 'w+')
  fh.write(msg)
  fh.close
end

#Function loadState
#Loads the current state (active and review issues) from the stateFile
def loadState
  if File.exists? @stateFile
    fh = File.open(@stateFile, 'r')
    fh.each_line do |line|
      if line.start_with? 'NW'
        key = line.split(' ')[1]
        if @issues.has_key? key
          @issues[key][:rv] = 'n'
          @issues[key][:rvt] = Time.now
          @issues[key][:lgtms] = []
        else
          data = {
              :id => nil,
              :p => 3,
              :tc => Time.now,
              :ts => Time.now,
              :new => false,
              :ctr => 0,
              :ex => true,
              :rv => 'n',
              :rvt => Time.now,
              :lgtms => []
          }
          @issues[key] = data
        end
      elsif line.start_with? 'Review'
        key = line.split(' ')[1]
        lgtms = []
        tmp = line.split(' ')[2]
        if tmp != nil
          lgtms = tmp.split(',')
        end
        if @issues.has_key? key
          @issues[key][:rv] = 'r'
          @issues[key][:rvt] = Time.now
          @issues[key][:lgtms] = lgtms
        else
          data = {
              :id => nil,
              :p => 3,
              :tc => Time.now,
              :ts => Time.now,
              :new => false,
              :ctr => 0,
              :ex => true,
              :rv => 'r',
              :rvt => Time.now,
              :lgtms => lgtms
          }
          @issues[key] = data
        end
      else
        key = line.chomp
        if @issues.has_key? key
          @issues[key][:ex] = false
          @issues[key][:ctr] = 3
        end
      end
    end
    File.delete @stateFile
  end
end

#Function soundEffect
# Play a random sound from the "sounds" folder
def soundEffect(key=nil, priority=nil)
  file = ''
  #we have a key and priority, check if that folder exists
  if key!=nil && priority != nil
    cls = key.split('-')[0]
    if Dir.exists?("sounds/#{cls}/#{priority}")
      sounds = Dir.entries("sounds/#{cls}/#{priority}")
      until file.ends_with? '.wav' || sounds.length == 0
        num = rand(sounds.length)
        file = "sounds/#{cls}/#{priority}/#{sounds[num]}"
        sounds.delete_at(num)
      end
    end
  end

  #Fallback to random
  if file == ''
    d =
        if Dir.exists?('sounds')
          sounds = Dir.entries('sounds')
          until file.ends_with? '.wav' || sounds.length == 0
            num = rand(sounds.length)
            file = "sounds/#{sounds[num]}"
            sounds.delete_at(num)
          end
        end
  end

  #If we have a file, play it
  unless file == ''
    logOut("Attempting to play file '#{file}'", 1)
    host_os = RbConfig::CONFIG['host_os']
    case host_os
      when /mswin|msys|mingw|cygwin|bccwin|wince|emc/
        #Windows, do nothing
      when /darwin|mac os/
        `/usr/bin/afplay \"#{file}\" &`
      when /linux/
        system("/usr/bin/aplay \"#{file}\" &")
      when /solaris|bsd/
        #Unix
    end
  end
end

#Function processCommentFTS
#Processes a comment to determine if it is an FTS comment and returns data if so
def processCommentFTS(comment)
  if comment.start_with? 'FTS','*FTS'
    begin
      arr = comment.split(/\n|\n+|;\s+|:\s+|\a|\e|\f|\n|\r|\t/)
      arr.delete_at(0)
      if arr[0].include?('=>') || arr[0].include?('->')
        arr.delete_at(0)
      end
      #return arr.join(' ')
      while arr[0] == ''
        arr.delete_at(0)
      end
      if arr[0] == "WFC"
        return arr[0] + ' ' + arr[1]
      else
        return arr[0]
      end
    rescue
      return 'ERROR: unable to parse FTS comment on this ticket'
    end
  end
  return nil
end

def doFTSSection(db, query, xhtml)
  msg = ""
  db.collection("issues").find(query).each do |issue|
    if xhtml
      msg += "<a href='https://jira.mongodb.org/browse/#{issue["jira"]["key"]}'>#{issue["jira"]["key"]}</a>  "
    else
      msg += "#{issue["jira"]["key"]}  "
    end

    if issue["jira"]["fields"]['customfield_10030']
      if xhtml
        msg += "(#{escapeXML(issue["jira"]["fields"]['customfield_10030']['name'])})  "
      else
        msg += "(#{issue["jira"]["fields"]['customfield_10030']['name']})  "
      end
    end

    commentsArr = db.collection("issues").find_one('jira.key'=>issue["jira"]["key"])["jira"]["fields"]["comment"]["comments"]
    lastComment = commentsArr[-1]['body']
    secondLastComment = nil
    if commentsArr[-2] != nil
      secondLastComment = commentsArr[-2]['body']
    end
    res = processCommentFTS(lastComment)
    if res == nil && secondLastComment != nil
      res = processCommentFTS(secondLastComment)
    end
    #Only add the Msg if there is one
    #Always add a newline
    if xhtml
      msg += escapeXML(res) unless res == nil
      msg += "<br/>"
    else
      msg += res unless res == nil
      msg += "\n"
    end
  end
  return msg
end

#Function doFTSMessage
#Writes the FTS message details
def doFTSMessageChannel(db)
  response = Jabber::Message.new()
  msg = "\n================\nACTIVE\n================\n"
  res = doFTSSection(db, @ftsActive, false)
  msg += res unless res == ""
  msg += "\n================\nWATCH\n================\n"
  res = doFTSSection(db, @ftsWFC, false)
  msg += res unless res == ""
  msg += "\nFor a version of this message in email format with links please send the #!FTS chat message to trafficbot@mongodb.com directly\n"
  return msg
end

#Function doFTSMessage
#Writes the FTS message details
def doFTSMessage(db)
  response = Jabber::Message.new()
  msg = "<br/><b>ACTIVE</b><br/>"
  res = doFTSSection(db, @ftsActive, true)
  msg += res unless res == ""
  msg += "<br/><b>WATCH</b><br/>"
  res = doFTSSection(db, @ftsWFC, true)
  msg += res unless res == ""
  #msg = escapeXML(msg)
  response.set_xhtml_body(msg)
  return response
end

def doWFCMessage(db, username)
  query = @wfcGeneral["$or"] = {"fields.assignee.name" => username, "fields.customfield_10041.name" => username}
  today = Date.new
  msg = "WFC Issues for #{username}, flagged for follow up:\n"
  db.collection("issues").find(query).each do |issue|
    commentsArr = db.collection("issues").find_one('jira.key'=>issue["jira"]["key"])["jira"]["fields"]["comment"]["comments"]
      lastComment = commentsArr[-1]['body']
    dateObj = lastComment.match(/ping (on )?(\d\d\d\d[\/-])?[\d|\d\d][\/-][\d\d|\d]/i)
    if dateObj
      dateNum = dateObj.to_s.split()[-1]
      arr = dateNum.split(/\/|-/)
      myDate = Date.new() - 1
      #We are MM/DD
      if arr.length == 2
        myDate = Date.new(today.year, arr[0].to_i, arr[1].to_i)
      end
      #We have YY/MM/DD
      if arr.length == 3
        myDate = Date.new(arr[0].to_i, arr[1].to_i, arr[2].to_i)
      end
      if myDate >= today
        msg += "#{issue["key"]}\n"
      end
    end
  end
  return msg
end

def doWFCMessageAll(db)
  today = Date.new
  msg = "WFC Issues for all users, flagged for follow up:\n"
  db.collection("issues").find(@wfcGeneral).each do |issue|
    commentsArr = db.collection("issues").find_one('jira.key'=>issue["jira"]["key"])["jira"]["jira"]["fields"]["comment"]["comments"]
    lastComment = commentsArr[-1]['body']
    dateObj = lastComment.match(/ping (on )?(\d\d\d\d[\/-])?[\d|\d\d][\/-][\d\d|\d]/i)
    if dateObj
      dateNum = dateObj.to_s.split()[-1]
      arr = dateNum.split(/\/|-/)
      myDate = Date.new() - 1
      #We are MM/DD
      if arr.length == 2
        myDate = Date.new(today.year, arr[0].to_i, arr[1].to_i)
      end
      #We have YY/MM/DD
      if arr.length == 3
        myDate = Date.new(arr[0].to_i, arr[1].to_i, arr[2].to_i)
      end
      if myDate >= today
        msg += "#{issue["key"]}\n"
      end
    end
  end
  return msg
end

#Return the number of seconds from creation that this nag requires
#These nags are currently only internal SLA for
def slaSchedule(slaInt)
  case slaInt
    when 1
      return 15 * 60
    when 2
      return 30 * 60
    when 3
      return 60 * 60
    when 4
      return 4 * 60 * 60
    when 5
      return 4 * 60 * 60
    else
      logOut "Asked for invalid SLA value of #{slaInt}", 1
  end
  return false
end

#Function slaNagNewIssue
#Does the SLA nagging on new issues
#Times are 30 min prior to SLA and upon break of SLA
def slaNagNewIssue(key)
  msg = nil
  dst = @roomName
  issue = @issues[key]
  #Warn about impending SLA breach 30 minutes prior
  if issue[:exsla] == false
    if Time.now > (issue[:tc] + slaSchedule(issue[:p].to_i) - (30 * 60))
      msg = "Issue #{key} has 30 minutes remaining on its SLA"
      @issues[key][:exsla] = true
    end
  else
    #We have breached the t-30 SLA, next nag is actual SLA
    if Time.now > (issue[:tc] + slaSchedule(issue[:p].to_i))
      msg = "Issue #{key} has just breached its SLA"
      @issues[key][:ex] = true
    end
  end
  @ipcqueue.push({'msg'=>msg, 'dst' => dst}) if msg != nil
end

#Function nagOldIssue (deprecated)
#Does generic nagging on older issues
def nagOldIssue(key)
  issue = @issues[key]
  counter = issue[:ctr]
  msg = nil
  dst = @roomName
  return if counter < 3
  if counter == 3
    msg = "Client responded on issue #{key}. Now waiting on MongoDB response"
  end
  @ipcqueue.push({'msg'=>msg, 'dst' => dst}) if msg != nil
end

# Function doNags
# Function to check if we should nag on the passed in issue.
def doNags(key)
  unless @issues[key][:ex]
    if @silent == false
      @issues[key][:new] ? slaNagNewIssue(key) : nagOldIssue(key)
    end
  end
end

#Function doQueueRead
#Reads if there are any requests via chat. Does things based on the chat requests
def doQueueRead(db)
  begin
    until @chatRequests.empty?
      #Take a message, get the arg
      req = @chatRequests.pop
      array = req.split
      endUser = array.shift.chomp
      protocol = array.shift.chomp
      dst = { 'prot' => protocol, 'recip' => endUser }
      arg = array.shift.chomp
      msg = nil
      case arg
        when 'REVIEW'
          key = array.shift
          if key.include? "HTTP"
            key = key.split("/")[-1]
          end
          #Remove any trailing nasties
          key = key.chomp().chomp(',').chomp('.')

          who = array.shift
          reviewers = []
          array.each do |entry|
            if entry.start_with? '@'
              entry[1..-1].split(',').each do |more|
                if more.start_with? '@'
                  reviewers.push more[1..-1]
                else
                  reviewers.push more
                end
              end
            end
          end
          db.collection("reviews").update({:key=> key},{:key=> key, :done => false, :requested_by =>who, :reviewers=>reviewers},{:upsert => true} )
          if @issues.has_key? key
            @issues[key][:rv] = 'r'
            @issues[key][:rvt] = Time.now
            @issues[key][:lgtms] = []
            @issues[key][:reviewers] = reviewers
          else
            data = {
                :id => nil,
                :p => 3,
                :tc => Time.now,
                :ts => Time.now,
                :new => false,
                :ctr => 0,
                :ex => true,
                :rv => 'r',
                :rvt => Time.now,
                :lgtms => [],
                :reviewers => reviewers
            }
            @issues[key] = data
          end
          msg = "#{who} requested review of #{key}"
          unless reviewers.empty?
            msg += " from #{reviewers.join(', ')}"
          end
          #Broadcast to IRC as well as XMPP
          @ipcqueue.push({'msg'=>msg, 'dst' => @ircRoomName}) if msg != nil
        when 'FIN'
          key = array.shift
          who = array.shift
          if key.include? "HTTP"
            key = key.split("/")[-1]
          end
          if @issues.has_key? key
            @issues[key][:rv] = nil
            msg = "Review of #{key} finalized by #{who}"
            #Broadcast to IRC as well as XMPP
            @ipcqueue.push({'msg'=>msg, 'dst' => @ircRoomName}) if msg != nil
            db.collection("reviews").update({:key=> key},{"$set"=>{"done" => true, :marked_by => who}})
          end
        when 'NEEDSWORK'
          key = array.shift
          who = array.shift
          if key.include? "HTTP"
            key = key.split("/")[-1]
          end
          if @issues.has_key? key
            @issues[key][:rv] = 'n'
            @issues[key][:lgtms] = []
            msg = "Review of #{key} set to 'needs work' by #{who}"
            #Broadcast to IRC as well as XMPP
            @ipcqueue.push({'msg'=>msg, 'dst' => @ircRoomName}) if msg != nil
            db.collection("reviews").update({:key=> key},{"$set"=>{"done" => "needs work", :marked_by => who}})
          end
        when 'LGTM'
          key = array.shift
          who = array.shift
          if key.include? "HTTP"
            key = key.split("/")[-1]
          end
          if @issues.has_key? key
            @issues[key][:lgtms].push who
            @issues[key][:lgtms].uniq!
            msg = "Issue #{key} LGTM'd by #{who}"
            #Broadcast to IRC as well as XMPP
            @ipcqueue.push({'msg'=>msg, 'dst' => @ircRoomName}) if msg != nil
            db.collection("reviews").update({:key=> key},{"$push" => { :lgtms => who}})
          end
        when 'SAVESTATE'
          saveState
          msg = "State Saved"
        when 'LOADSTATE'
          loadState
          if dst['recip'] != 'nobody'
            msg = "State Loaded"
          end
        when 'IGNORE'
          key = array.shift
          if @issues.has_key? key
            @issues[key][:ex] = true
            msg = "Issue #{key} added to ignore list"
          end
        when 'ACTIVE'
          key = array.shift
          if @issues.has_key? key
            @issues[key][:ex] = false
            @issues[key][:ctr] = 3
            msg = "Issue #{key} added to active list"
          end
        when 'LIST'
          doIgn = false
          if !array.empty? && array[0] == 'IGNORED'
            doIgn = true
          end
          if doIgn
            msg = "List of Ignored issues:\n"
          else
            msg = "List of Active issues:\n"
          end
          @issues.each_key do |key|
            #Xor Bitches
            unless @issues[key][:ex] ^ doIgn
              msg += "#{escapeKey(key)}\n"
            end
            if @issues[key][:rv] == 'r'
              msg += "Review "
              unless @issues[key][:warned] == nil || @issues[key][:warned] == false
                msg += "*"
              end
              msg += escapeKey(key)
              if @issues[key][:reviewers] != nil
                if @issues[key][:reviewers].size > 0
                  msg += " (by #{@issues[key][:reviewers].join(',')})"
                end
              end
              if @issues[key][:lgtms] != nil
                if @issues[key][:lgtms].size > 0
                  msg += " LGTMs: #{@issues[key][:lgtms].join(',')}"
                end
              end
              msg+="\n"
            end
            if @issues[key][:rv] == 'n'
              msg += "Needs work #{escapeKey(key)}\n"
            end
          end
        when 'SOUNDCHECK'
          soundEffect
          msg = "Soundcheck Performed\n"
        when 'FTS'
          msg = "Performing FTS. This may take some time."
          Thread.new(){
            response = ""
            begin
              if (dst['recip'].include? @partychatdomain) || dst['prot'] == "IRC"
                response = doFTSMessageChannel(db)
              else
                response = doFTSMessage(db)
              end
            rescue => e
              logOut "Error in processing thread: #{e}"
              logOut "backtrace: #{e.backtrace}"
              response = "Error in processing FTS #{e}"
            end
            @ipcqueue.push({'msg'=>response, 'dst' => dst}) if msg != nil
          }
        when 'WFC'
          msg = "Performing WFC. This may take some time."
          who = array.shift
          Thread.new(){
            response = ""
            begin
              (who == nil) ? response = doWFCMessageAll(db) : response = doWFCMessage(db, who)
            rescue => e
              logOut "Error in processing thread: #{e}"
              logOut "backtrace: #{e.backtrace}"
              response = "Error in processing WFC #{e}"
            end
            @ipcqueue.push({'msg'=>response, 'dst' => dst}) if response != nil
          }
      end
      @ipcqueue.push({'msg'=>msg, 'dst' => dst}) if msg != nil
    end
  rescue => e
    logOut "Error in processing thread: #{e}"
    logOut "backtrace: #{e.backtrace}"
  end
end

def checkForFinalized(db)
  @issues.each_key do |key|
    if @issues[key][:rv]
      begin
        if @issues[key][:warned] == nil || @issues[key][:warned] == false
          ir = db.collection("issues").find_one('jira.key'=>key)
            status = ir["jira"]["fields"]["status"]["id"]
          lastComment = ir["jira"]["fields"]["comment"]['comments'][-1]
          # Confirm that there is a comment on the issue
          unless lastComment == nil
            if (!lastComment.has_key? "visibility") && (!['1','3'].include? status)
              @chatRequests.push("#{@defaultXMPPRoom} XMPP FIN #{key} Auto:pushed")
              @chatRequests.push("#{@supportIRCChan} IRC FIN #{key} Auto:pushed")
            end
          end
        end
      rescue => e
        logOut "Error in processing autocomplete #{key} - #{e}"
        logOut "Backtrace: #{e.backtrace}"
        if @issues[key][:warned] == nil || @issues[key][:warned] == false
          @issues[key][:warned] = true
          @ipcqueue.push({'msg'=>"Unable to find issue '#{key}' for auto finalize", 'dst' => @roomName})
          @ipcqueue.push({'msg'=>"Unable to find issue '#{key}' for auto finalize", 'dst' => @ircRoomName})
        end
        return
      end
    end
  end
end

# Function - readAndUpdateJira
# Will read from the Jira REST API using the given client and update the global hash of current issues in the support CS Queue
# Has an optional "init" value which lets you specify if you want to be alerted
def readAndUpdateJiraCS(db,query,init = false)

  #Set the Current TS for this lap
  time = Time.now

  #Compare the current List of issues to the old, update if needed
  db.collection("issues").find(query).each do |issue|
    begin
      unless @issues.has_key? issue["jira"]["key"]
        msg = ""
        #Issue ID, Priority, timeCreated, currentTime, new or old, counter of times seen, excluded from nagging?, slabreach nag done?, review needed?
        data = {
            id: issue["jira"]["id"],
            p: issue["jira"]["fields"]['priority']['id'],
            tc: issue["jira"]["fields"]['created'],
            ts: time,
            new: false,
            ctr: 0,
            ex: false,
            exsla: false,
            rv: nil,
            rvt: nil
        }

        #New Issue or returning old issue?
        if issue["jira"]["fields"]['created'].to_i >= (Time.now.to_i - (@jiraInterval*4))
          msg = "New #{issue["jira"]["fields"]['priority']['name'].split()[0]} - #{issue["jira"]["fields"]['reporter']['displayName']}"
          if issue["jira"]["fields"]['customfield_10030']
            msg += " from #{issue["jira"]["fields"]['customfield_10030']['name']}"
          end
          msg += " created #{issue["jira"]["key"]}: #{issue["jira"]['fields']['summary']}"
          data[:new] = true
          if @soundOn
            begin
              soundEffect(issue["jira"]["key"], issue["jira"]["fields"]['priority']['name'].split()[0])
            rescue => e
              logOut "Error playing soundEffect: #{e}"
            end
          end
        end

        if init
          data[:ex] = true
        else
          @ipcqueue.push({'msg'=>msg, 'dst' => @roomNameNewIssue}) if msg != nil
          @ipcqueue.push({'msg'=>msg, 'dst' => @ircNameNewIssue}) if msg != nil
        end
        @issues[issue["jira"]["key"]] = data
      end
      @issues[issue["jira"]["key"]][:ts] = time
      @issues[issue["jira"]["key"]][:ctr] += 1
    rescue => e
      logOut "Error in processing thread: #{e}"
      logOut "Backtrace: #{e.backtrace}"
      logOut issue["jira"]["key"]
    end
  end

  #Remove Old issues (assigned ones)
  @issues.each_key do |key|
    if @issues[key][:rv]
      @issues[key][:ts] = time
      @issues[key][:ctr] += 1
    end
    if @issues[key][:ts] != time
      unless @issues[key][:proactive]
        logOut "Issue #{key} was removed from register", 1
        @issues.delete(key)
      end
    else
      doNags(key)
    end
  end
end #readAndUpdateJiraCS

#Checks for and alerts when there are new proactive tickets
def checkNewProactive(db)
  #Set the Current TS for this lap
  time = Time.now

  #Compare the current List of issues to the old, update if needed
  db.collection("issues").find({"jira.fields.issuetype.id" => "23"}).each do |issue|
    begin
      unless @proactiveAlertsSent.include? issue["key"]
        comments = issue["jira"]["fields"]["comment"]["comments"]
        assignee = issue["jira"]["fields"]["assignee"]
        if assignee == nil
          alerted = false
          comments.each do |comment|
            unless comment["author"]["emailAddress"].end_with? "@10gen.com", "@mongodb.com"
              time = comment["created"]
              if alerted == false && ! @issues.has_key?(issue["jira"]["key"])
                if time.to_i >= (Time.now.to_i - (@jiraInterval*4))
                  if @soundOn
                    begin
                      soundEffect(issue["jira"]["key"], issue["jira"]["fields"]['priority']['name'].split()[0])
                    rescue => e
                      logOut "Error playing soundEffect: #{e}", 1
                    end
                  end
                  data = {
                      id: issue["jira"]["id"],
                      p: issue["jira"]["fields"]['priority']['id'],
                      tc: issue["jira"]["fields"]['created'],
                      ts: time,
                      new: false,
                      ctr: 0,
                      ex: false,
                      exsla: false,
                      rv: nil,
                      rvt: nil,
                      proactive: false
                  }
                  @issues[issue["jira"]["key"]] = data
                  msg = "Proactive issue #{issue["jira"]["key"]} has had customer response"
                  @proactiveAlertsSent.push issue["jira"]["key"]
                  @ipcqueue.push({'msg'=>msg, 'dst' => @roomNameNewIssue}) if msg != nil
                  @ipcqueue.push({'msg'=>msg, 'dst' => @ircNameNewIssue}) if msg != nil
                end
                alerted = true
              end
            end
          end
        end
      end
    rescue => e
      logOut "Error in processing thread: #{e}"
      logOut "Backtrace: #{e.backtrace}"
      logOut issue["jira"]["key"]
    end
  end
  @issues.each_key do |key|
    if @issues[key][:proactive]
      ir = db.collection("issues").find_one('jira.key'=>key)
      status = ir["jira"]["fields"]["status"]["id"]
      assignee = ir["jira"]["fields"]["assignee"]
      unless status == "10005" || status == "10006" || assignee != nil
        logOut "Issue #{key} was removed from register", 1
        @issues.delete(key)
      end
    end
  end
end

#Function mainJiraThread
# Main thread for Jira polling
def mainJiraThread(db)
  @proactiveAlertsSent = []
  counter = 1
  while true
    if (counter % @jiraInterval) == 0
      doQueueRead(db)
      checkForFinalized(db)
      readAndUpdateJiraCS(db, @jiraquery)
      checkNewProactive(db)
    else
      doQueueRead(db)
    end
    if (counter % (60 * 20)) == 0
      reviewCount = 0
      @issues.each_key do |key|
        if @issues[key][:rv] == 'r'
          reviewCount+=1
        end
      end
      if reviewCount > 0
        @ipcqueue.push({'msg'=>"There are currently #{reviewCount} reviews in the queue", 'dst' => @roomName})
      end
      counter = 0
    end
    counter += 1
    sleep 1
  end
end