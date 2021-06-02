class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class NoDataError(Error):
    """Raised when there is not enough valid data for the given runs.
    Attributes:
        message -- explanation of the error
        runlst -- list of runs
    """
    def __init__(self,runlst,message="Not enough valid data for the given runs"):
        self.runlst = runlst
        self.message = "{message}, runs: {runs}.".format(message=message,runs=self.runlst)
        #super(Exception,self).__init__(self.message)
    
class TriggerModeNoneError(Error):
    """Raised when the trigger mode is None for a given run.
    Attributes:
        message -- explanation of the error
        runlst -- runs number
    """
    def __init__(self,run,message="The trigger mode is None"):
        self.run = run
        self.message = "{message}, run: {runs}.".format(message=message,runs=self.run)

class NoValidTriggersError(Error):
    """Raised when there are no valid triggers specified
    Attributes:
        message -- explanation of the error
    """
    def __init__(self,message="There were no valid triggers specified"):
        self.message = "{message}".format(message=message)
