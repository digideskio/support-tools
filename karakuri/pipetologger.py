class PipeToLogger:
    def __init__(self, logger):
        self.logger = logger

    def write(self, s):
        self.logger.info(s.strip())
