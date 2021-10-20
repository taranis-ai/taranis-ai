from model.role import Role
from model.permission import Permission
from model.user import User
from model.address import Address
from model.organization import Organization
from model.collectors_node import CollectorsNode
from model.collector import Collector
from model.parameter import Parameter
from model.parameter_value import ParameterValue
from model.attribute import Attribute, AttributeEnum
from taranisng.schema.attribute import AttributeType
from taranisng.schema.parameter import ParameterType
from model.report_item_type import ReportItemType, AttributeGroup, AttributeGroupItem
from model.osint_source import OSINTSource, OSINTSourceGroup
from managers import db_manager
import sys

from sqlalchemy.exc import IntegrityError


def main(db):
    user_role = Role(None, 'User', 'Test user role', [])
    user_role.permissions.append(Permission.find("ASSESS_ACCESS"))
    user_role.permissions.append(Permission.find("ASSESS_CREATE"))
    user_role.permissions.append(Permission.find("ASSESS_UPDATE"))
    user_role.permissions.append(Permission.find("ASSESS_DELETE"))
    user_role.permissions.append(Permission.find("ANALYZE_ACCESS"))
    user_role.permissions.append(Permission.find("ANALYZE_CREATE"))
    user_role.permissions.append(Permission.find("ANALYZE_UPDATE"))
    user_role.permissions.append(Permission.find("ANALYZE_DELETE"))
    user_role.permissions.append(Permission.find("PUBLISH_ACCESS"))
    user_role.permissions.append(Permission.find("PUBLISH_CREATE"))
    user_role.permissions.append(Permission.find("PUBLISH_UPDATE"))
    user_role.permissions.append(Permission.find("PUBLISH_DELETE"))
    user_role.permissions.append(Permission.find("PUBLISH_PRODUCT"))
    db.session.add(user_role)

    address = Address("Budatinska 30", "Bratislava", "851 06", "Slovakia")
    organization = Organization(None, "SK-CERT", "", address)
    db.session.add(organization)

    role = Role.find_by_name('User')

    user = User(None, 'user', 'Test User', [], [], [])
    user.roles.append(role)
    user.organizations.append(organization)

    db.session.add(user)
    db.session.commit()

    admin_role = Role(None, 'Admin', 'Test admin role', [])
    
    admin_role.permissions.append(Permission.find('CONFIG_ACCESS'))

    admin_role.permissions.append(Permission.find('CONFIG_ORGANIZATION_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_ORGANIZATION_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_ORGANIZATION_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_ORGANIZATION_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_USER_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_USER_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_USER_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_USER_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_ROLE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_ROLE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_ROLE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_ROLE_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_ACL_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_ACL_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_ACL_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_ACL_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_PRODUCT_TYPE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_PRODUCT_TYPE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_PRODUCT_TYPE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_PRODUCT_TYPE_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_ATTRIBUTE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_ATTRIBUTE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_ATTRIBUTE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_ATTRIBUTE_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_REPORT_TYPE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_REPORT_TYPE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_REPORT_TYPE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_REPORT_TYPE_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_WORD_LIST_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_WORD_LIST_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_WORD_LIST_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_WORD_LIST_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_COLLECTORS_NODE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_COLLECTORS_NODE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_COLLECTORS_NODE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_COLLECTORS_NODE_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_OSINT_SOURCE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_OSINT_SOURCE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_OSINT_SOURCE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_OSINT_SOURCE_DELETE'))
    admin_role.permissions.append(Permission.find('CONFIG_OSINT_SOURCE_GROUP_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_OSINT_SOURCE_GROUP_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_OSINT_SOURCE_GROUP_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_OSINT_SOURCE_GROUP_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_REMOTE_ACCESS_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_REMOTE_ACCESS_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_REMOTE_ACCESS_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_REMOTE_ACCESS_DELETE'))
    admin_role.permissions.append(Permission.find('CONFIG_REMOTE_NODE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_REMOTE_NODE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_REMOTE_NODE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_REMOTE_NODE_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_PRESENTERS_NODE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_PRESENTERS_NODE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_PRESENTERS_NODE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_PRESENTERS_NODE_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_PUBLISHERS_NODE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_PUBLISHERS_NODE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_PUBLISHERS_NODE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_PUBLISHERS_NODE_DELETE'))
    admin_role.permissions.append(Permission.find('CONFIG_PUBLISHER_PRESET_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_PUBLISHER_PRESET_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_PUBLISHER_PRESET_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_PUBLISHER_PRESET_DELETE'))
    
    admin_role.permissions.append(Permission.find('CONFIG_BOTS_NODE_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_BOTS_NODE_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_BOTS_NODE_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_BOTS_NODE_DELETE'))
    admin_role.permissions.append(Permission.find('CONFIG_BOT_PRESET_ACCESS'))
    admin_role.permissions.append(Permission.find('CONFIG_BOT_PRESET_CREATE'))
    admin_role.permissions.append(Permission.find('CONFIG_BOT_PRESET_UPDATE'))
    admin_role.permissions.append(Permission.find('CONFIG_BOT_PRESET_DELETE'))
    
    admin_role.permissions.append(Permission.find('ASSESS_ACCESS'))
    admin_role.permissions.append(Permission.find('ASSESS_CREATE'))
    admin_role.permissions.append(Permission.find('ASSESS_UPDATE'))
    admin_role.permissions.append(Permission.find('ASSESS_DELETE'))
    
    admin_role.permissions.append(Permission.find('MY_ASSETS_ACCESS'))
    admin_role.permissions.append(Permission.find('MY_ASSETS_CREATE'))
    admin_role.permissions.append(Permission.find('MY_ASSETS_CONFIG'))
    
    admin_role.permissions.append(Permission.find('ANALYZE_ACCESS'))
    admin_role.permissions.append(Permission.find('ANALYZE_CREATE'))
    admin_role.permissions.append(Permission.find('ANALYZE_UPDATE'))
    admin_role.permissions.append(Permission.find('ANALYZE_DELETE'))
    
    admin_role.permissions.append(Permission.find('PUBLISH_ACCESS'))
    admin_role.permissions.append(Permission.find('PUBLISH_CREATE'))
    admin_role.permissions.append(Permission.find('PUBLISH_UPDATE'))
    admin_role.permissions.append(Permission.find('PUBLISH_DELETE'))
    admin_role.permissions.append(Permission.find('PUBLISH_PRODUCT'))

    db.session.add(admin_role)

    role = Role.find_by_name('Admin')

    user = User(None, 'admin', 'Test Administrator', [], [], [])
    user.roles.append(role)
    user.organizations.append(organization)
    db.session.add(user)

    user = User(None, 'customer', 'Test Customer', [], [], [])
    user.permissions.append(Permission.find("MY_ASSETS_ACCESS"))
    user.permissions.append(Permission.find("MY_ASSETS_CREATE"))
    user.permissions.append(Permission.find("MY_ASSETS_CONFIG"))
    user.organizations.append(organization)
    db.session.add(user)

