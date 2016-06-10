require 'zmq'

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
    logOut("Attempting to play file '#{file}'")
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

ctx = ZMQ::Context.new(1)
sock = ctx.socket(ZMQ::SUB)
sock.connect("tcp://127.0.0.1")

loop do
	input = sock.recv
	arr = input.split
	soundEffect arr[0], arr[1]
	break if input == "QUIT"
end
