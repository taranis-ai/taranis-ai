from datetime import datetime

from core.managers.db_manager import db


class AuditRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    ip_address = db.Column(db.String())

    user_id = db.Column(db.String())
    user_name = db.Column(db.String())

    system_id = db.Column(db.String())
    system_name = db.Column(db.String())

    activity_type = db.Column(db.String())
    activity_resource = db.Column(db.String())
    activity_detail = db.Column(db.String())

    def __init__(
        self,
        ip_address,
        user_id,
        user_name,
        system_id,
        system_name,
        activity_type,
        activity_resource,
        activity_detail,
    ):
        self.id = None
        self.ip_address = ip_address
        self.user_id = user_id
        self.user_name = user_name
        self.system_id = system_id
        self.system_name = system_name
        self.activity_type = activity_type
        self.activity_resource = activity_resource
        self.activity_detail = activity_detail

    @classmethod
    def store(
        cls,
        ip_address,
        user_id,
        user_name,
        system_id,
        system_name,
        activity_type,
        activity_resource,
        activity_detail,
    ):
        audit_record = AuditRecord(
            ip_address,
            user_id,
            user_name,
            system_id,
            system_name,
            activity_type,
            activity_resource,
            activity_detail,
        )
        db.session.add(audit_record)
        db.session.commit()
