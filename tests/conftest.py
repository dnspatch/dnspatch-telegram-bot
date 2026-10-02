import pytest
from fakeredis import FakeAsyncRedis


@pytest.fixture
def redis() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)
