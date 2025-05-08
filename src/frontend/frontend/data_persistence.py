from flask import request
from flask_jwt_extended import get_jwt_identity
from typing import Type

from frontend.core_api import CoreApi
from frontend.config import Config
from frontend.cache import cache
from models.base import TaranisBaseModel, T
from frontend.cache_models import CacheObject, PagingData
from frontend.log import logger


class DataPersistenceLayer:
    def __init__(self, jwt_token=None):
        self.jwt_token = jwt_token or self.get_jwt_from_request()
        self.api = CoreApi(jwt_token=self.jwt_token)

    def make_user_key(self, endpoint: str):
        return f"{get_jwt_identity()}_{self.make_key(endpoint)}"

    def make_key(self, endpoint: str):
        return endpoint.replace("/", "_")

    def get_jwt_from_request(self):
        return request.cookies.get(Config.JWT_ACCESS_COOKIE_NAME)

    def get_endpoint(self, object_model: Type[TaranisBaseModel] | TaranisBaseModel) -> str:
        return object_model._core_endpoint

    def get_object(self, object_model: Type[T], object_id: int | str) -> TaranisBaseModel | None:
        endpoint = self.get_endpoint(object_model)

        if cache_object := cache.get(key=self.make_user_key(endpoint)):
            logger.debug(f"Cache hit for {endpoint}")
            for object in cache_object:
                if object.id == object_id:  # type: ignore
                    return object
        if result := self.api.api_get(f"{endpoint}/{object_id}"):
            return object_model(**result)

        logger.warning(f"Failed to fetch object from: {endpoint}")

    def invalidate_cache(self, suffix: str | None = None) -> None:
        keys = list(cache.cache._cache.keys())
        for key in keys:
            if suffix is None or key.endswith(f"_{suffix}"):
                cache.delete(key)

    def invalidate_cache_by_object(self, object: TaranisBaseModel | Type[TaranisBaseModel]):
        suffix = self.make_key(object._core_endpoint)
        self.invalidate_cache(suffix)

    def get_objects(self, object_model: Type[T], paging_data: PagingData | None = None) -> list[T]:
        endpoint = self.get_endpoint(object_model)
        cache_object: CacheObject | None
        if cache_object := cache.get(key=self.make_user_key(endpoint)):
            logger.debug(f"Cache hit for {endpoint}")
            return cache_object.search_and_paginate(paging_data)
        if result := self.api.api_get(endpoint):
            return self._cache_and_paginate_objects(result, object_model, endpoint, paging_data)
        raise ValueError(f"Failed to fetch {object_model.__name__} from: {endpoint}")

    def _cache_and_paginate_objects(self, result, object_model, endpoint, paging_data):
        result_object = [object_model(**object) for object in result.get("items", [])]
        if not result_object:
            logger.warning(f"Empty result for {endpoint}")
            return []
        total_count = result.get("total_count", len(result_object))
        links = result.get("_links", {})
        cache_object = CacheObject(
            result_object,
            total_count=total_count,
            links=links,
        )
        logger.debug(f"Adding {endpoint} to cache with timeout: {cache_object.timeout}")
        cache.set(key=self.make_user_key(endpoint), value=cache_object, timeout=cache_object.timeout)
        return cache_object.search_and_paginate(paging_data)

    def store_object(self, object: TaranisBaseModel):
        store_object = object.model_dump(mode="json")
        logger.info(f"Storing object: {store_object}")
        response = self.api.api_post(object._core_endpoint, json_data=store_object)
        if response.ok:
            self.invalidate_cache_by_object(object)
        return response

    def delete_object(self, object_model: Type[TaranisBaseModel], object_id: int | str):
        endpoint = self.get_endpoint(object_model)
        response = self.api.api_delete(f"{endpoint}/{object_id}")
        if response.ok:
            self.invalidate_cache_by_object(object_model)
        return response

    def update_object(self, object: TaranisBaseModel, object_id: int | str):
        endpoint = self.get_endpoint(object)
        response = self.api.api_put(f"{endpoint}/{object_id}", json_data=object.model_dump(mode="json"))
        if response.ok:
            self.invalidate_cache_by_object(object)
        return response
