import os

from roger.config import AnnotationConfig, RedisConfig, RogerConfig


def test_merge():
    dict_a = {
        'redis': {
            'host': 'redis',
            'port': 6379,
            'user': 'admin',
            'password': 'pass1'
        }
    }
    dict_b = {
        'redis': {
            'port': 6389,
            'password': 'pass2'
        },
        'elasticsearch': {
            'host': 'elastic',
            'port': 9200
        }
    }

    assert RogerConfig.merge_dicts(dict_a, dict_b) == {
       'redis': {
           'host': 'redis',
           'port': 6389,
           'user': 'admin',
           'password': 'pass2'
        },
        'elasticsearch': {
            'host': 'elastic',
            'port': 9200
        }
    }


def test_get_overrides():
    prefix = "TEST_VALUES_"
    assert RogerConfig.get_override_data(prefix) == {}

    os.environ[f"{prefix}REDIS_HOST"] = 'http://redis.svc'
    os.environ[f"{prefix}REDIS_PORT"] = '6379'
    os.environ[f"{prefix}REDIS_USER"] = 'redis-admin'
    os.environ[f"{prefix}REDIS_PASSWORD"] = 'admin-pass'
    os.environ[f"{prefix}ELASTIC__SEARCH_HOST"] = 'http://elastic.svc'

    actual = RogerConfig.get_override_data(prefix)
    expected = {
        'redis': {
            'host': 'http://redis.svc',
            'port': '6379',
            'user': 'redis-admin',
            'password': 'admin-pass',
        },
        'elastic_search': {
            'host': 'http://elastic.svc',
        }
    }
    assert actual == expected


def test_redis_conf():
    redis_conf = RedisConfig(**{})
    assert redis_conf.username == ""
    assert redis_conf.password == ""
    assert redis_conf.host == "redis"
    assert redis_conf.graph == "test"
    assert redis_conf.port == 6379

    redis_conf = RedisConfig(**{"port": "6379"})
    assert redis_conf.port == 6379



def test_annotation_cache_flags_coerced_from_environment_strings():
    """Env vars arrive as strings, and 'false' is truthy -- which would leave
    POST caching on for someone who explicitly turned it off."""
    conf = AnnotationConfig(
        cache_post_requests='false',
        http_cache_expire_seconds='3600',
        annotate_workers='8',
    )
    assert conf.cache_post_requests is False
    assert conf.http_cache_expire_seconds == 3600
    assert conf.annotate_workers == 8

    assert AnnotationConfig(cache_post_requests='true').cache_post_requests
    # a zero or negative worker count would break ThreadPoolExecutor
    assert AnnotationConfig(annotate_workers='0').annotate_workers == 1


def test_annotation_cache_defaults_are_safe():
    """POST caching on, and a nonzero expiry so requests_cache writes redis
    entries with SETEX -- keeping the annotation cache evictable while the
    graph keys sharing that redis are not."""
    conf = AnnotationConfig()
    assert conf.cache_post_requests is True
    assert conf.http_cache_expire_seconds > 0