#     param1 = Parameter(None, "FEED_URL", "Feed URL", "Full url for RSS feed", ParameterType.STRING)
#     param2 = Parameter(None, "REFRESH_INTERVAL", "Refresh Interval", "How often is this collector queried for new data",
#                     ParameterType.NUMBER)
#     param3 = Parameter(None, "USER_AGENT", "User agent", "Type of user agent", ParameterType.STRING)

#     collector_rss = Collector("RSS Collector", "Collector for gathering data from RSS feeds", "RSS_COLLECTOR",
#                             [param1, param2, param3])

#     collectors_node = CollectorsNode(None, "Node A", "First collectors node", "http://127.0.0.1:5001", "12345", [])
#     collectors_node.collectors.append(collector_rss)
#     db.session.add(collectors_node)

#     value1 = ParameterValue("https://ics-cert.us-cert.gov/alerts/alerts.xml", param1)
#     value1.parameter = param1
#     value2 = ParameterValue("60", param2)
#     value2.parameter = param2
#     value3 = ParameterValue("Firefox: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:76.0) Gecko/20100101 Firefox/76.0",
#                             param3)
#     value3.parameter = param3

#     rss_source = OSINTSource(None, "RSS Feed", "Test RSS feed", collector_rss.id, [value1, value2, value3], [])
#     db.session.add(rss_source)

    attr_string = Attribute(None, "Text", "Simple text box", AttributeType.STRING, None, None, None, [])
    Attribute.create_attribute(attr_string)

    attr_text = Attribute(None, "Text Area", "Simple text area", AttributeType.TEXT, None, None, None, [])
    Attribute.create_attribute(attr_text)

    attr_tlp = Attribute(None, "TLP", "Traffic Light Protocol element", AttributeType.TLP, None, None, None, [])
    Attribute.create_attribute(attr_tlp)

    attr_cpe = Attribute(None, "CPE", "Common Platform Enumeration element", AttributeType.CPE, None, None, None, [])
    Attribute.create_attribute(attr_cpe)

    attr_cvss = Attribute(None, "CVSS", "Common Vulnerability Scoring System element", AttributeType.CVSS, None, None, None, [])
    Attribute.create_attribute(attr_cvss)

    attr_cve = Attribute(None, "CVE", "Common Vulnerabilities and Exposures element", AttributeType.CVE, None, None, None, [])
    Attribute.create_attribute(attr_cve)

    attr_date = Attribute(None, "Date", "Date picker", AttributeType.DATE, None, None, None, [])
    Attribute.create_attribute(attr_date)

    conf_enums = [AttributeEnum(None, 0, "UNRESTRICTED", ""), AttributeEnum(None, 1, "CLASSIFIED", ""),
                AttributeEnum(None, 2, "CONFIDENTIAL", ""), AttributeEnum(None, 3, "SECRET", ""),
                AttributeEnum(None, 4, "TOP SECRET", "")]
    attr_conf = Attribute(None, "Confidentiality", "Radio box for confidentiality level", AttributeType.RADIO, None, None,
                        None,
                        conf_enums)
    Attribute.create_attribute(attr_conf)

    impact_enums = [AttributeEnum(None, 0,
                                "Malicious code execution affecting overall confidentiality, integrity, and availability of the system",
                                ""),
                    AttributeEnum(None, 1, "Malicious code execution", ""),
                    AttributeEnum(None, 2, "Denial of service", ""),
                    AttributeEnum(None, 3, "Privilege escalation", ""),
                    AttributeEnum(None, 4, "Information exposure", ""),
                    AttributeEnum(None, 5, "Unauthorized access to the system", ""),
                    AttributeEnum(None, 6, "Unauthorized change in system", "")]
    attr_impact = Attribute(None, "Impact", "Combo box for impact level", AttributeType.ENUM, None, None, None,
                            impact_enums)
    Attribute.create_attribute(attr_impact)

    items1 = [AttributeGroupItem(None, "CVSS", "", 0, 1, 1, attr_cvss.id),
            AttributeGroupItem(None, "TLP", "", 1, 1, 1, attr_tlp.id),
            AttributeGroupItem(None, "Confidentiality", "", 2, 1, 1, attr_conf.id),
            AttributeGroupItem(None, "Description", "", 3, 1, 1, attr_text.id),
            AttributeGroupItem(None, "Exposure Date", "", 4, 1, 1, attr_date.id),
            AttributeGroupItem(None, "Update Date", "", 5, 1, 1, attr_date.id),
            AttributeGroupItem(None, "CVE", "", 6, 0, 1000, attr_cve.id),
            AttributeGroupItem(None, "Impact", "", 7, 0, 1000, attr_impact.id)]
    group1 = AttributeGroup(None, "Vulnerability", "", None, None, 0, items1)

    items2 = [AttributeGroupItem(None, "Affected systems", "", 0, 0, 1000, attr_cpe.id),
            AttributeGroupItem(None, "IOC", "", 1, 0, 1000, attr_string.id),
            AttributeGroupItem(None, "Recommendations", "", 2, 1, 1, attr_text.id)]
    group2 = AttributeGroup(None, "Identify and Act", "", None, None, 0, items2)

    items3 = [AttributeGroupItem(None, "Links", "", 0, 0, 1000, attr_string.id)]
    group3 = AttributeGroup(None, "Resources", "", None, None, 0, items3)

    report_type = ReportItemType(None, "Vulnerability Report", "Basic report type", [group1, group2, group3])
    db.session.add(report_type)

    db.session.commit()

