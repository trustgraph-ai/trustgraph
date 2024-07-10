
from enum import Enum
import _pulsar

class LogLevel(Enum):
    DEBUG = 'debug'
    INFO = 'info'
    WARN = 'warn'
    ERROR = 'error'

    def __str__(self):
        return self.value

    def to_pulsar(self):
        if self == LogLevel.DEBUG: return _pulsar.LoggerLevel.Debug
        if self == LogLevel.INFO: return _pulsar.LoggerLevel.Info
        if self == LogLevel.WARN: return _pulsar.LoggerLevel.Warn
        if self == LogLevel.ERROR: return _pulsar.LoggerLevel.Error
        raise RuntimeError("Log level mismatch")

