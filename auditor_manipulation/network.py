"""Wall-clock bounded API transport, including providers that send keepalives."""
import multiprocessing
import time

from .runner import request_json

def _request_worker(connection, path, key, payload, timeout):
    try:
        # Workers are spawned afresh, so an opt-in transport-only amendment can
        # apply between requests without interrupting the running study.
        from .prompt_cache_transport import dispatch_cached
        connection.send(dispatch_cached(request_json, path, key, payload, timeout))
    except Exception as exc:
        connection.send({"http_status": None, "transport_error": type(exc).__name__,
                         "body": None})
    finally:
        connection.close()

def bounded_request_json(path, key, payload=None, timeout=300, *, _worker=_request_worker):
    """Stop the local network worker after a wall deadline; upstream billing may continue.

    A socket timeout alone is insufficient because periodic whitespace can reset it.
    A spawned process lets the controller close a stuck transport without waiting on
    its network read or abandoning an unbounded background thread. No automatic retry.
    The key travels through process IPC, never a shell command or saved request.
    """
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 600:
        raise ValueError("Wall timeout must be positive and at most 600 seconds")
    started = time.monotonic()
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(sender, path, key, payload, timeout),
                              name="bounded-api-request", daemon=True)
    result = None
    try:
        process.start()
        sender.close()
        remaining = max(0, timeout - (time.monotonic() - started))
        if receiver.poll(remaining):
            try:
                result = receiver.recv()
            except EOFError:
                result = {"http_status": None, "transport_error": "WorkerExited", "body": None}
        else:
            result = {"http_status": None, "transport_error": "LocalWallDeadlineExceeded",
                      "body": None, "upstream_completion_and_billing": "unknown"}
    finally:
        receiver.close()
        sender.close()
        if process.pid is not None:
            process.join(timeout=.2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            process.close()
    result["local_elapsed_seconds"] = time.monotonic() - started
    result["wall_timeout_seconds"] = timeout
    return result
