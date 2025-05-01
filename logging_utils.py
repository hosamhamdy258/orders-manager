import atexit
import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue

global_queue = Queue(-1)


class LoggingQueue(QueueHandler):
    """Custom log queue that ensures dynamic handlers and graceful shutdown."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, queue=None, handlers=[], respect_handler_level=True):
        if queue == None:
            queue = global_queue
        super().__init__(queue)
        self.handler_map = handlers
        self.respect_handler_level = respect_handler_level

    def start_listener(self):
        resolved = {}
        for logger_name, handler_names in self.handler_map.items():
            resolved[logger_name] = [handler for handler in (logging.getHandlerByName(name) for name in handler_names) if handler]

        self.listener = ListenerQueue(self.queue, resolved, respect_handler_level=self.respect_handler_level)


class ListenerQueue(QueueListener):
    def __init__(self, queue, handlers, respect_handler_level=True):
        super().__init__(queue, handlers, respect_handler_level=respect_handler_level)
        self.handlers = handlers
        self.start()
        atexit.register(self.stop)

    def handle(self, record):
        record = self.prepare(record)
        handlers = self.handlers.get(record.name, None)
        if handlers:
            for handler in handlers:
                if not self.respect_handler_level:
                    process = True
                else:
                    process = record.levelno >= handler.level
                if process:
                    handler.handle(record)
