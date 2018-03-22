import logging
logging.basicConfig(filename='garpr.log',level=logging.ERROR)
logger = logging.getLogger('garpr')
logger.setLevel(logging.DEBUG)
logger.info('logging setup. log file is ./garpr.log');