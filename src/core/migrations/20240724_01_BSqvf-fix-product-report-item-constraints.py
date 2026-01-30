"""
fix product_report_item constraints
"""

from yoyo import step

__depends__ = {"20240703_01_KgAWj-update-user-model"}

steps = [
    step("""
        ALTER TABLE product_report_item DROP CONSTRAINT IF EXISTS product_report_item_product_id_fkey;
        ALTER TABLE product_report_item DROP CONSTRAINT IF EXISTS product_report_item_report_item_id_fkey;
        ALTER TABLE product_report_item
            ADD CONSTRAINT product_report_item_product_id_fkey FOREIGN KEY (product_id)
            REFERENCES product(id) ON DELETE CASCADE;
        ALTER TABLE product_report_item
            ADD CONSTRAINT product_report_item_report_item_id_fkey FOREIGN KEY (report_item_id)
            REFERENCES report_item(id) ON DELETE CASCADE;
        DELETE FROM product_report_item WHERE product_id IS NULL OR report_item_id IS NULL;
    """)
]
