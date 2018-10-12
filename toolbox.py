"""
Utilities that almost every Python system needs
"""
import logging


def nested_get(d, *keys):
    """
    Iteratively fetch keys from nested dictionaries
    """
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, None)
        else:
            return None
    return d


def ordered_distinct(collection):
    """
    Return the unique elements of the given collection, preserving the order of elements.
    """
    seen = set()
    return [x for x in collection if x not in seen and (seen.add(x) or True)]


def null_logger():
    """
    Return a logger that does nothing
    """
    return logging.getLogger("NullLogger").addHandler(logging.NullHandler())