#     group = OSINTSourceGroup(None, "RSS Feeds", "Desc", [])
#     group.osint_sources = OSINTSource.get_all()
#     db.session.add(group)
#     db.session.commit()

    '''
    MISP Report
    '''

    # event_distribution_enums = [AttributeEnum(0, "Your organisation only", ""),
    #                             AttributeEnum(1, "This community only", ""),
    #                             AttributeEnum(2, "Connected communities", ""),
    #                             AttributeEnum(3, "All communities", "")]
    # attr_event_distribution = Attribute("MISP Event Distribution", "Combo box for MISP event distribution",
    #                                     AttributeType.ENUM, None, None, None, event_distribution_enums)
    # db.session.add(attr_event_distribution)
    # db.session.commit()
    #
    # event_threat_level_enums = [AttributeEnum(0, "High", ""),
    #                             AttributeEnum(1, "Medium", ""),
    #                             AttributeEnum(2, "Low", ""),
    #                             AttributeEnum(3, "Undefined", "")]
    # attr_event_threat_level = Attribute("MISP Event Threat Level", "Combo box for MISP event threat level",
    #                                     AttributeType.ENUM, None, None, None, event_threat_level_enums)
    # db.session.add(attr_event_threat_level)
    # db.session.commit()
    #
    # event_analysis_enums = [AttributeEnum(0, "Initial", ""),
    #                         AttributeEnum(1, "Ongoing", ""),
    #                         AttributeEnum(2, "Completed", "")]
    # attr_event_analysis = Attribute("MISP Event Analysis", "Combo box for MISP event analysis",
    #                                 AttributeType.ENUM, None, None, None, event_analysis_enums)
    # db.session.add(attr_event_analysis)
    # db.session.commit()
    #
    # attribute_category_enums = [AttributeEnum(0, "Internal reference", ""),
    #                             AttributeEnum(1, "Targeting data", ""),
    #                             AttributeEnum(2, "Antivirus detection", ""),
    #                             AttributeEnum(3, "Payload delivery", ""),
    #                             AttributeEnum(4, "Artifacts dropped", ""),
    #                             AttributeEnum(5, "Payload installation", ""),
    #                             AttributeEnum(6, "Persistence mechanism", ""),
    #                             AttributeEnum(7, "Network activity", ""),
    #                             AttributeEnum(8, "Payload type", ""),
    #                             AttributeEnum(9, "Attribution", ""),
    #                             AttributeEnum(10, "External analysis", ""),
    #                             AttributeEnum(11, "Financial fraud", ""),
    #                             AttributeEnum(12, "Support Tool", ""),
    #                             AttributeEnum(13, "Social network", ""),
    #                             AttributeEnum(14, "Person", ""),
    #                             AttributeEnum(15, "Other", "")]
    # attr_attribute_category = Attribute("MISP Attribute Category", "Combo box for MISP attribute category",
    #                                     AttributeType.ENUM, None, None, None, attribute_category_enums)
    # db.session.add(attr_attribute_category)
    # db.session.commit()
    #
    # attribute_type_enums = [AttributeEnum(0, "md5", ""),
    #                         AttributeEnum(1, "sha1", ""),
    #                         AttributeEnum(2, "sha256", ""),
    #                         AttributeEnum(3, "filename", ""),
    #                         AttributeEnum(4, "pbd", ""),
    #                         AttributeEnum(5, "filename|md5", ""),
    #                         AttributeEnum(6, "filename|sha1", ""),
    #                         AttributeEnum(7, "filename|sha256", ""),
    #                         AttributeEnum(8, "ip-src", ""),
    #                         AttributeEnum(9, "ip-dst", ""),
    #                         AttributeEnum(10, "hostname", ""),
    #                         AttributeEnum(11, "domain", ""),
    #                         AttributeEnum(12, "domain|ip", ""),
    #                         AttributeEnum(13, "email-src", ""),
    #                         AttributeEnum(14, "eppn", ""),
    #                         AttributeEnum(15, "email-dst", ""),
    #                         AttributeEnum(16, "email-subject", ""),
    #                         AttributeEnum(17, "email-attachment", ""),
    #                         AttributeEnum(18, "email-body", ""),
    #                         AttributeEnum(19, "float", ""),
    #                         AttributeEnum(20, "url", ""),
    #                         AttributeEnum(21, "http-method", ""),
    #                         AttributeEnum(22, "user-agent", ""),
    #                         AttributeEnum(23, "ja3-fingerprint-md5", ""),
    #                         AttributeEnum(24, "hassh-md5", ""),
    #                         AttributeEnum(25, "hasshserver-md5", ""),
    #                         AttributeEnum(26, "reg-key", ""),
    #                         AttributeEnum(27, "regkey|value", ""),
    #                         AttributeEnum(28, "AS", ""),
    #                         AttributeEnum(29, "snort", ""),
    #                         AttributeEnum(30, "bro", ""),
    #                         AttributeEnum(31, "zeek", ""),
    #                         AttributeEnum(32, "community-id", ""),
    #                         AttributeEnum(33, "pattern-in-traffic", ""),
    #                         AttributeEnum(34, "pattern-in-memory", ""),
    #                         AttributeEnum(35, "yara", ""),
    #                         AttributeEnum(36, "stix2-pattern", ""),
    #                         AttributeEnum(37, "sigma", ""),
    #                         AttributeEnum(38, "gene", ""),
    #                         AttributeEnum(39, "kusto-query", ""),
    #                         AttributeEnum(40, "mime-type", ""),
    #                         AttributeEnum(41, "identity-card-number", ""),
    #                         AttributeEnum(42, "cookie", ""),
    #                         AttributeEnum(43, "vulnerability", ""),
    #                         AttributeEnum(44, "weakness", ""),
    #                         AttributeEnum(45, "link", ""),
    #                         AttributeEnum(46, "comment", ""),
    #                         AttributeEnum(47, "text", ""),
    #                         AttributeEnum(48, "hex", ""),
    #                         AttributeEnum(49, "other", ""),
    #                         AttributeEnum(50, "named pipe", ""),
    #                         AttributeEnum(51, "mutex", ""),
    #                         AttributeEnum(52, "target-user", ""),
    #                         AttributeEnum(53, "target-email", ""),
    #                         AttributeEnum(54, "target-machine", ""),
    #                         AttributeEnum(55, "target-org", ""),
    #                         AttributeEnum(56, "target-location", ""),
    #                         AttributeEnum(57, "target-external", ""),
    #                         AttributeEnum(58, "btc", ""),
    #                         AttributeEnum(59, "dash", ""),
    #                         AttributeEnum(60, "xmr", ""),
    #                         AttributeEnum(61, "iban", ""),
    #                         AttributeEnum(62, "bic", ""),
    #                         AttributeEnum(63, "bank-account-nr", ""),
    #                         AttributeEnum(64, "aba-rtn", ""),
    #                         AttributeEnum(65, "bin", ""),
    #                         AttributeEnum(66, "cc-number", ""),
    #                         AttributeEnum(67, "prtn", ""),
    #                         AttributeEnum(68, "phone-number", ""),
    #                         AttributeEnum(69, "threat-actor", ""),
    #                         AttributeEnum(70, "campaign-name", ""),
    #                         AttributeEnum(71, "campaign-id", ""),
    #                         AttributeEnum(72, "malware-type", ""),
    #                         AttributeEnum(73, "uri", ""),
    #                         AttributeEnum(74, "authentihash", ""),
    #                         AttributeEnum(75, "ssdeep", ""),
    #                         AttributeEnum(76, "implash", ""),
    #                         AttributeEnum(77, "pahash", ""),
    #                         AttributeEnum(78, "impfuzzy", ""),
    #                         AttributeEnum(79, "sha224", ""),
    #                         AttributeEnum(80, "sha384", ""),
    #                         AttributeEnum(81, "sha512", ""),
    #                         AttributeEnum(82, "sha512/224", ""),
    #                         AttributeEnum(83, "sha512/256", ""),
    #                         AttributeEnum(84, "tlsh", ""),
    #                         AttributeEnum(85, "cdhash", ""),
    #                         AttributeEnum(86, "filename|authentihash", ""),
    #                         AttributeEnum(87, "filename|ssdeep", ""),
    #                         AttributeEnum(88, "filename|implash", ""),
    #                         AttributeEnum(89, "filename|impfuzzy", ""),
    #                         AttributeEnum(90, "filename|pehash", ""),
    #                         AttributeEnum(91, "filename|sha224", ""),
    #                         AttributeEnum(92, "filename|sha384", ""),
    #                         AttributeEnum(93, "filename|sha512", ""),
    #                         AttributeEnum(94, "filename|sha512/224", ""),
    #                         AttributeEnum(95, "filename|sha512/256", ""),
    #                         AttributeEnum(96, "filename|tlsh", ""),
    #                         AttributeEnum(97, "windows-scheduled-task", ""),
    #                         AttributeEnum(98, "windows-service-name", ""),
    #                         AttributeEnum(99, "windows-service-displayname", ""),
    #                         AttributeEnum(100, "whois-registrant-email", ""),
    #                         AttributeEnum(101, "whois-registrant-phone", ""),
    #                         AttributeEnum(102, "whois-registrant-name", ""),
    #                         AttributeEnum(103, "whois-registrant-org", ""),
    #                         AttributeEnum(104, "whois-registrar", ""),
    #                         AttributeEnum(105, "whois-creation-date", ""),
    #                         AttributeEnum(106, "x509-fingerprint-sha1", ""),
    #                         AttributeEnum(107, "x509-fingerprint-md5", ""),
    #                         AttributeEnum(108, "x509-fingerprint-sha256", ""),
    #                         AttributeEnum(109, "dns-soa-email", ""),
    #                         AttributeEnum(110, "size-in-bytes", ""),
    #                         AttributeEnum(111, "counter", ""),
    #                         AttributeEnum(112, "datetime", ""),
    #                         AttributeEnum(113, "cpe", ""),
    #                         AttributeEnum(114, "port", ""),
    #                         AttributeEnum(115, "ip-dist|port", ""),
    #                         AttributeEnum(116, "ip-src|port", ""),
    #                         AttributeEnum(117, "hostname|port", ""),
    #                         AttributeEnum(118, "mac-address", ""),
    #                         AttributeEnum(119, "mac-eui-64", ""),
    #                         AttributeEnum(120, "email-dst-display-name", ""),
    #                         AttributeEnum(121, "email-src-display-name", ""),
    #                         AttributeEnum(122, "email-header", ""),
    #                         AttributeEnum(123, "email-reply-to", ""),
    #                         AttributeEnum(124, "email-x-mailer", ""),
    #                         AttributeEnum(125, "email-mime-boundary", ""),
    #                         AttributeEnum(126, "email-thread-index", ""),
    #                         AttributeEnum(127, "email-message-id", ""),
    #                         AttributeEnum(128, "github-username", ""),
    #                         AttributeEnum(129, "github-repository", ""),
    #                         AttributeEnum(130, "githzb-organisation", ""),
    #                         AttributeEnum(131, "jabber-id", ""),
    #                         AttributeEnum(132, "twitter-id", ""),
    #                         AttributeEnum(133, "first-name", ""),
    #                         AttributeEnum(134, "middle-name", ""),
    #                         AttributeEnum(135, "last-name", ""),
    #                         AttributeEnum(136, "date-of-birth", ""),
    #                         AttributeEnum(137, "gender", ""),
    #                         AttributeEnum(138, "passport-number", ""),
    #                         AttributeEnum(139, "passport-country", ""),
    #                         AttributeEnum(140, "passport-expiration", ""),
    #                         AttributeEnum(141, "redress-number", ""),
    #                         AttributeEnum(142, "nationality", ""),
    #                         AttributeEnum(143, "visa-number", ""),
    #                         AttributeEnum(144, "issue-date-of-the-visa", ""),
    #                         AttributeEnum(145, "primary-residence", ""),
    #                         AttributeEnum(146, "country-of-residence", ""),
    #                         AttributeEnum(147, "special-service-request", ""),
    #                         AttributeEnum(148, "frequent-flyer-number", ""),
    #                         AttributeEnum(149, "travel-details", ""),
    #                         AttributeEnum(150, "payments-details", ""),
    #                         AttributeEnum(151, "place-port-of-original-embarkation", ""),
    #                         AttributeEnum(152, "passenger-name-record-locator-number", ""),
    #                         AttributeEnum(153, "mobile-application-id", ""),
    #                         AttributeEnum(154, "chrome-extension-id", ""),
    #                         AttributeEnum(155, "cortex", ""),
    #                         AttributeEnum(156, "boolean", ""),
    #                         AttributeEnum(157, "anonymised", "")]
    # attr_attribute_type = Attribute("MISP Attribute Type", "Combo box for MISP attribute type",
    #                                 AttributeType.ENUM, None, None, None, attribute_type_enums)
    # db.session.add(attr_attribute_type)
    # db.session.commit()
    #
    # attribute_distribution_enums = [AttributeEnum(0, "Your organisation only", ""),
    #                                 AttributeEnum(1, "This community only", ""),
    #                                 AttributeEnum(2, "Connected communities", ""),
    #                                 AttributeEnum(3, "All communities", ""),
    #                                 AttributeEnum(4, "Inherit event", "")]
    # attr_attribute_distribution = Attribute("MISP Attribute Distribution", "Combo box for MISP attribute type",
    #                                         AttributeType.ENUM, None, None, None, attribute_distribution_enums)
    # db.session.add(attr_attribute_distribution)
    # db.session.commit()
    #
    # attribute_data_enums = [AttributeEnum(0, "For Intrusion Detection System", ""),
    #                         AttributeEnum(2, "Disable Correlation", "")]
    # attr_attribute_data = Attribute("Data", "Radio box for additional data", AttributeType.RADIO, None,
    #                                 None, None, attribute_data_enums)
    # db.session.add(attr_attribute_data)
    # db.session.commit()
    #
    # items4 = [AttributeGroupItem("Event distribution", "", 0, 1, 1, attr_string.id),
    #           AttributeGroupItem("Event threat level", "", 1, 1, 1, attr_string.id),
    #           AttributeGroupItem("Event analysis", "", 2, 1, 1, attr_string.id),
    #           AttributeGroupItem("Event info", "", 3, 1, 1, attr_string.id)]
    # group4 = AttributeGroup("Event", "", None, None, 0, items4)
    #
    # items5 = [AttributeGroupItem("Attribute category", "", 0, 1, 1, attr_string.id),
    #           AttributeGroupItem("Attribute type", "", 1, 1, 1, attr_string.id),
    #           AttributeGroupItem("Attribute distribution", "", 2, 1, 1, attr_string.id),
    #           AttributeGroupItem("Attribute value", "", 3, 1, 1, attr_text.id),
    #           AttributeGroupItem("Attribute contextual comment", "", 4, 1, 1, attr_string.id),
    #           AttributeGroupItem("Attribute additional information", "", 5, 1, 1, attr_attribute_data.id),
    #           AttributeGroupItem("First seen date", "", 6, 1, 1, attr_date.id),
    #           AttributeGroupItem("Last seen date", "", 7, 1, 1, attr_date.id)
    #           ]
    #
    # group5 = AttributeGroup("Attribute", "", None, None, 0, items5)
    #
    # report_type = ReportItemType("MISP Report", "MISP report type", [group4, group5])
    # db.session.add(report_type)
    # db.session.commit()

    '''
    MISP without combo boxes
    '''
    attribute_data_enums = [AttributeEnum(None, 0, "For Intrusion Detection System", ""),
                            AttributeEnum(None, 1, "Disable Correlation", "")]
    attr_attribute_data = Attribute(None, "Data", "Radio box for additional data", AttributeType.RADIO, None,
                                    None, None, attribute_data_enums)
    db.session.add(attr_attribute_data)
    db.session.commit()

    items4 = [AttributeGroupItem(None, "Event distribution", "", 0, 1, 1, attr_string.id),
            AttributeGroupItem(None, "Event threat level", "", 1, 1, 1, attr_string.id),
            AttributeGroupItem(None, "Event analysis", "", 2, 1, 1, attr_string.id),
            AttributeGroupItem(None, "Event info", "", 3, 1, 1, attr_string.id)]
    group4 = AttributeGroup(None, "Event", "", None, None, 0, items4)

    items5 = [AttributeGroupItem(None, "Attribute category", "", 0, 1, 1, attr_string.id),
            AttributeGroupItem(None, "Attribute type", "", 1, 1, 1, attr_string.id),
            AttributeGroupItem(None, "Attribute distribution", "", 2, 1, 1, attr_string.id),
            AttributeGroupItem(None, "Attribute value", "", 3, 1, 1, attr_text.id),
            AttributeGroupItem(None, "Attribute contextual comment", "", 4, 1, 1, attr_string.id),
            AttributeGroupItem(None, "Attribute additional information", "", 5, 1, 1, attr_attribute_data.id),
            AttributeGroupItem(None, "First seen date", "", 6, 1, 1, attr_date.id),
            AttributeGroupItem(None, "Last seen date", "", 7, 1, 1, attr_date.id)
            ]

    group5 = AttributeGroup(None, "Attribute", "", None, None, 0, items5)

    report_type = ReportItemType(None, "MISP Report", "MISP report type", [group4, group5])
    db.session.add(report_type)
    db.session.commit()


def run(db):
    try:
        main(db_manager.db)
    except IntegrityError as exc:
        print(exc, file=sys.stderr)
        print('Detected UniqueViolation exception. Probably the '
              'sample data has already been imported. If not, please report '
              'this as bug.', file=sys.stderr)


if __name__ == '__main__':
    run(db_manager.db)
    sys.exit()
