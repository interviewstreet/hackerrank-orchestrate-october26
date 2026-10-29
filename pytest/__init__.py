def fixture(_func=None, **kwargs):
    """Simple fixture decorator compatible with pytest style used in tests.
    Returns the original function unchanged.
    """
    def decorator(func):
        return func
    if _func is None:
        return decorator
    return _func
