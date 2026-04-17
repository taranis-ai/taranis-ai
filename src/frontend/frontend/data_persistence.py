import hashlib
import json
from typing import Any, Type

from flask import request
from flask_jwt_extended import get_jwt_identity
from models.base import T, TaranisBaseModel
from requests import Response

from frontend.cache import DEFAULT_LIST_CACHE_SUFFIX, cache
from frontend.cache_models import CacheObject, PagingData
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.log import logger


class DataPersistenceLayer:
    def __init__(self, jwt_token=None):
        self.jwt_token = jwt_token or self.get_jwt_from_request()
        self.api = CoreApi(jwt_token=self.jwt_token)

    def get_cache_username(self) -> str:
        try:
            identity = get_jwt_identity()
        except Exception:
            identity = None
        return str(identity or "anonymous")

    def make_filter_key(self, filter_data: Any) -> str:
        json_str = json.dumps(filter_data, sort_keys=True, separators=(",", ":"))
        return hashlib.md5(json_str.encode("utf-8")).hexdigest()

    def get_jwt_from_request(self):
        return request.cookies.get(Config.JWT_ACCESS_COOKIE_NAME)

    def get_endpoint(self, object_model: Type[TaranisBaseModel] | TaranisBaseModel) -> str:
        return object_model._core_endpoint

    def get_first(self, object_model: Type[T]) -> T | None:
        objects = self.get_objects(object_model).items
        return None if len(objects) < 1 else objects[0]

    @staticmethod
    def _normalize_collection_payload(result: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
        if isinstance(result, list):
            return {"items": result, "total_count": len(result)}
        return result

    def make_list_cache_suffix(self, endpoint: str, paging_data: PagingData | None = None) -> str:
        payload = {
            "endpoint": endpoint,
            "paging": paging_data.model_dump(mode="json") if paging_data else {},
        }
        return self.make_filter_key(payload) if payload["paging"] or endpoint else DEFAULT_LIST_CACHE_SUFFIX

    def make_list_cache_key(self, object_model: Type[T], endpoint: str, paging_data: PagingData | None = None) -> str:
        return cache.model_list_key(self.get_cache_username(), object_model._model_name, self.make_list_cache_suffix(endpoint, paging_data))

    def make_detail_cache_key(self, object_model: Type[T], object_id: int | str | None = None) -> str:
        return cache.model_detail_key(self.get_cache_username(), object_model._model_name, object_id)

    @staticmethod
    def _deserialize_object(object_model: Type[T], payload: dict[str, Any]) -> T:
        return object_model(**payload)

    def _build_cache_object(self, object_model: Type[T], result: dict[str, Any], paging_data: PagingData | None) -> CacheObject[T]:
        items = result.get("items", [])
        result_object = [object_model(**object_data) for object_data in items]
        total_count = result.get("total_count", result.get("counts", {}).get("total_count", len(result_object)))
        links = result.get("_links", {})
        return CacheObject(
            result_object,
            total_count=total_count,
            limit=paging_data.limit if paging_data and paging_data.limit else 20,
            page=paging_data.page if paging_data and paging_data.page else 1,
            order=paging_data.order if paging_data and paging_data.order else "",
            query_params=paging_data.query_params if paging_data else {},
            links=links,
        )

    def get_object(self, object_model: Type[T], object_id: int | str | None = None) -> T | None:
        endpoint = self.get_endpoint(object_model)
        cache_key = self.make_detail_cache_key(object_model, object_id)
        if (cached_payload := cache.get(key=cache_key)) is not None:
            try:
                return self._deserialize_object(object_model, cached_payload)
            except Exception:
                logger.exception("Failed to deserialize cached object for %s", cache_key)
                cache.delete(cache_key)
        path = endpoint if object_id is None else f"{endpoint}/{object_id}"
        result = self.api.api_get(path)
        if isinstance(result, dict):
            cache_object = object_model(**result)
            timeout = getattr(object_model, "_cache_timeout", Config.CACHE_DEFAULT_TIMEOUT)
            cache.set(key=cache_key, value=cache_object.model_dump(mode="json"), timeout=timeout)
            return cache_object
        logger.warning(f"Failed to fetch object from: {endpoint}")

    def invalidate_cache(self, suffix: str | None = None) -> Response:
        if not suffix:
            return self.api.api_post("/admin/cache/invalidate", json_data={"mode": "all"})
        return self.api.api_post("/admin/cache/invalidate", json_data={"mode": "model", "model": suffix})

    def invalidate_cache_by_object(self, object_model: TaranisBaseModel | Type[TaranisBaseModel]) -> Response:
        return self.api.api_post("/admin/cache/invalidate", json_data={"mode": "model", "model": object_model._model_name})

    def invalidate_cache_by_object_id(self, object_model: TaranisBaseModel | Type[TaranisBaseModel], object_id: int | str) -> Response:
        return self.api.api_post(
            "/admin/cache/invalidate",
            json_data={"mode": "model", "model": object_model._model_name, "object_id": str(object_id)},
        )

    def get_objects_by_endpoint(self, object_model: Type[T], endpoint: str, paging_data: PagingData | None = None) -> CacheObject[T]:
        cache_key = self.make_list_cache_key(object_model, endpoint, paging_data)
        if (cached_payload := cache.get(key=cache_key)) is not None:
            logger.debug(f"Cache hit for {cache_key}")
            try:
                return self._build_cache_object(object_model, cached_payload, paging_data)
            except Exception:
                logger.exception("Failed to deserialize cached object list for %s", cache_key)
                cache.delete(cache_key)
        result = self.api.api_get(endpoint, paging_data.query_params if paging_data else None)
        if isinstance(result, (dict, list)):
            return self._cache_and_paginate_objects(
                self._normalize_collection_payload(result),
                object_model,
                endpoint,
                paging_data,
            )
        raise ValueError(f"Failed to fetch {object_model.__name__} from: {endpoint}")

    def get_objects(self, object_model: Type[T], paging_data: PagingData | None = None) -> CacheObject[T]:
        if paging_data is None:
            paging_data = PagingData().set_fetch_all()
        endpoint = self.get_endpoint(object_model)
        cache_key = self.make_list_cache_key(object_model, endpoint, paging_data)
        if (cached_payload := cache.get(key=cache_key)) is not None:
            logger.debug(f"Cache hit for {cache_key}")
            try:
                return self._build_cache_object(object_model, cached_payload, paging_data)
            except Exception:
                logger.exception("Failed to deserialize cached model list for %s", cache_key)
                cache.delete(cache_key)
        result = self.api.api_get(endpoint, paging_data.query_params if paging_data else None)
        if isinstance(result, (dict, list)):
            return self._cache_and_paginate_objects(
                self._normalize_collection_payload(result),
                object_model,
                endpoint,
                paging_data,
            )
        raise ValueError(f"Failed to fetch {object_model.__name__} from: {endpoint}")

    def _cache_and_paginate_objects(
        self,
        result: dict[str, Any],
        object_model: Type[T],
        endpoint: str,
        paging_data: PagingData | None,
    ) -> CacheObject[T]:
        cache_object = self._build_cache_object(object_model, result, paging_data)
        timeout = getattr(object_model, "_cache_timeout", cache_object.timeout)
        logger.debug(f"Adding {len(cache_object)} items from {endpoint} to cache with timeout: {timeout}")
        cache.set(key=self.make_list_cache_key(object_model, endpoint, paging_data), value=result, timeout=timeout)
        return cache_object

    def store_object(self, object) -> Response:
        store_object = object.model_dump(mode="json")
        return self.api.api_post(object._core_endpoint, json_data=store_object)

    def delete_object(self, object_model: Type[TaranisBaseModel], object_id: int | str) -> Response:
        endpoint = self.get_endpoint(object_model)
        return self.api.api_delete(f"{endpoint}/{object_id}")

    def update_object(self, object: TaranisBaseModel, object_id: int | str) -> Response:
        endpoint = self.get_endpoint(object)
        return self.api.api_put(f"{endpoint}/{object_id}", json_data=object.model_dump(mode="json"))
