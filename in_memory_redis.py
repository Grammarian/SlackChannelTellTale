class InMemoryRedis:
    """
    This class like an in-memory version of Redis.

    Useful for unit tests or if Redis isn't available
    """

    def __init__(self):
        self._cache = {}

    def get(self, key):
        """
        Return the value associate with the given key, or None if it doesn't exist.
        :param key:
        :return: The associated value or none
        """
        return self._cache.get(key)

    def setnx(self, key, value):
        """
        Set the given key to have the given value IFF the given key doesn't already exist.
        :param key:
        :param value:
        :return: Return true if key is set to the value
        """
        if key in self._cache:
            return False
        self._cache[key] = value
        return True

    def expire(self, key, ttl):
        """
        Set the time to live for the given key.

        :param key:
        :param ttl:
        :return: True to indicate success
        """
        # This is a no-op
        return True
