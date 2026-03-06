from typing import Any

from flask import render_template
from models.admin import ACL, OSINTSource, OSINTSourceGroup, ProductType, ReportItemType, Role, WordList

from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


class ACLView(AdminMixin, BaseView):
    model = ACL
    _index = 50
    icon = "lock-closed"

    item_types = {
        "osint_source": {"id": "osint_source", "name": "OSINT Source", "model": OSINTSource},
        "osint_source_group": {"id": "osint_source_group", "name": "OSINT Source Group", "model": OSINTSourceGroup},
        "product_type": {"id": "product_type", "name": "Product Type", "model": ProductType},
        "report_item_type": {"id": "report_item_type", "name": "Report Type", "model": ReportItemType},
        "word_list": {"id": "word_list", "name": "Word List", "model": WordList},
    }

    @staticmethod
    def _get_objects_safe(dpl: DataPersistenceLayer, model) -> list[Any]:
        try:
            return list(dpl.get_objects(model))
        except ValueError:
            logger.warning(f"Failed to fetch {model.__name__} objects for ACL context")
            return []

    @classmethod
    def get_extra_context(cls, base_context: dict) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        item_ids = []
        selected_item_label = "Item ID"
        acl = base_context.get("acl")
        item_type = str(acl.item_type) if acl and acl.item_type else ""

        if item_type in cls.item_types:
            model = cls.item_types[item_type]["model"]
            objs = cls._get_objects_safe(dpl, model)
            use_title = item_type in {"product_type", "report_item_type"}
            item_ids = [{"id": item.id, "name": item.title if use_title else item.name} for item in objs]
            selected_item_label = cls.item_types[item_type]["name"]

        base_context |= {
            "roles": [p.model_dump() for p in cls._get_objects_safe(dpl, Role)],
            "item_types": cls.item_types.values(),
            "item_ids": item_ids,
            "selected_item_label": selected_item_label,
        }
        return base_context

    @classmethod
    def get_acl_item_ids_view(cls, item_type: str = ""):
        if not item_type or item_type not in cls.item_types:
            return render_template("acl/acl_item_ids.html")
        dpl = DataPersistenceLayer()

        model = cls.item_types[item_type]["model"]
        objs = cls._get_objects_safe(dpl, model)

        use_title = item_type in {"product_type", "report_item_type"}

        item_ids = [{"id": item.id, "name": item.title if use_title else item.name} for item in objs]
        selected_item_label = cls.item_types[item_type]["name"]
        return render_template(
            "acl/acl_item_ids.html",
            selected_item_label=selected_item_label,
            item_ids=item_ids,
        )
