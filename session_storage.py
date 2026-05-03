"""
Per-user session storage backed by NiceGUI's app.storage.user.

Previously this was a single global dict shared by ALL users — meaning
the last person to log in would overwrite everyone else's session.

Now `session_storage` is a proxy object that delegates to the
per-browser, cookie-backed `app.storage.user` dictionary provided
by NiceGUI.  Every import of `session_storage` across the codebase
continues to work via duck-typing (get, pop, __setitem__, etc.).
"""


class _SessionStorageProxy:
    """Dict-like proxy that delegates to NiceGUI's per-user storage.

    NiceGUI's `app.storage.user` is only available inside a request
    context (i.e., inside a @ui.page handler or a UI callback).
    This proxy lazily accesses it on every call so it always reads
    the storage for the *current* user's browser session.

    Falls back to a plain dict when called outside a request context
    (e.g., during module import or in background threads).
    """

    def _store(self):
        try:
            from nicegui import app as _app
            return _app.storage.user
        except Exception:
            # Outside request context — return a throwaway dict so
            # callers don't crash (e.g. during startup imports).
            if not hasattr(self, '_fallback'):
                self._fallback = {}
            return self._fallback

    # ── dict-like interface ──────────────────────────────────────────
    def get(self, key, default=None):
        return self._store().get(key, default)

    def pop(self, key, *args):
        return self._store().pop(key, *args)

    def __getitem__(self, key):
        return self._store()[key]

    def __setitem__(self, key, value):
        self._store()[key] = value

    def __delitem__(self, key):
        del self._store()[key]

    def __contains__(self, key):
        return key in self._store()

    def __iter__(self):
        return iter(self._store())

    def __len__(self):
        return len(self._store())

    def keys(self):
        return self._store().keys()

    def values(self):
        return self._store().values()

    def items(self):
        return self._store().items()

    def update(self, *args, **kwargs):
        return self._store().update(*args, **kwargs)

    def setdefault(self, key, default=None):
        return self._store().setdefault(key, default)

    def __repr__(self):
        try:
            return f"SessionStorageProxy({dict(self._store())})"
        except Exception:
            return "SessionStorageProxy(<no context>)"


session_storage = _SessionStorageProxy()
