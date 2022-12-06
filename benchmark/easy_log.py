from benchmark.logs import ParseError, LogParser

''' Print a summary of the logs '''
try:
    print(LogParser.chop_process('./logs', faults='?').result())
except ParseError as e:
    pass
