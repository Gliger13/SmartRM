import logging

# Initialization logger
logger = logging.getLogger('SmartRM')
console_handler = logging.StreamHandler()

console_format = logging.Formatter('%(message)s')
console_handler.setFormatter(console_format)
console_handler.setLevel(logging.DEBUG)
logger.setLevel(logging.WARNING)
logger.addHandler(console_handler)

if __name__ == '__main__':
    module_logger = logging.getLogger('SmartRM')
    module_logger.debug('Some debug information')
    module_logger.info('Some information')
    module_logger.warning('Some warning')
    module_logger.error('Some error')
    module_logger.critical('Some critical error')