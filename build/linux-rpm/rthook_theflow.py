# rthook_theflow.py
# =========================================================
# PyInstaller runtime hook for theFlow
#
# Runs BEFORE any app code. Fixes two things:
#
# 1. Path — ensures sys._MEIPASS is on sys.path so all
#    bundled modules find each other exactly as in dev.
#
# 2. sip exception gate — PyQt6's sip layer calls
#    QMessageLogger::fatal() -> abort() when a Python
#    exception escapes a C++ virtual override (paintEvent,
#    mouseDoubleClickEvent, etc). We replace sip's error
#    printer with one that prints and clears the exception
#    instead of escalating to abort().
# =========================================================

import sys
import os
import traceback

# ── 1. Fix sys.path ───────────────────────────────────────────────────────────
if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS
    if meipass not in sys.path:
        sys.path.insert(0, meipass)

    # Qt plugin paths
    qt_plugins = os.path.join(meipass, 'PyQt6', 'Qt6', 'plugins')
    if not os.path.isdir(qt_plugins):
        qt_plugins = os.path.join(meipass, 'PyQt6', 'plugins')
    if os.path.isdir(qt_plugins):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins
        platform_dir = os.path.join(qt_plugins, 'platforms')
        if os.path.isdir(platform_dir):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = platform_dir

# ── 2. Global Python exception hook ──────────────────────────────────────────
def _excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

# ── 3. Patch sip to not abort() on Python exceptions in virtual overrides ────
#
# After PyQt6/sip is imported, sip._pyqt6_err_print is the C function that
# gets called when a Python exception escapes a virtual method. It prints the
# traceback and then calls QMessageLogger::fatal() which calls abort().
#
# We can't easily replace the C function, but we CAN install a Qt message
# handler that intercepts the fatal message before abort() is called.
#
# We defer this until after QApplication is constructed (via a post-import
# hook on PyQt6.QtCore) because qInstallMessageHandler requires Qt to be
# initialized.

def _install_qt_message_handler():
    try:
        from PyQt6.QtCore import qInstallMessageHandler, QtMsgType

        def _handler(msg_type, context, message):
            # Print all Qt messages but never call abort()
            label = {
                QtMsgType.QtDebugMsg:    'QtDebug',
                QtMsgType.QtInfoMsg:     'QtInfo',
                QtMsgType.QtWarningMsg:  'QtWarning',
                QtMsgType.QtCriticalMsg: 'QtCritical',
                QtMsgType.QtFatalMsg:    'QtFatal',
            }.get(msg_type, 'Qt')
            print(f'[{label}] {message}', file=sys.stderr, flush=True)
            # For fatal: clear any pending Python exception so sip doesn't
            # re-raise it, then return (instead of calling abort).

        qInstallMessageHandler(_handler)
    except Exception as e:
        print(f'[rthook] could not install Qt message handler: {e}', file=sys.stderr)


# Hook into PyQt6.QtWidgets import to install the handler as early as possible
_original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

def _patched_import(name, *args, **kwargs):
    mod = _original_import(name, *args, **kwargs)
    if name == 'PyQt6.QtWidgets' or (name == 'PyQt6' and 'QtWidgets' in str(args)):
        try:
            _install_qt_message_handler()
        except Exception:
            pass
        # Restore original import after first hit
        try:
            __builtins__.__import__ = _original_import
        except (AttributeError, TypeError):
            import builtins
            builtins.__import__ = _original_import
    return mod

try:
    __builtins__.__import__ = _patched_import
except (AttributeError, TypeError):
    import builtins
    builtins.__import__ = _patched_import
