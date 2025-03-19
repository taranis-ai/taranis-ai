from flask import request
from flask_jwt_extended import get_jwt_identity
from typing import Type

from admin.core_api import CoreApi
from admin.config import Config
from admin.cache import cache
from admin.models import TaranisBaseModel, T, CacheObject, PagingData
from admin.log import logger


class DataPersistenceLayer:
    def __init__(self, jwt_token=None):
        self.jwt_token = jwt_token or self.get_jwt_from_request()
        self.api = CoreApi(jwt_token=self.jwt_token)

    def make_key(self, endpoint: str):
        return f"{get_jwt_identity()}_{endpoint.replace('/', '_')}"

    def get_jwt_from_request(self):
        return request.cookies.get(Config.JWT_ACCESS_COOKIE_NAME)

    def get_endpoint(self, object_model: Type[TaranisBaseModel] | TaranisBaseModel) -> str:
        return object_model._core_endpoint

    def get_object(self, object_model: Type[T], object_id: int | str) -> TaranisBaseModel | None:
        if result := self.get_objects(object_model):
            for object in result:
                if object.id == object_id:  # type: ignore
                    return object

    def invalidate_cache(self, suffix: str):
        keys = list(cache.cache._cache.keys())
        keys_to_delete = [key for key in keys if key.endswith(f"_{suffix}")]
        for key in keys_to_delete:
            cache.delete(key)

    def get_objects(self, object_model: Type[T], paging_data: PagingData | None = None) -> list[T] | None:
        endpoint = self.get_endpoint(object_model)
        cache_object: CacheObject | None
        if cache_object := cache.get(key=self.make_key(endpoint)):
            logger.info(f"Cache hit for {endpoint}")
            return cache_object.paginate(paging_data)
        if result := self.api.api_get(endpoint):
            result_object = [object_model(**object) for object in result["items"]]
            cache_object = CacheObject(result_object)
            cache.set(key=self.make_key(endpoint), value=cache_object, timeout=Config.CACHE_DEFAULT_TIMEOUT)
            return cache_object.paginate(paging_data)

    def store_object(self, object: TaranisBaseModel):
        store_object = object.model_dump()
        return self.api.api_post(object._core_endpoint, json_data=store_object)

    def delete_object(self, object_model: Type[TaranisBaseModel], object_id: int | str):
        endpoint = self.get_endpoint(object_model)
        return self.api.api_delete(f"{endpoint}/{object_id}")

    def update_object(self, object: TaranisBaseModel, object_id: int | str):
        endpoint = self.get_endpoint(object)
        return self.api.api_put(f"{endpoint}/{object_id}", json_data=object.model_dump())
