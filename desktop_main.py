"""PyInstaller entry point. freeze_support MUST precede desktop startup/imports."""
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()
    try:
        from desktop.launcher import main
        result=main()
    except Exception as error:
        # Also capture imports that fail before launcher.main enters its guard.
        from desktop.startup import Startup
        from desktop.windows import message
        startup=Startup('bootstrap')
        try: startup.prepare()
        except Exception: pass
        startup.stage='entrypoint_import'
        message(startup.failure(error),error=True)
        result=1
    raise SystemExit(result)
