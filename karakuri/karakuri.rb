require 'mongo'
require 'yajl'
require 'time'
require 'thread'
require 'jira'

#Borrow the trafficbot init
require_relative '../support-bot/lib/init-functions.rb'
require_relative "options.rb"

passedArgs = AutoOptParse.parse(ARGV)

@jirausername = nil
@jirapassword = nil
@jiraserver = 'https://jira.mongodb.org/'

@loggingQueue = Queue.new
#@workflow = nil
#@key = nil
@demo = passedArgs.demo
@logLevel = 0
@dbURI = "mongodb://localhost:27017/support"
@dbConnOpts = {:pool_size => 5}

logThr = Thread.new { loggingThread(passedArgs.log_file) }

readSteeringFile("../support-bot/conf/trafficbot.conf")

options = {
    :username => @jirausername,
    :password => @jirapassword,
    :site     => @jiraserver,
    :context_path => '',
    :auth_type => :basic,
    :ssl_verify_mode => OpenSSL::SSL::VERIFY_NONE
}

client = JIRA::Client.new(options)
db = Mongo::MongoClient.from_uri(@dbURI,@dbConnOpts).db('support')

logOut "Started run with file #{passedArgs.file}"

unless @demo
  p "LIVE MODE"
  logOut "Loaded and running live"
end

def loadWorkflow (file)
	json = File.read(file)
	return Yajl::Parser.parse(json)["workflow"]
end

def timePassed(db, key)
	return Time.now.to_i - key['jira']["fields"]['updated'].to_i
end

def haveDone? (db, key, action)
	return db.collection("karakuri").find_one({"key" => key, "actions_taken"=>action})
end

def prerequsMet(db, key, prereqs)
	done = db.collection("karakuri").find_one({"key" => key})
	#Issue doesnt exist
	if done == nil
		return false
	end
    unless done.include? "actions_taken"
        return false
    end
	list = done["actions_taken"]
	prereqs.each do |prereq|
		unless list.include? prereq
			return false
		end
	end
	return true
end

def userNotResponded(db, key)
	key["jira"]["fields"]["comment"]["comments"].each do |comment|
		unless isMongoDB? comment["author"]["emailAddress"]
			return false
		end
	end
	return true
end

def isMongoDB?(username)
	if username.end_with? "@10gen.com", "@mongodb.com"
		return true
	end
	return false
end

def userInformedOfTicket(db, key)
	if userNotResponded(db, key)
		if key["jira"]["fields"]["customfield_10030"] != nil || !isMongoDB?(key["jira"]["fields"]["assignee"]["emailAddress"]) || !isMongoDB?(key["jira"]["fields"]["reporter"]["emailAddress"])
			return true
		end
	end
	return false
end

def smartWorkflowTransiton(client, key, trans_name)
	available_transitions = client.Transition.all(:issue => key)
	available_transitions.each do |t|
		if t.name == trans_name
			return t.id
		end
	end
	return false
end

def wasLastMe?(db, key)
  lastComment = key["jira"]["fields"]["comment"]["comments"][-1]
  if lastComment["emailAddress"] = "trafficbot@10gen.com"
    return true;
  end
end

def shouldI?(db, key, name)
  #If i'm interractive ask someone. Don't check the DB
  if passedArgs.mode == "i"
    p "Would you like to execute #{name} for #{key}?"
    response = gets
    response.downcase
    until "yn".include? response[0]
      p "Sorry, i didnt understand that. Would you like to execute #{name} for #{key} [y/n]?"
      response = gets
      response.downcase
    end
    if response[0] == "y"
      # We will take an action here, so remove the "tbd"
      db.collection("karakuri").update({"key" => key}, {"$pull" => { "actions_wanted" => name}})
      return true
    else
      return false
    end
  end
  #If force flag is on - just do whatever
  if passedArgs.force == true
    return true
  end

  #We aren't on force and we aren't interractive, we now should check
  doc = db.collection("karakuri").find_one({"key" => key})

  #No doc? we should add one
  if doc == nil
    db.collection("karakuri").update({"key" => key}, {"$addToSet" => { "actions_wanted" => name}},{:upsert => true})
    return false
  end
  #Is a doc, are we okay to send?
  if doc.include? "actions_approved" and doc["actions_approved"].include? name
    return true
  else
    db.collection("karakuri").update({"key" => key}, {"$addToSet" => { "actions_wanted" => name}},{:upsert => true})
    return false
  end

