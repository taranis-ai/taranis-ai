import threading

from core.managers.db_manager import db
from core.managers import publishers_manager
from core.model.asset import Asset
from core.model.publisher_preset import PublisherPreset


def remove_vulnerability(report_item_id):
    Asset.remove_vulnerability(report_item_id)
    db.session.commit()


def report_item_changed(report_item):
    if report_item.completed:
        cpes = []
        for cpe in report_item.report_item_cpes:
            cpes.append(cpe.value)

        assets = Asset.get_by_cpe(cpes)

        notification_groups = set()

        for asset in assets:
            asset.add_vulnerability(report_item)
            notification_groups.add(asset.asset_group)

        db.session.commit()

        publisher_preset = PublisherPreset.find_for_notifications()
        if publisher_preset is not None:

            class NotificationThread(threading.Thread):
                @classmethod
                def run(cls):
                    for notification_group in notification_groups:
                        for template in notification_group.templates:
                            recipients = [recipient.email for recipient in template.recipients]
                            publishers_manager.publish(
                                publisher_preset,
                                None,
                                template.message_title,
                                template.message_body,
                                recipients,
                            )

            notification_thread = NotificationThread()
            notification_thread.start()
