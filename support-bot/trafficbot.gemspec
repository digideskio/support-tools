Gem::Specification.new do |s|
  s.name        = 'trafficbot'
  s.version     = '0.0.0'
  s.date        = '2014-02-18'
  s.summary     = "The Trafficbot!"
  s.description = "A simple hello world gem"
  s.authors     = ["David Hows"]
  s.email       = 'david.hows@mongodb.com'
  s.homepage    =
      'http://github.com/daveh86/support-bot'
  s.files = Dir['lib/   *.rb'] + Dir['bin/*']
  s.files += Dir['[A-Z]*'] + Dir['test/**/*']
  s.files.reject! { |fn| fn.include? "CVS" }
  s.add_runtime_dependency('mongo')
  s.add_runtime_dependency('jira-ruby')
  s.add_runtime_dependency('yajl-ruby')
  s.add_runtime_dependency('time-lord')
  s.add_runtime_dependency('xmpp4r')
end