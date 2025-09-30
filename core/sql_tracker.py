import threading
import time
import traceback

from django.conf import settings
from django.db.backends.utils import CursorWrapper
from django.utils.deprecation import MiddlewareMixin

# Global query storage
_thread_queries = threading.local()


def get_thread_queries():
    if not hasattr(_thread_queries, "queries"):
        _thread_queries.queries = []
    return _thread_queries.queries


def reset_thread_queries():
    _thread_queries.queries = []


# Monkey patch to capture queries
original_execute = CursorWrapper.execute
original_executemany = CursorWrapper.executemany


def tracking_execute(self, sql, params=None):
    start_time = time.time()
    try:
        return original_execute(self, sql, params)
    finally:
        end_time = time.time()
        execution_time = end_time - start_time

        # Extract caller stack (skip Django internals, keep app code)
        stack = traceback.format_stack()
        # Keep only relevant lines (skip the last few inside execute itself)
        caller_stack = [line for line in stack[:-2] if "site-packages/django" not in line]

        queries = get_thread_queries()
        queries.append(
            {
                "sql": sql,
                "time": f"{execution_time:.6f}",
                "params": params,
                "stack": caller_stack[-5:],  # last few relevant lines
            }
        )

        print(f"[SQL] {sql} ({execution_time:.6f}s)")
        for line in caller_stack[-5:]:
            print("   ", line.strip())


def tracking_executemany(self, sql, param_list):
    start_time = time.time()
    try:
        return original_executemany(self, sql, param_list)
    finally:
        end_time = time.time()
        execution_time = end_time - start_time

        stack = traceback.format_stack()
        caller_stack = [line for line in stack[:-2] if "site-packages/django" not in line]

        queries = get_thread_queries()
        queries.append(
            {
                "sql": sql,
                "time": f"{execution_time:.6f}",
                "params": f"{len(param_list)} executions",
                "stack": caller_stack[-5:],
            }
        )

        print(f"[SQL-MANY] {sql} ({execution_time:.6f}s)")
        for line in caller_stack[-5:]:
            print("   ", line.strip())


class SqlTracker(MiddlewareMixin):
    def process_request(self, request):
        if settings.DEBUG and getattr(settings, "TRACK_SQL", False):
            # Apply monkey patch
            CursorWrapper.execute = tracking_execute
            CursorWrapper.executemany = tracking_executemany
