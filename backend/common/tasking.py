try:
    from celery import shared_task
except ImportError:  # pragma: no cover - fallback for local environments without Celery.
    def shared_task(*decorator_args, **decorator_kwargs):
        def decorator(func):
            func.delay = func
            return func

        if decorator_args and callable(decorator_args[0]) and not decorator_kwargs:
            return decorator(decorator_args[0])
        return decorator


__all__ = ["shared_task"]
