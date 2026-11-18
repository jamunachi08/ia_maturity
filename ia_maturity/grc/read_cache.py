"""Read-operation-local reuse; never persist private data or authority in Redis.

Only explicitly scoped read APIs opt in. Writes, commits and rollbacks disable
reuse for the remainder of that scope, including direct database updates.
"""
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps

import frappe


def invalidate():
    state = getattr(frappe.local, "grc_read_cache", None)
    if state is not None:
        state["disabled"] = True
        state["values"].clear()


@contextmanager
def read_scope():
    previous = getattr(frappe.local, "grc_read_cache", None)
    if previous is not None:
        yield
        return
    writes = getattr(frappe.db, "transaction_writes", None)
    transaction_hooks = [getattr(frappe.db, name, None) for name in ("after_commit", "after_rollback")]
    supported = isinstance(writes, int) and all(callable(getattr(hook, "add", None)) for hook in transaction_hooks)
    state = {"values": {}, "disabled": not supported, "db": frappe.db, "writes": writes}
    frappe.local.grc_read_cache = state

    def end_transaction():
        state["disabled"] = True
        state["values"].clear()

    for callbacks in transaction_hooks:
        if callable(getattr(callbacks, "add", None)):
            callbacks.add(end_transaction)
    try:
        yield
    finally:
        state["values"].clear()
        frappe.local.grc_read_cache = previous


def read_request(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        with read_scope():
            return method(*args, **kwargs)
    return wrapped


def read_cached(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        state = getattr(frappe.local, "grc_read_cache", None)
        if state is None or state["disabled"]:
            return method(*args, **kwargs)
        if (state["db"] is not frappe.db or frappe.flags.get("grc_service_write")
                or state["writes"] != getattr(frappe.db, "transaction_writes", None)):
            invalidate()
            return method(*args, **kwargs)
        key = (frappe.local.site, frappe.session.user, method.__module__,
               method.__name__, args, tuple(sorted(kwargs.items())))
        try:
            hash(key)
        except TypeError:
            return method(*args, **kwargs)
        if key not in state["values"]:
            result = method(*args, **kwargs)
            # A nested call may have performed a write and disabled this scope.
            if (state["disabled"] or state["writes"] != getattr(frappe.db, "transaction_writes", None)):
                invalidate()
                return result
            state["values"][key] = deepcopy(result)
        return deepcopy(state["values"][key])
    return wrapped
