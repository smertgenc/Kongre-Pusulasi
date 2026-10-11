"""Spawned backend owns its loopback socket until shutdown; no port race."""
import asyncio
import socket

def run_backend(pipe, stop, database, token, log_directory):
    from desktop.logging_setup import configure_logs, event
    from desktop.startup import Startup
    from pathlib import Path
    startup=Startup('backend');sock=None
    try:
        startup.stage='logging_initialization'
        configure_logs(log_directory);startup.log_directory=Path(log_directory)
        startup.mark('backend_starting')
        startup.mark('socket_binding')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1',0)); sock.listen(128)
        port = sock.getsockname()[1]
        startup.mark('application_import')
        from app.main import create_app
        import uvicorn
        startup.mark('application_creation')
        app = create_app(database, desktop_session={'token':token,'host':f'127.0.0.1:{port}'})
        config = uvicorn.Config(app, host='127.0.0.1', port=port, log_config=None, access_log=False,
                                timeout_graceful_shutdown=12, timeout_keep_alive=5, loop='asyncio', http='h11')
        server = uvicorn.Server(config)
        async def serve():
            startup.mark('database_starting')
            task = asyncio.create_task(server.serve(sockets=[sock]))
            while not server.started and not task.done() and not stop.is_set():
                await asyncio.sleep(.05)
            if not server.started:
                server.should_exit = True
                await task
                raise RuntimeError('BACKEND_START_FAILED')
            startup.mark('backend_ready')
            pipe.send({'port':port}); pipe.close()
            while not task.done() and not stop.is_set(): await asyncio.sleep(.2)
            server.should_exit = True
            await task
        asyncio.run(serve())
    except BaseException as error:
        startup.failure(error)
        try: pipe.send({'error':'BACKEND_START_FAILED','stage':startup.stage,'error_type':type(error).__name__})
        except (OSError, EOFError): pass
    finally:
        if sock is not None: sock.close()
        pipe.close()
