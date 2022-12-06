from benchmark.logs import ParseError, LogParser
from benchmark.utils import Print
from benchmark.remote import BenchError

''' Print a summary of the logs '''
try:
    print(LogParser.chop_process('./logs', faults='?').result())
except ParseError as e:
    Print.error(BenchError('Failed to parse logs', e))
