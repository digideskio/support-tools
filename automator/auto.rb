require 'mongo'
require 'yajl'
require 'time'
require 'thread'
require 'jira'

#Borrow the trafficbot init
require_relative '../lib/init-functions.rb'
require_relative "options.rb"

passedArgs = AutoOptParse.parse(ARGV)

#Main init
@dbURI = "mongodb://localhost:27017/support"
@dbConnOpts = {:pool_size => 5}

@jirausername = nil
@jirapassword = nil
@jiraserver = 'https://jira.mongodb.org/'

@loggingQueue = Queue.new
@workflow = nil
@key = nil
@demo = passedArgs.demo
unless @demo
  p "LIVE MODE"
end

readSteeringFile("../conf/trafficbot.conf")

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

def loadWorkflow (file)
	json = File.read(file)
	return Yajl::Parser.parse(json)["workflow"]
end

def timePassed(db, key)
	return Time.now.to_i - key["fields"]['updated'].to_i
end

def haveDone? (db, key, action)
	return db.collection("automation").find_one({"key" => key, "actions_taken"=>action})
end

def prerequsMet(db, key, prereqs)
	done = db.collection("automation").find_one({"key" => key})
	#Issue doesnt exist
	if done == nil
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
	key["fields"]["comment"]["comments"].each do |comment|
		unless comment["author"]["emailAddress"].end_with?  "@10gen.com", "@mongodb.com"
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
		if key["fields"]["customfield_10030"] != nil || !isMongoDB?(key["fields"]["assignee"]["emailAddress"]) || !isMongoDB?(key["fields"]["reporter"]["emailAddress"])
			return true;
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

def workflowIteration(db, client, workflow, limit)
	processesedThisLap = []
	workflow.each do |wItem|
		query = wItem["base_filter"]
		db.collection("issues").find(query, {:limit => limit}).each do |key|
			unless processesedThisLap.include? key["key"]
				unless haveDone?(db, key["key"], wItem["name"])
					if wItem["time_passed"] < timePassed(db, key)
						go = false
						if wItem.has_key? "workflowPrereq" 
							if prerequsMet(db, key["key"], wItem["workflowPrereq"])
							end
						else
							go = true
            end
            #Interractive check. Ewwwww
            if passedArgs.mode == "i" && go == true
              p "Would you like to execute #{wItem["name"]} for #{key["key"]}?"
              response = ""
              response = gets
              until "yn".include? response[0]
                p "Sorry, i didnt understand that. Would you like to execute #{wItem["name"]} for #{key["key"]} [y/n]?"
                response = gets
                response.downcase
              end
              if response[0] == "y"
                go = true
              else
                go = false
              end
            end
						if go
							begin
								res = methods.send(wItem["postFilterFunction"], db, key)
								if res 
									p "Workflow #{wItem["name"]} triggered for #{key["key"]}"
									unless @demo
										ir = client.Issue.find(key["key"])
										c = ir.comments.build
										out = c.save(wItem["workflow_comment"])
										unless out
											p "Failed action #{wItem["workflow_comment"]}"
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
												p "Failed action #{wItem["workflow_action"]}"
											end
										end
										db.collection("automation").update({"key"=>key["key"]},{"$push" => {"actions_taken" => wItem["name"]}},{:upsert => true})
									end
									processesedThisLap.push(key["key"])
								end
							rescue => e
								p e
								p e.backtrace
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
  workflowIteration(db, client, workflow, passedArgs.limit)
	sleep 60
end

#Run one instance before leaving in cron mode
if passedArgs.mode == "c"
  workflowIteration(db, client, workflow, passedArgs.limit)
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
  workflowIteration(db, client, workflow, 0)
end