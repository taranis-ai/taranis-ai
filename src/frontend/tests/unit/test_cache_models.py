from frontend.cache_models import CacheObject


def test_cache_object_slice_preserves_paging_metadata():
    sliced = CacheObject([1, 2, 3], page=2, limit=2, order="title", total_count=5)[1:]

    assert isinstance(sliced, CacheObject)
    assert list(sliced) == [2, 3]
    assert sliced.current_page == 2
    assert sliced.limit == 2
    assert sliced.total_count == 5
