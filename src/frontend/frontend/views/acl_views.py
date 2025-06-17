from typing import Any
from flask import render_template

from models.admin import ACL, Role, OSINTSource, OSINTSourceGroup, ProductType, ReportItemType, WordList
from frontend.data_persistence import DataPersistenceLayer
from frontend.views.base_view import BaseView


class ACLView(BaseView):
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

    @classmethod
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        dpl = DataPersistenceLayer()
        return {"roles": [p.model_dump() for p in dpl.get_objects(Role)], "item_types": cls.item_types.values()}

    @classmethod
    def get_acl_item_ids_view(cls, item_type: str = ""):
        if not item_type or item_type not in cls.item_types:
            return render_template("acl/acl_item_ids.html")
        dpl = DataPersistenceLayer()

        model = cls.item_types[item_type]["model"]
        objs = dpl.get_objects(model)

        use_title = item_type in {"product_type", "report_item_type"}

        item_ids = [{"id": item.id, "name": item.title if use_title else item.name} for item in objs]
        selected_item_label = cls.item_types[item_type]["name"]
        return render_template(
            "acl/acl_item_ids.html",
            selected_item_label=selected_item_label,
            item_ids=item_ids,
        )