end

def labelsGood?(db, key)
  db.collection("issues").find({'jira.key'=> key["key"]})
end

def workflowIteration(db, client, passedArgs)
    workflow = loadWorkflow(passedArgs.file)

    if passedArgs.mode == "i"
        limit = 0
    else
        limit = passedArgs.limit
    end

	processesedThisLap = []
	workflow.each do |wItem|
        logOut "Considering #{wItem["name"]}..."
		query = wItem["base_filter"]
		db.collection("issues").find(query, {:limit => limit}).each do |key|
			unless processesedThisLap.include? key['jira']["key"]
				unless haveDone?(db, key['jira']["key"], wItem["name"])
					if wItem["time_passed"] < timePassed(db, key)
						go = false

            #Have we met all the prerequisites?
						if wItem.has_key? "workflowPrereq" 
							if prerequsMet(db, key['jira']["key"], wItem["workflowPrereq"])
                                go = true
							end
						else
							go = true
            end
            if go
              go = shouldI?(db, key['jira']["key"], wItem["name"], passedArgs)
            end
						if go
							begin
								res = methods.send(wItem["postFilterFunction"], db, key)
								if res 
									logOut "Workflow #{wItem["name"]} triggered for #{key['jira']["key"]}"
									unless @demo
										ir = client.Issue.find(key['jira']["key"])
										c = ir.comments.build
										out = c.save(wItem["workflow_comment"])
										unless out
											logOut "Writing comment on #{key['jira']["key"]} for action #{wItem["workflow_comment"]}"
										end
										t_id = smartWorkflowTransiton(client, ir, wItem["workflow_action"])
										if t_id != nil
											t = ir.transitions.build
											if wItem["workflow_action"] == "Resolve Issue"
												out = t.save("transition" => {"id" => t_id}, "fields" => {"resolution" => {"name" => "Incomplete"}, "labels" => [ "cbb" ]})
											else	
												out = t.save("transition" => {"id" => t_id})
											end
											unless out
												logOut "Failed workflow transition on #{key['jira']["key"]} for #{wItem["workflow_action"]}"
											end
                    end
                    db.collection("karakuri").update({"key"=>key['jira']["key"]},{"$push" => {"actions_taken" => wItem["name"]}, "$pull" => { "actions_approved" => wItem["name"]}},{:upsert => true})
									end
									processesedThisLap.push(key['jira']["key"])
								end
							rescue => e
								logOut "Caught exception: #{e} while processing #{wItem["name"]} on #{key['jira']["key"]}"
								logOut e.backtrace
							end
						end
					end
				end
			end
		end
	end
end

workflow = loadWorkflow(passedArgs.file)

#Run as a daemon
while passedArgs.mode == "d"
  workflowIteration(db, client, passedArgs)
	sleep 60
end

#Run one instance before leaving in cron mode
if passedArgs.mode == "c"
  workflowIteration(db, client, passedArgs)
end

#Run interractively. Ick
if passedArgs.mode == "i"
  response = ""
  p "I've got #{passedArgs.file} as your chosen file. Is that correct?"
  response = gets
  response.downcase

  #HAX!
  until "yn".include? response[0]
    p "Sorry, i didnt understand that. Is #{passedArgs.file} the correct file [y/n]?"
    response = gets
    response.downcase
  end
  if response[0] == "n"
    p "What file would you like instead?"
    response = gets
    until File.exist? response.chomp!
      p "Sorry, that file does not exist. Please enter a workflow filename"
      response = gets
    end
    workflow = loadWorkflow(passedArgs.file)
  end
  #We check when running interactive, so no need for the Demo flag
  @demo = false
  #No limit when running interactive
  workflowIteration(db, client, passedArgs)
end
