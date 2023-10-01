from core.managers.db_manager import db
from core.model.asset import Asset
from core.model.report_item import ReportItem


def remove_vulnerability(report_item_id):
    Asset.remove_vulnerability(report_item_id)
    db.session.commit()


def report_item_changed(report_item: "ReportItem"):
    if not report_item:
        return
    if not report_item.completed:
        return
    cpes = [cpe.value for cpe in report_item.report_item_cpes]
    assets = Asset.get_by_cpe(cpes)

    notification_groups = set()

    for asset in assets:
        asset.add_vulnerability(report_item)
        notification_groups.add(asset.asset_group)

    db.session.commit()
