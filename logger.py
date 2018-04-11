import sys
import logging
logging.basicConfig(filename='garpr.log',level=logging.ERROR)
logger = logging.getLogger('garpr')
logger.setLevel(logging.DEBUG)
logger.info('logging setup. log file is ./garpr.log');

'''
errors = logging.getLogger('errors')

errors.setLevel(logging.ERROR)
'''

'''
#ALWAYS WRITE UNHANDLED EXCEPTIONS TO THE LOG
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception
'''