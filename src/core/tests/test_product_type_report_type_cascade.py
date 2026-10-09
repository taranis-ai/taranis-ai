"""Deleting a product type removes its associations and preserves shared report types."""

from models.types import PRESENTER_TYPES

from core.managers.db_manager import db
from core.model.product_type import ProductType, ProductTypeReportType
from core.model.report_item_type import ReportItemType


def test_product_type_deletion_preserves_report_types_and_other_products(app, session, sample_report_type):
    with app.app_context():
        second_report_type = ReportItemType(title="Second cascade report type", description="")
        session.add(second_report_type)
        session.flush()
        report_type_ids = [sample_report_type.id, second_report_type.id]
        product_type = ProductType(
            title="Deleted cascade product type",
            type=PRESENTER_TYPES.HTML_PRESENTER,
            parameters={"TEMPLATE_PATH": "osint_report_tailwind.html"},
            report_types=report_type_ids,
        )
        other_product_type = ProductType(
            title="Retained cascade product type",
            type=PRESENTER_TYPES.HTML_PRESENTER,
            parameters={"TEMPLATE_PATH": "osint_report_tailwind.html"},
            report_types=[sample_report_type.id],
        )
        session.add_all([product_type, other_product_type])
        session.commit()
        product_type_id, other_product_type_id = product_type.id, other_product_type.id
        assert {report_type.id for report_type in product_type.report_types} == set(report_type_ids)

        result, status = ProductType.delete(product_type_id)

        assert status == 200
        assert "deleted" in result["message"].lower()
        assert ProductType.get(product_type_id) is None
        assert all(ReportItemType.get(report_type_id) is not None for report_type_id in report_type_ids)
        assert db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type_id).all() == []
        retained = ProductType.get(other_product_type_id)
        assert retained is not None
        session.refresh(retained)
        assert [report_type.id for report_type in retained.report_types] == [sample_report_type.id]
