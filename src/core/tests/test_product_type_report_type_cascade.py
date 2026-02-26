"""
Test for ProductType deletion cascade behavior.

This test verifies the behavior when removing a ProductType record
that references ReportItemType(s) through the n:m relationship.

Expected behavior when deleting a ProductType:
- The ProductType should be deleted
- The ReportItemType(s) should remain intact
- The n:m relationship entries in product_type_report_type should be removed
- Other ProductTypes referencing the same ReportItemType should remain unaffected
"""

import pytest

from core.managers.db_manager import db
from core.model.product_type import ProductType, ProductTypeReportType
from core.model.report_item_type import ReportItemType


# ignore warning shown when fixtures try to delete already-deleted product types
pytestmark = pytest.mark.filterwarnings("ignore:DELETE statement on table 'product_type'.*:sqlalchemy.exc.SAWarning")


def test_initial_relationship_setup(sample_product_type, additional_product_type, sample_report_type):
    """Test that the n:m relationship is properly established"""

    product_type_1_id = sample_product_type.id
    product_type_2_id = additional_product_type.id
    report_type_id = sample_report_type.id

    # Verify the relationship exists from ProductType side by checking IDs
    product_type1_report_ids = [rt_item.id for rt_item in sample_product_type.report_types]
    product_type2_report_ids = [rt_item.id for rt_item in additional_product_type.report_types]

    assert report_type_id in product_type1_report_ids
    assert report_type_id in product_type2_report_ids

    # Verify the association table entry exists
    associations = db.session.query(ProductTypeReportType).filter_by(report_item_type_id=report_type_id).all()
    assert len(associations) == 2

    product_type_ids = {assoc.product_type_id for assoc in associations}
    assert product_type_ids == {product_type_1_id, product_type_2_id}


def test_product_type_deletion_cascade_behavior(sample_product_type, additional_product_type, sample_report_type):
    """Test that deleting a ProductType properly cascades to remove n:m associations"""
    product_type_to_delete_id = sample_product_type.id
    remaining_product_type_id = additional_product_type.id
    report_type_id = sample_report_type.id

    # Delete one ProductType using the delete method
    result, status_code = ProductType.delete(product_type_to_delete_id)

    # Verify deletion was successful
    assert status_code == 200
    assert "deleted" in result["message"].lower()

    # Verify the ProductType is gone
    deleted_product_type = ProductType.get(product_type_to_delete_id)
    assert deleted_product_type is None

    # Verify the ReportItemType still exists
    remaining_report_type = ReportItemType.get(report_type_id)
    assert remaining_report_type is not None
    assert remaining_report_type.title == sample_report_type.title

    # Verify the other ProductType still exists
    remaining_product_type = ProductType.get(remaining_product_type_id)
    assert remaining_product_type is not None

    # Verify n:m associations are properly cleaned up
    # Only one association should remain (for the non-deleted ProductType)
    remaining_associations = db.session.query(ProductTypeReportType).filter_by(report_item_type_id=report_type_id).all()
    assert len(remaining_associations) == 1
    assert remaining_associations[0].product_type_id == remaining_product_type_id

    # Verify no associations exist for the deleted ProductType
    deleted_associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type_to_delete_id).all()
    assert len(deleted_associations) == 0

    # Verify the remaining ProductType still has the ReportItemType
    db.session.refresh(remaining_product_type)
    assert len(remaining_product_type.report_types) == 1
    assert remaining_product_type.report_types[0].id == report_type_id


def test_product_type_deletion_with_multiple_report_types(sample_product_type_multi_report_types):
    """Test ProductType deletion when it references multiple ReportItemTypes"""

    product_type_id = sample_product_type_multi_report_types.id
    report_type_ids = [rt_item.id for rt_item in sample_product_type_multi_report_types.report_types]

    # Verify initial associations (should be 3)
    initial_associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type_id).all()
    assert len(initial_associations) == 3

    # Delete the ProductType
    _, status_code = ProductType.delete(product_type_id)
    assert status_code == 200

    # Verify ProductType is deleted
    assert ProductType.get(product_type_id) is None

    # Verify all ReportItemTypes still exist
    for report_type_id in report_type_ids:
        remaining_report_type = ReportItemType.get(report_type_id)
        assert remaining_report_type is not None

    # Verify all associations are cleaned up
    remaining_associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type_id).all()
    assert len(remaining_associations) == 0


def test_database_cascade_constraint_analysis(sample_report_type, sample_product_type):
    """Analyze the database CASCADE constraints for ProductType deletion"""

    product_type_id = sample_product_type.id
    report_type_id = sample_report_type.id

    # Verify association exists
    association = (
        db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type_id, report_item_type_id=report_type_id).first()
    )
    assert association is not None

    # Perform direct database deletion (bypassing the delete method)
    # This tests the actual database constraint behavior
    db.session.delete(sample_product_type)
    db.session.commit()

    # Verify ProductType is deleted
    assert ProductType.get(product_type_id) is None

    # Verify ReportItemType still exists
    assert ReportItemType.get(report_type_id) is not None

    # Verify association is automatically removed by CASCADE constraint
    remaining_association = (
        db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type_id, report_item_type_id=report_type_id).first()
    )
    assert remaining_association is None

    print("✓ Database CASCADE constraint working correctly:")
    print("  - ProductType deleted")
    print("  - ReportItemType preserved")
    print("  - Association automatically removed")
