"""
DICOM metadata extractor logger.
Provides structured logging using structlog,
configuration. Supports both FunctionGraph and CCE batch execution modes.
"""

import logging
import sys
import os
import structlog

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
BATCH_JOB_ID = os.environ.get('BATCH_JOB_ID', None)
FUNCTION_NAME = os.environ.get('FUNCTION_NAME', None)
FORMAT = logging.Formatter('"%(created)f - %(pathname)s - %(message)s"')

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


def get_logger(name):
    log = structlog.get_logger(name)
    if BATCH_JOB_ID:
        log.bind(BATCH_JOB_ID=BATCH_JOB_ID)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(FORMAT)
        log.addHandler(console_handler)
    elif FUNCTION_NAME:
        pass
    else:
        log = structlog.get_logger(name)

    log.setLevel(LOGLEVEL)
    return log
