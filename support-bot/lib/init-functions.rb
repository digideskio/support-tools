#Function logOut
# Function to write to the logging queue, this should be used instead of a print
def logOut(s)
  @loggingQueue.push(s.to_s)
end

#Function loggingThread
# Async Logging output thread
def loggingThread(filename = 'trafficbot.log')
  f = File.open(filename, 'a')
  while true
    ostr = Time.now.to_s + " " + @loggingQueue.pop().to_s
    #p ostr
    f.puts ostr
    f.flush
  end
end

#Function readSteeringFile
# Reads a steering file to grab the username and password and other things need to know about
def readSteeringFile(file = 'conf/trafficbot.conf')
  if file == nil || (! File.exists? file)
    file = 'conf/trafficbot.conf'
  end

  logOut "Reading from steeringfile - #{file}"
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
      when 'soundonly'
        @soundOnlyMode = arr[1].chomp
      when 'soundon'
        @soundOn = arr[1].chomp
      when 'daemon'
        @daemon = arr[1].chomp
    end
  end
  if ! (@jirausername||@jirapassword||@jabberusername||@jabberpassword)
    logOut 'Error: Missing critical variables please define them in the steering file'
  end
  if @soundOnlyMode == nil || @soundOnlyMode == 'true'
    @soundOnlyMode = true
  end
  if @soundOnlyMode == 'false'
    @soundOnlyMode = false
  end
  if @soundOn == nil || @soundOn == 'true'
    @soundOn = true
  end
  if @soundOn == 'false'
    @soundOn = false
  end

  #Daemon loading options for auto
  if @daemon == nil || @daemon == 'false'
    @daemon = false
  end
  if @daemon == 'true'
    @daemon = true
  end
end