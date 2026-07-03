class MockRedisPipeline:
    def __init__(self, client) -> None:
        self.client = client

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def zremrangebyscore(self, key, min_val, max_val):
        return self

    def zadd(self, key, mapping):
        return self

    def zcard(self, key):
        return self

    def expire(self, key, ttl):
        return self

    async def execute(self):
        # Default zset cardinality check response (1)
        return (0, 1, 1, True)

class MockRedis:
    def __init__(self, *args, **kwargs) -> None:
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, val: str, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = val
        return True

    async def delete(self, key: str):
        if key in self.store:
            del self.store[key]
        return True

    async def incr(self, key: str) -> int:
        val = int(self.store.get(key, 0)) + 1
        self.store[key] = str(val)
        return val

    async def llen(self, key: str) -> int:
        return 0

    async def ping(self) -> bool:
        return True

    def pipeline(self, transaction: bool = True) -> MockRedisPipeline:
        return MockRedisPipeline(self)
