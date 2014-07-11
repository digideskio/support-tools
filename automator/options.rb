require 'optparse'
require 'optparse/time'
require 'ostruct'


class AutoOptParse

  MODES = %w[i d c]
  MODE_ALIASES = {"I" => "i", "D" => "d", "C" => "c"}
  #
  # Return a structure describing the options.
  #
  def self.parse(args)
    # The options specified on the command line will be collected in *options*.
    # We set default values here.
    options = OpenStruct.new
    options.mode = "c"
    options.demo = true
    options.file = "workflow.json"
    options.verbose = false
    options.limit = 0

    opt_parser = OptionParser.new do |opts|
      opts.banner = "Usage: auto.rb [options]"

      opts.separator ""
      opts.separator "Specific options:"

      # Mandatory argument.
      mode_list = (MODE_ALIASES.keys + MODES).join(',')
      opts.on("-m", "--mode [MODE]", MODES, MODE_ALIASES, "Select mode",
              "  ([i]nteractive|[d]aemon|[c]ron)") do |mode|
        options.mode = mode
      end

      opts.on("-l", "--live",
              "Run automator in live mode. Has no effect in interactive mode") do |live|
        options.demo = false
      end

      opts.on("-f", "--file [workflow file]",
              "Select the file to get a workflow from. Default is workflow.json") do |file|
        unless File.exist? file
          p "Error, specified file does not exist"
          exit
        end
        options.file = file
      end

      opts.on("-n", "--limit [n]",
              "Max number of object to update this run. Has no effect in interactive mode") do |n|
        options.limit = n
      end


      opts.on("-v", "--[no-]verbose", "Run verbosely") do |v|
        options.verbose = v
      end

      opts.separator ""
      opts.separator "Common options:"

      # No argument, shows at tail.  This will print an options summary.
      # Try it and see!
      opts.on_tail("-h", "--help", "Show this message") do
        puts opts
        exit
      end
    end
    opt_parser.parse!(args)
    options
  end  # parse()

end  # class OptparseExample