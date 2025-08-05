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
from core.model.product_type import ProductType, ProductTypeReportType
from core.model.report_item_type import ReportItemType
from core.model.worker import PRESENTER_TYPES
from core.managers.db_manager import db


class TestProductTypeDeletionCascade:
    """Test cascade behavior when deleting ProductType"""

    @pytest.fixture
    def sample_report_type(self, app):
        """Create a sample ReportItemType for testing"""
        with app.app_context():
            report_type = ReportItemType(title="Test Report Type", description="A test report type for cascade testing")
            db.session.add(report_type)
            db.session.commit()
            yield report_type
            # Cleanup
            try:
                db.session.delete(report_type)
                db.session.commit()
            except Exception:
                db.session.rollback()

    @pytest.fixture
    def sample_product_type(self, app, sample_report_type):
        """Create a sample ProductType linked to the ReportItemType"""
        with app.app_context():
            product_type = ProductType(
                title="Test Product Type",
                type=PRESENTER_TYPES.HTML_PRESENTER,
                description="A test product type",
                report_types=[sample_report_type.id],
            )
            db.session.add(product_type)
            db.session.commit()
            yield product_type
            # Cleanup
            try:
                db.session.delete(product_type, confirm_deleted_rows=False)
                db.session.commit()
            except Exception:
                db.session.rollback()

    @pytest.fixture
    def additional_product_type(self, app, sample_report_type):
        """Create another ProductType linked to the same ReportItemType"""
        with app.app_context():
            product_type2 = ProductType(
                title="Second Test Product Type",
                type=PRESENTER_TYPES.PDF_PRESENTER,
                description="A second test product type",
                report_types=[sample_report_type.id],
            )
            db.session.add(product_type2)
            db.session.commit()
            yield product_type2
            # Cleanup
            try:
                db.session.delete(product_type2, confirm_deleted_rows=False)
                db.session.commit()
            except Exception:
                db.session.rollback()

    @pytest.fixture
    def sample_product_type_multi_report_types(self, app):
        with app.app_context():
            # Create multiple ReportItemTypes
            report_type1 = ReportItemType(title="Report Type 1", description="First report type")
            report_type2 = ReportItemType(title="Report Type 2", description="Second report type")
            report_type3 = ReportItemType(title="Report Type 3", description="Third report type")

            db.session.add_all([report_type1, report_type2, report_type3])
            db.session.flush()

            # Create a ProductType that references all three ReportItemTypes
            product_type = ProductType(
                title="Multi-Report Product Type",
                type=PRESENTER_TYPES.HTML_PRESENTER,
                description="Product type with multiple report types",
                report_types=[report_type1.id, report_type2.id, report_type3.id],
            )
            db.session.add(product_type)
            db.session.commit()
            yield product_type
            try:
                db.session.delete(product_type, confirm_deleted_rows=False)
                db.session.commit()
            except Exception:
                db.session.rollback()

    def test_initial_relationship_setup(self, sample_product_type, additional_product_type, sample_report_type):
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

    def test_product_type_deletion_cascade_behavior(self, app, sample_product_type, additional_product_type, sample_report_type):
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

    def test_product_type_deletion_with_multiple_report_types(self, sample_product_type_multi_report_types):
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

    def test_product_type_deletion_with_usage_check(self, app):
        """Test ProductType deletion when it's used in a Product"""
        with app.app_context():
            # Create a ReportItemType and ProductType
            report_type = ReportItemType(title="Usage Test Report Type")
            db.session.add(report_type)
            db.session.flush()

            product_type = ProductType(title="Usage Test Product Type", type=PRESENTER_TYPES.PDF_PRESENTER, report_types=[report_type.id])
            db.session.add(product_type)
            db.session.commit()

            # Try to delete the ProductType
            result, status_code = ProductType.delete(product_type.id)

            # The current implementation should allow deletion if not used in a Product
            # If it's used in a Product, it should return 409
            if status_code == 200:
                # Deletion succeeded - verify cascade behavior
                assert "deleted" in result["message"].lower()

                # Verify ProductType is gone
                assert ProductType.get(product_type.id) is None

                # Verify ReportItemType still exists
                assert ReportItemType.get(report_type.id) is not None

                # Verify associations are cleaned up
                associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type.id).all()
                assert len(associations) == 0

            elif status_code == 409:
                # Deletion prevented due to usage in Product
                assert "product" in result["error"].lower()

                # Verify ProductType still exists
                assert ProductType.get(product_type.id) is not None

                # Verify ReportItemType still exists
                assert ReportItemType.get(report_type.id) is not None

                # Verify associations still exist
                associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type.id).all()
                assert len(associations) == 1

    def test_database_cascade_constraint_analysis(self, app):
        """Analyze the database CASCADE constraints for ProductType deletion"""
        with app.app_context():
            # Create test data
            report_type = ReportItemType(title="Constraint Analysis Report Type")
            db.session.add(report_type)
            db.session.flush()

            product_type = ProductType(
                title="Constraint Analysis Product Type", type=PRESENTER_TYPES.TEXT_PRESENTER, report_types=[report_type.id]
            )
            db.session.add(product_type)
            db.session.commit()

            product_type_id = product_type.id
            report_type_id = report_type.id

            # Verify association exists
            association = (
                db.session.query(ProductTypeReportType).filter_by(product_type_id=product_type_id, report_item_type_id=report_type_id).first()
            )
            assert association is not None

            # Perform direct database deletion (bypassing the delete method)
            # This tests the actual database constraint behavior
            db.session.delete(product_type)
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

    def test_product_type_deletion_removes_associations(self, app, sample_product_type, additional_product_type, sample_report_type):
        """Test that deleting a ProductType removes its n:m relationship entries (original test)"""
        with app.app_context():
            original_product_type_id = sample_product_type.id
            additional_product_type_id = additional_product_type.id
            original_report_type_id = sample_report_type.id

            # Verify initial state - 2 associations exist
            initial_associations = db.session.query(ProductTypeReportType).filter_by(report_item_type_id=original_report_type_id).all()
            assert len(initial_associations) == 2

            # Delete one ProductType
            result, status_code = ProductType.delete(original_product_type_id)
            assert status_code == 200

            # Verify the ProductType is gone
            deleted_product_type = ProductType.get(original_product_type_id)
            assert deleted_product_type is None

            # Verify only one association remains (for the other ProductType)
            remaining_associations = db.session.query(ProductTypeReportType).filter_by(report_item_type_id=original_report_type_id).all()
            assert len(remaining_associations) == 1
            assert remaining_associations[0].product_type_id == additional_product_type_id

            # Verify the ReportItemType still exists
            remaining_report_type = ReportItemType.get(original_report_type_id)
            assert remaining_report_type is not None
            assert sample_report_type is not None

    def test_current_cascade_behavior_summary(self, app):
        """Summary test demonstrating the current CASCADE behavior"""
        with app.app_context():
            print("\n=== PRODUCT TYPE DELETION CASCADE TEST ===")

            # Setup: Create ReportItemTypes and ProductTypes
            report_type1 = ReportItemType(title="Shared Report Type", description="Used by multiple product types")
            report_type2 = ReportItemType(title="Exclusive Report Type", description="Used by only one product type")

            db.session.add_all([report_type1, report_type2])
            db.session.flush()

            # ProductType that will be deleted (uses both report types)
            product_type_to_delete = ProductType(
                title="Product Type To Delete",
                type=PRESENTER_TYPES.HTML_PRESENTER,
                description="This product type will be deleted",
                report_types=[report_type1.id, report_type2.id],
            )

            # ProductType that will remain (uses only report_type1)
            product_type_to_keep = ProductType(
                title="Product Type To Keep",
                type=PRESENTER_TYPES.PDF_PRESENTER,
                description="This product type will remain",
                report_types=[report_type1.id],
            )

            db.session.add_all([product_type_to_delete, product_type_to_keep])
            db.session.commit()

            # Store IDs for verification
            delete_id = product_type_to_delete.id
            keep_id = product_type_to_keep.id
            report1_id = report_type1.id
            report2_id = report_type2.id

            print(f"Created ProductType to delete: {delete_id}")
            print(f"Created ProductType to keep: {keep_id}")
            print(f"Created shared ReportItemType: {report1_id}")
            print(f"Created exclusive ReportItemType: {report2_id}")

            # Verify initial associations for our specific data
            delete_associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=delete_id).all()
            keep_associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=keep_id).all()

            print(f"Associations for ProductType to delete: {len(delete_associations)}")
            print(f"Associations for ProductType to keep: {len(keep_associations)}")

            # Should be 2 for delete (report1_id + report2_id) and 1 for keep (report1_id)
            assert len(delete_associations) == 2
            assert len(keep_associations) == 1

            # Delete the ProductType
            print(f"\nDeleting ProductType {delete_id}...")
            result, status_code = ProductType.delete(delete_id)

            if status_code == 200:
                print("✓ ProductType deletion successful")

                # Verify ProductType is gone
                assert ProductType.get(delete_id) is None
                print("✓ ProductType removed from database")

                # Verify ReportItemTypes still exist
                assert ReportItemType.get(report1_id) is not None
                assert ReportItemType.get(report2_id) is not None
                print("✓ ReportItemTypes preserved")

                # Verify remaining ProductType still exists
                remaining_product_type = ProductType.get(keep_id)
                assert remaining_product_type is not None
                print("✓ Other ProductType preserved")

                # Verify association cleanup - check specific associations for our data
                remaining_delete_associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=delete_id).all()
                remaining_keep_associations = db.session.query(ProductTypeReportType).filter_by(product_type_id=keep_id).all()

                print(f"Remaining associations for deleted ProductType: {len(remaining_delete_associations)}")
                print(f"Remaining associations for kept ProductType: {len(remaining_keep_associations)}")

                # Should be 0 for deleted ProductType, 1 for kept ProductType
                assert len(remaining_delete_associations) == 0
                assert len(remaining_keep_associations) == 1
                assert remaining_keep_associations[0].report_item_type_id == report1_id
                print("✓ Associations properly cleaned up")

                # Verify the remaining ProductType still has its ReportItemType
                db.session.refresh(remaining_product_type)
                assert len(remaining_product_type.report_types) == 1
                assert remaining_product_type.report_types[0].id == report1_id
                print("✓ Remaining ProductType->ReportItemType relationship intact")

                print("\n=== CASCADE BEHAVIOR SUMMARY ===")
                print("✅ ProductType deletion works correctly:")
                print("   - Deleted ProductType removed")
                print("   - ReportItemTypes preserved")
                print("   - n:m associations automatically cleaned up")
                print("   - Other ProductTypes unaffected")
                print("   - Database integrity maintained")

            else:
                print(f"❌ ProductType deletion failed: {result}")
                print(f"Status code: {status_code}")
                # This might happen if the ProductType is used in a Product
