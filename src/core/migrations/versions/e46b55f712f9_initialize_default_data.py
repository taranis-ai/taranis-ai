"""initialize default data

Revision ID: e46b55f712f9
Revises: 094b85ef4dcf
Create Date: 2022-06-03 11:08:51.663784

"""
from enum import Enum, auto
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


# revision identifiers, used by Alembic.
revision = 'e46b55f712f9'
down_revision = '094b85ef4dcf'
branch_labels = None
depends_on = None


class PermissionREVe46b55f712f9(Base):
    __tablename__ = 'permission'

    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())


class RoleREVe46b55f712f9(Base):
    __tablename__ = 'role'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(64), unique=True, nullable=False)
    description = sa.Column(sa.String())
    permissions = orm.relationship(PermissionREVe46b55f712f9, secondary='role_permission')

    def __init__(self, name, description, permissions):
        self.id = None
        self.name = name
        self.description = description
        self.permissions = permissions

class RolePermissionREVe46b55f712f9(Base):
    __tablename__ = 'role_permission'
    role_id = sa.Column(sa.Integer, sa.ForeignKey('role.id'), primary_key=True)
    permission_id = sa.Column(sa.String, sa.ForeignKey('permission.id'), primary_key=True)

class AttributeTypeREVe46b55f712f9(Enum):
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    RADIO = auto()
    ENUM = auto()
    TEXT = auto()
    RICH_TEXT = auto()
    DATE = auto()
    TIME = auto()
    DATE_TIME = auto()
    LINK = auto()
    ATTACHMENT = auto()
    TLP = auto()
    CPE = auto()
    CVE = auto()
    CVSS = auto()

class AttributeValidatorREVe46b55f712f9(Enum):
    NONE = auto()
    EMAIL = auto()
    NUMBER = auto()
    RANGE = auto()
    REGEXP = auto()

class AttributeREVe46b55f712f9(Base):
    __tablename__ = 'attribute'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String())
    type = sa.Column(sa.Enum(AttributeTypeREVe46b55f712f9))
    default_value = sa.Column(sa.String())
    validator = sa.Column(sa.Enum(AttributeValidatorREVe46b55f712f9))
    validator_parameter = sa.Column(sa.String())

    def __init__(self, name, description, type, default_value, validator, validator_parameter):
        self.id = None
        self.name = name
        self.description = description
        self.type = type
        self.default_value = default_value
        self.validator = validator
        self.validator_parameter = validator_parameter

class AttributeEnumREVe46b55f712f9(Base):
    __tablename__ = 'attribute_enum'

    id = sa.Column(sa.Integer, primary_key=True)
    index = sa.Column(sa.Integer)
    value = sa.Column(sa.String(), nullable=False)
    description = sa.Column(sa.String())
    imported = sa.Column(sa.Boolean, default=False)
    attribute_id = sa.Column(sa.Integer, sa.ForeignKey('attribute.id'))

    def __init__(self, index, value, description, attribute_id):
        self.id = None
        self.index = index
        self.value = value
        self.description = description
        self.attribute_id = attribute_id


class AttributeGroupItemREVe46b55f712f9(Base):
    __tablename__ = 'attribute_group_item'

    id = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.String())
    description = sa.Column(sa.String())
    index = sa.Column(sa.Integer)
    min_occurrence = sa.Column(sa.Integer)
    max_occurrence = sa.Column(sa.Integer)
    attribute_group_id = sa.Column(sa.Integer, sa.ForeignKey('attribute_group.id'))
    attribute_id = sa.Column(sa.Integer, sa.ForeignKey('attribute.id'))

    def __init__(self, title, description, index, min_occurrence, max_occurrence, attribute_group_id, attribute_id):
        self.id = None
        self.title = title
        self.description = description
        self.index = index
        self.min_occurrence = min_occurrence
        self.max_occurrence = max_occurrence
        self.attribute_group_id = attribute_group_id
        self.attribute_id = attribute_id

class AttributeGroupREVe46b55f712f9(Base):
    __tablename__ = 'attribute_group'

    id = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.String())
    description = sa.Column(sa.String())
    section = sa.Column(sa.Integer)
    section_title = sa.Column(sa.String())
    index = sa.Column(sa.Integer)
    report_item_type_id = sa.Column(sa.Integer, sa.ForeignKey('report_item_type.id'))

    def __init__(self, title, description, section, section_title, index, report_item_type_id):
        self.id = None
        self.title = title
        self.description = description
        self.section = section
        self.section_title = section_title
        self.index = index
        self.report_item_type_id = report_item_type_id

