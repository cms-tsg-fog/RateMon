class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class NoDataError(Error):
    """Raised when there is not enough valid data for the given triggers/runs.
    Attributes:
        message -- explanation of the error
        runlst -- list of runs
    """
    def __init__(self,runlst,message="Not enough valid data for the given runs"):
        self.runlst = runlst
        self.message = "{message}, runs: {runs}.".format(message=message,runs=self.runlst)
        #super(Exception,self).__init__(self.message)
    
