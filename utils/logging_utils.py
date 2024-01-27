import logging
import logging.config
import sys

LOGGING_LINE_FORMAT = "%(message)s"
LOGGING_DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"


class MlflowLoggingStream:
    """
    A Python stream for use with event logging APIs throughout MLflow (`eprint()`,
    `logger.info()`, etc.). This stream wraps `sys.stderr`, forwarding `write()` and
    `flush()` calls to the stream referred to by `sys.stderr` at the time of the call.
    It also provides capabilities for disabling the stream to silence event logs.
    """

    def __init__(self):
        self._enabled = True

    def write(self, text):
        if self._enabled:
            sys.stderr.write(text)

    def flush(self):
        if self._enabled:
            sys.stderr.flush()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value


MLFLOW_LOGGING_STREAM = MlflowLoggingStream()


def disable_logging():
    """
    Disables the `MlflowLoggingStream` used by event logging APIs throughout MLflow
    (`eprint()`, `logger.info()`, etc), silencing all subsequent event logs.
    """
    MLFLOW_LOGGING_STREAM.enabled = False


def enable_logging():
    """
    Enables the `MlflowLoggingStream` used by event logging APIs throughout MLflow
    (`eprint()`, `logger.info()`, etc), emitting all subsequent event logs. This
    reverses the effects of `disable_logging()`.
    """
    MLFLOW_LOGGING_STREAM.enabled = True


def _configure_mlflow_loggers(root_module_name):
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "mlflow_formatter": {
                    "format": LOGGING_LINE_FORMAT,
                    "datefmt": LOGGING_DATETIME_FORMAT,
                },
            },
            "handlers": {
                "mlflow_handler": {
                    "formatter": "mlflow_formatter",
                    "class": "logging.FileHandler",
                    "filename": "/usr/local/etc/audit_log.log",
                },
            },
            "loggers": {
                root_module_name: {
                    "handlers": ["mlflow_handler"],
                    "level": "DEBUG",
                    "propagate": False,
                },
            },
        }
    )


def eprint(*args, **kwargs):
    print(*args, file=MLFLOW_LOGGING_STREAM, **kwargs)  # pylint: disable=print-function