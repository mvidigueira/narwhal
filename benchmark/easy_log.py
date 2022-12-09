from benchmark.logs import ParseError, LogParser
import sys

''' Print a summary of the logs '''
try:
    n = len(sys.argv)
    if n < 2:
        print("Must provide the logs directory path")
    else:
        print(LogParser.chop_process(sys.argv[1], faults='?').result())
except ParseError as e:
    pass