class ReportItemTypeREVe46b55f712f9(Base):
    __tablename__ = 'report_item_type'

    id = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.String())
    description = sa.Column(sa.String())

    def __init__(self, title, description):
        self.id = None
        self.title = title
        self.description = description


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # if no roles exist, add the default Admin role
    if not session.query(RoleREVe46b55f712f9).all():
        print('Adding default Admin role.', flush=True)
        admin_role = RoleREVe46b55f712f9('Admin', 'Administrator role', session.query(PermissionREVe46b55f712f9).all())
        session.add(admin_role)
        session.commit()

    # add attribute types
    if not session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first():
        print('Adding default Text attribute.', flush=True)
        attr_string = AttributeREVe46b55f712f9("Text", "Simple text box", AttributeTypeREVe46b55f712f9.STRING, None, None, None)
        session.add(attr_string)
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="Text Area").first():
        print('Adding default Text Area attribute.', flush=True)
        attr_text = AttributeREVe46b55f712f9("Text Area", "Simple text area", AttributeTypeREVe46b55f712f9.TEXT, None, None, None)
        session.add(attr_text)
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="TLP").first():
        print('Adding default TLP attribute.', flush=True)
        attr_tlp = AttributeREVe46b55f712f9("TLP", "Traffic Light Protocol element", AttributeTypeREVe46b55f712f9.TLP, None, None, None)
        session.add(attr_tlp)
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="CPE").first():
        print('Adding default CPE attribute.', flush=True)
        attr_cpe = AttributeREVe46b55f712f9("CPE", "Common Platform Enumeration element", AttributeTypeREVe46b55f712f9.CPE, None, None, None)
        session.add(attr_cpe)
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="CVSS").first():
        print('Adding default CVSS attribute.', flush=True)
        attr_cvss = AttributeREVe46b55f712f9("CVSS", "Common Vulnerability Scoring System element", AttributeTypeREVe46b55f712f9.CVSS, None, None, None)
        session.add(attr_cvss)
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="CVE").first():
        print('Adding default CVE attribute.', flush=True)
        attr_cve = AttributeREVe46b55f712f9("CVE", "Common Vulnerabilities and Exposures element", AttributeTypeREVe46b55f712f9.CVE, None, None, None)
        session.add(attr_cve)
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="Date").first():
        print('Adding default Date attribute.', flush=True)
        attr_date = AttributeREVe46b55f712f9("Date", "Date picker", AttributeTypeREVe46b55f712f9.DATE, None, None, None)
        session.add(attr_date)
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="Confidentiality").first():
        print('Adding default Confidentiality attribute.', flush=True)
        attr_conf = AttributeREVe46b55f712f9("Confidentiality", "Radio box for confidentiality level", AttributeTypeREVe46b55f712f9.RADIO, None, None, None)
        session.add(attr_conf)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "UNRESTRICTED", "", attr_conf.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "CLASSIFIED", "", attr_conf.id))
        session.add(AttributeEnumREVe46b55f712f9(2, "CONFIDENTIAL", "", attr_conf.id))
        session.add(AttributeEnumREVe46b55f712f9(3, "SECRET", "", attr_conf.id))
        session.add(AttributeEnumREVe46b55f712f9(4, "TOP SECRET", "", attr_conf.id))
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="Impact").first():
        print('Adding default Impact attribute.', flush=True)
        attr_impact = AttributeREVe46b55f712f9("Impact", "Combo box for impact level", AttributeTypeREVe46b55f712f9.ENUM, None, None, None)
        session.add(attr_impact)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "Malicious code execution affecting overall confidentiality, integrity, and availability of the system", "", attr_impact.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "Malicious code execution", "", attr_impact.id))
        session.add(AttributeEnumREVe46b55f712f9(2, "Denial of service", "", attr_impact.id))
        session.add(AttributeEnumREVe46b55f712f9(3, "Privilege escalation", "", attr_impact.id))
        session.add(AttributeEnumREVe46b55f712f9(4, "Information exposure", "", attr_impact.id))
        session.add(AttributeEnumREVe46b55f712f9(5, "Unauthorized access to the system", "", attr_impact.id))
        session.add(AttributeEnumREVe46b55f712f9(6, "Unauthorized change in system", "", attr_impact.id))
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="Additional Data").first():
        print('Adding default Additional Data attribute.', flush=True)
        attr_attribute_data = AttributeREVe46b55f712f9("Additional Data", "Radio box for MISP additional data", AttributeTypeREVe46b55f712f9.RADIO, None, None, None)
        session.add(attr_attribute_data)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "For Intrusion Detection System", "", attr_attribute_data.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "Disable Correlation", "", attr_attribute_data.id))
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="MISP Event Distribution").first():
        print('Adding default MISP Event Distribution attribute.', flush=True)
        attr_event_distribution = AttributeREVe46b55f712f9("MISP Event Distribution", "Combo box for MISP event distribution", AttributeTypeREVe46b55f712f9.ENUM, None, None, None)
        session.add(attr_event_distribution)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "Your organisation only", "", attr_event_distribution.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "This community only", "", attr_event_distribution.id))
        session.add(AttributeEnumREVe46b55f712f9(2, "Connected communities", "", attr_event_distribution.id))
        session.add(AttributeEnumREVe46b55f712f9(3, "All communities", "", attr_event_distribution.id))
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="MISP Event Threat Level").first():
        print('Adding default MISP Event Threat Level attribute.', flush=True)
        attr_event_threat_level = AttributeREVe46b55f712f9("MISP Event Threat Level", "Combo box for MISP event threat level", AttributeTypeREVe46b55f712f9.ENUM, None, None, None)
        session.add(attr_event_threat_level)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "High", "", attr_event_threat_level.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "Medium", "", attr_event_threat_level.id))
        session.add(AttributeEnumREVe46b55f712f9(2, "Low", "", attr_event_threat_level.id))
        session.add(AttributeEnumREVe46b55f712f9(3, "Undefined", "", attr_event_threat_level.id))
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="MISP Event Analysis").first():
        print('Adding default MISP Event Analysis attribute.', flush=True)
        attr_event_analysis = AttributeREVe46b55f712f9("MISP Event Analysis", "Combo box for MISP event analysis", AttributeTypeREVe46b55f712f9.ENUM, None, None, None)
        session.add(attr_event_analysis)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "Initial", "", attr_event_analysis.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "Ongoing", "", attr_event_analysis.id))
        session.add(AttributeEnumREVe46b55f712f9(2, "Completed", "", attr_event_analysis.id))
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="MISP Attribute Category").first():
        print('Adding default MISP Attribute Category attribute.', flush=True)
        attr_attribute_category = AttributeREVe46b55f712f9("MISP Attribute Category", "Combo box for MISP attribute category", AttributeTypeREVe46b55f712f9.ENUM, None, None, None)
        session.add(attr_attribute_category)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "Internal reference", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "Targeting data", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(2, "Antivirus detection", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(3, "Payload delivery", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(4, "Artifacts dropped", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(5, "Payload installation", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(6, "Persistence mechanism", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(7, "Network activity", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(8, "Payload type", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(9, "Attribution", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(10, "External analysis", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(11, "Financial fraud", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(12, "Support Tool", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(13, "Social network", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(14, "Person", "", attr_attribute_category.id))
        session.add(AttributeEnumREVe46b55f712f9(15, "Other", "", attr_attribute_category.id))
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="MISP Attribute Type").first():
        print('Adding default MISP Attribute Type attribute.', flush=True)
        attr_attribute_type = AttributeREVe46b55f712f9("MISP Attribute Type", "Combo box for MISP attribute type", AttributeTypeREVe46b55f712f9.ENUM, None, None, None)
        session.add(attr_attribute_type)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "md5", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "sha1", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(2, "sha256", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(3, "filename", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(4, "pbd", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(5, "filename|md5", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(6, "filename|sha1", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(7, "filename|sha256", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(8, "ip-src", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(9, "ip-dst", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(10, "hostname", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(11, "domain", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(12, "domain|ip", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(13, "email-src", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(14, "eppn", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(15, "email-dst", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(16, "email-subject", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(17, "email-attachment", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(18, "email-body", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(19, "float", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(20, "url", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(21, "http-method", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(22, "user-agent", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(23, "ja3-fingerprint-md5", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(24, "hassh-md5", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(25, "hasshserver-md5", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(26, "reg-key", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(27, "regkey|value", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(28, "AS", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(29, "snort", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(30, "bro", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(31, "zeek", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(32, "community-id", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(33, "pattern-in-traffic", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(34, "pattern-in-memory", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(35, "yara", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(36, "stix2-pattern", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(37, "sigma", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(38, "gene", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(39, "kusto-query", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(40, "mime-type", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(41, "identity-card-number", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(42, "cookie", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(43, "vulnerability", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(44, "weakness", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(45, "link", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(46, "comment", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(47, "text", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(48, "hex", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(49, "other", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(50, "named pipe", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(51, "mutex", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(52, "target-user", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(53, "target-email", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(54, "target-machine", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(55, "target-org", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(56, "target-location", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(57, "target-external", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(58, "btc", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(59, "dash", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(60, "xmr", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(61, "iban", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(62, "bic", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(63, "bank-account-nr", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(64, "aba-rtn", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(65, "bin", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(66, "cc-number", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(67, "prtn", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(68, "phone-number", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(69, "threat-actor", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(70, "campaign-name", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(71, "campaign-id", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(72, "malware-type", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(73, "uri", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(74, "authentihash", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(75, "ssdeep", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(76, "implash", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(77, "pahash", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(78, "impfuzzy", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(79, "sha224", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(80, "sha384", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(81, "sha512", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(82, "sha512/224", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(83, "sha512/256", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(84, "tlsh", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(85, "cdhash", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(86, "filename|authentihash", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(87, "filename|ssdeep", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(88, "filename|implash", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(89, "filename|impfuzzy", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(90, "filename|pehash", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(91, "filename|sha224", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(92, "filename|sha384", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(93, "filename|sha512", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(94, "filename|sha512/224", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(95, "filename|sha512/256", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(96, "filename|tlsh", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(97, "windows-scheduled-task", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(98, "windows-service-name", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(99, "windows-service-displayname", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(100, "whois-registrant-email", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(101, "whois-registrant-phone", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(102, "whois-registrant-name", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(103, "whois-registrant-org", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(104, "whois-registrar", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(105, "whois-creation-date", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(106, "x509-fingerprint-sha1", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(107, "x509-fingerprint-md5", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(108, "x509-fingerprint-sha256", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(109, "dns-soa-email", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(110, "size-in-bytes", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(111, "counter", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(112, "datetime", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(113, "cpe", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(114, "port", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(115, "ip-dist|port", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(116, "ip-src|port", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(117, "hostname|port", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(118, "mac-address", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(119, "mac-eui-64", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(120, "email-dst-display-name", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(121, "email-src-display-name", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(122, "email-header", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(123, "email-reply-to", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(124, "email-x-mailer", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(125, "email-mime-boundary", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(126, "email-thread-index", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(127, "email-message-id", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(128, "github-username", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(129, "github-repository", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(130, "githzb-organisation", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(131, "jabber-id", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(132, "twitter-id", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(133, "first-name", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(134, "middle-name", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(135, "last-name", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(136, "date-of-birth", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(137, "gender", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(138, "passport-number", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(139, "passport-country", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(140, "passport-expiration", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(141, "redress-number", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(142, "nationality", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(143, "visa-number", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(144, "issue-date-of-the-visa", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(145, "primary-residence", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(146, "country-of-residence", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(147, "special-service-request", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(148, "frequent-flyer-number", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(149, "travel-details", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(150, "payments-details", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(151, "place-port-of-original-embarkation", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(152, "passenger-name-record-locator-number", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(153, "mobile-application-id", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(154, "chrome-extension-id", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(155, "cortex", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(156, "boolean", "", attr_attribute_type.id))
        session.add(AttributeEnumREVe46b55f712f9(157, "anonymised", "", attr_attribute_type.id))
        session.commit()

    if not session.query(AttributeREVe46b55f712f9).filter_by(name="MISP Attribute Distribution").first():
        print('Adding default MISP Attribute Distribution attribute.', flush=True)
        attr_attribute_distribution = AttributeREVe46b55f712f9("MISP Attribute Distribution", "Combo box for MISP attribute type", AttributeTypeREVe46b55f712f9.ENUM, None, None, None)
        session.add(attr_attribute_distribution)
        session.commit()
        session.add(AttributeEnumREVe46b55f712f9(0, "Your organisation only", "", attr_attribute_distribution.id))
        session.add(AttributeEnumREVe46b55f712f9(1, "This community only", "", attr_attribute_distribution.id))
        session.add(AttributeEnumREVe46b55f712f9(2, "Connected communities", "", attr_attribute_distribution.id))
        session.add(AttributeEnumREVe46b55f712f9(3, "All communities", "", attr_attribute_distribution.id))
        session.add(AttributeEnumREVe46b55f712f9(4, "Inherit event", "", attr_attribute_distribution.id))
        session.commit()

    # add attribute groups and report item type
    if not session.query(ReportItemTypeREVe46b55f712f9).filter_by(title="Vulnerability Report").first():
        print('Adding default Vulnerability report type.', flush=True)
        report_item_type = ReportItemTypeREVe46b55f712f9("Vulnerability Report", "Basic report type")
        session.add(report_item_type)
        session.commit()

        group1 = AttributeGroupREVe46b55f712f9("Vulnerability", "", None, None, 0, report_item_type.id)
        session.add(group1)
        group2 = AttributeGroupREVe46b55f712f9("Identify and Act", "", None, None, 0, report_item_type.id)
        session.add(group2)
        group3 = AttributeGroupREVe46b55f712f9("Resources", "", None, None, 0, report_item_type.id)
        session.add(group3)
        session.commit()

        session.add(AttributeGroupItemREVe46b55f712f9("CVSS", "", 0, 1, 1, group1.id, session.query(AttributeREVe46b55f712f9).filter_by(name="CVSS").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("TLP", "", 1, 1, 1, group1.id, session.query(AttributeREVe46b55f712f9).filter_by(name="TLP").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Confidentiality", "", 2, 1, 1, group1.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Confidentiality").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Description", "", 3, 1, 1, group1.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text Area").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Exposure Date", "", 4, 1, 1, group1.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Date").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Update Date", "", 5, 1, 1, group1.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Date").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("CVE", "", 6, 0, 1000, group1.id, session.query(AttributeREVe46b55f712f9).filter_by(name="CVE").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Impact", "", 7, 0, 1000, group1.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Impact").first().id))
        session.commit()

        session.add(AttributeGroupItemREVe46b55f712f9("Affected systems", "", 0, 0, 1000, group2.id, session.query(AttributeREVe46b55f712f9).filter_by(name="CPE").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("IOC", "", 1, 0, 1000, group2.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Recommendations", "", 2, 1, 1, group2.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text Area").first().id))
        session.commit()

        session.add(AttributeGroupItemREVe46b55f712f9("Links", "", 0, 0, 1000, group3.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.commit()

    if not session.query(ReportItemTypeREVe46b55f712f9).filter_by(title="MISP Report").first():
        print('Adding default MISP report type.', flush=True)
        report_item_type = ReportItemTypeREVe46b55f712f9("MISP Report", "MISP report type")
        session.add(report_item_type)
        session.commit()

        group4 = AttributeGroupREVe46b55f712f9("Event", "", None, None, 0, report_item_type.id)
        session.add(group4)
        group5 = AttributeGroupREVe46b55f712f9("Attribute", "", None, None, 0, report_item_type.id)
        session.add(group5)
        session.commit()

        session.add(AttributeGroupItemREVe46b55f712f9("Event distribution", "", 0, 1, 1, group4.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Event threat level", "", 1, 1, 1, group4.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Event analysis", "", 2, 1, 1, group4.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Event info", "", 2, 1, 1, group4.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.commit()

        session.add(AttributeGroupItemREVe46b55f712f9("Attribute category", "", 0, 1, 1, group5.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Attribute type", "", 1, 1, 1, group5.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Attribute distribution", "", 2, 1, 1, group5.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Attribute value", "", 3, 1, 1, group5.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text Area").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Attribute contextual comment", "", 4, 1, 1, group5.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Text").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Attribute additional information", "", 5, 1, 1, group5.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Additional Data").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("First seen date", "", 6, 1, 1, group5.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Date").first().id))
        session.add(AttributeGroupItemREVe46b55f712f9("Last seen date", "", 7, 1, 1, group5.id, session.query(AttributeREVe46b55f712f9).filter_by(name="Date").first().id))
        session.commit()


def downgrade():
    pass
