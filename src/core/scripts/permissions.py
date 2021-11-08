import sys

from managers import db_manager
from model.permission import Permission

def run(db):
    Permission.add("ANALYZE_ACCESS", "Analyze access", "Access to Analyze module")
    Permission.add("ANALYZE_CREATE", "Analyze create", "Create report item")
    Permission.add("ANALYZE_UPDATE", "Analyze update", "Update report item")
    Permission.add("ANALYZE_DELETE", "Analyze delete", "Delete report item")

    Permission.add("ASSESS_ACCESS", "Assess access", "Access to Assess module")
    Permission.add("ASSESS_CREATE", "Assess create", "Create news item")
    Permission.add("ASSESS_UPDATE", "Assess update", "Update news item")
    Permission.add("ASSESS_DELETE", "Assess delete", "Delete news item")

    Permission.add("MY_ASSETS_ACCESS", "My Assets access", "Access to My Assets module")
    Permission.add("MY_ASSETS_CREATE", "My Assets create", "Creation of products in My Assets module")
    Permission.add("MY_ASSETS_CONFIG", "My Assets config", "Configuration of access and groups in My Assets module")

    Permission.add("CONFIG_ACCESS", "Configuration access", "Access to Configuration module")

    Permission.add("CONFIG_ORGANIZATION_ACCESS", "Config organizations access", "Access to attributes configuration")
    Permission.add("CONFIG_ORGANIZATION_CREATE", "Config organization create", "Create organization configuration")
    Permission.add("CONFIG_ORGANIZATION_UPDATE", "Config organization update", "Update organization configuration")
    Permission.add("CONFIG_ORGANIZATION_DELETE", "Config organization delete", "Delete organization configuration")

    Permission.add("CONFIG_USER_ACCESS", "Config users access", "Access to users configuration")
    Permission.add("CONFIG_USER_CREATE", "Config user create", "Create user configuration")
    Permission.add("CONFIG_USER_UPDATE", "Config user update", "Update user configuration")
    Permission.add("CONFIG_USER_DELETE", "Config user delete", "Delete user configuration")

    Permission.add("CONFIG_ROLE_ACCESS", "Config roles access", "Access to roles configuration")
    Permission.add("CONFIG_ROLE_CREATE", "Config role create", "Create role configuration")
    Permission.add("CONFIG_ROLE_UPDATE", "Config role update", "Update role configuration")
    Permission.add("CONFIG_ROLE_DELETE", "Config role delete", "Delete role configuration")

    Permission.add("CONFIG_ACL_ACCESS", "Config acls access", "Access to acls configuration")
    Permission.add("CONFIG_ACL_CREATE", "Config acl create", "Create acl configuration")
    Permission.add("CONFIG_ACL_UPDATE", "Config acl update", "Update acl configuration")
    Permission.add("CONFIG_ACL_DELETE", "Config acl delete", "Delete acl configuration")

    Permission.add("CONFIG_PRODUCT_TYPE_ACCESS", "Config product types access", "Access to product types configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_CREATE", "Config product type create", "Create product type configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_UPDATE", "Config product type update", "Update product type configuration")
    Permission.add("CONFIG_PRODUCT_TYPE_DELETE", "Config product type delete", "Delete product type configuration")

    Permission.add("CONFIG_ATTRIBUTE_ACCESS", "Config attributes access", "Access to attributes configuration")
    Permission.add("CONFIG_ATTRIBUTE_CREATE", "Config attribute create", "Create attribute configuration")
    Permission.add("CONFIG_ATTRIBUTE_UPDATE", "Config attribute update", "Update attribute configuration")
    Permission.add("CONFIG_ATTRIBUTE_DELETE", "Config attribute delete", "Delete attribute configuration")

    Permission.add("CONFIG_REPORT_TYPE_ACCESS", "Config report item types access",
                   "Access to report item types configuration")
    Permission.add("CONFIG_REPORT_TYPE_CREATE", "Config report item type create",
                   "Create report item type configuration")
    Permission.add("CONFIG_REPORT_TYPE_UPDATE", "Config report item type update",
                   "Update report item type configuration")
    Permission.add("CONFIG_REPORT_TYPE_DELETE", "Config report item type delete",
                   "Delete report item type configuration")
    Permission.add("CONFIG_WORD_LIST_ACCESS", "Config word lists access", "Access to word lists configuration")
    Permission.add("CONFIG_WORD_LIST_CREATE", "Config word list create", "Create word list configuration")
    Permission.add("CONFIG_WORD_LIST_UPDATE", "Config word list update", "Update word list configuration")
    Permission.add("CONFIG_WORD_LIST_DELETE", "Config word list delete", "Delete word list configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_ACCESS", "Config collectors nodes access",
                   "Access to collectors nodes configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_CREATE", "Config collectors node create",
                   "Create collectors node configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_UPDATE", "Config collectors node update",
                   "Update collectors node configuration")
    Permission.add("CONFIG_COLLECTORS_NODE_DELETE", "Config collectors node delete",
                   "Delete collectors node configuration")
    Permission.add("CONFIG_OSINT_SOURCE_ACCESS", "Config OSINT source access", "Access to OSINT sources configuration")
    Permission.add("CONFIG_OSINT_SOURCE_CREATE", "Config OSINT source create", "Create OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_UPDATE", "Config OSINT source update", "Update OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_DELETE", "Config OSINT source delete", "Delete OSINT source configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_ACCESS", "Config OSINT source group access",
                   "Access to OSINT sources groups configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_CREATE", "Config OSINT source group create",
                   "Create OSINT source group configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_UPDATE", "Config OSINT source group update",
                   "Update OSINT source group configuration")
    Permission.add("CONFIG_OSINT_SOURCE_GROUP_DELETE", "Config OSINT source group delete",
                   "Delete OSINT source group configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_ACCESS", "Config remote access access",
                   "Access to remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_CREATE", "Config remote access create", "Create remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_UPDATE", "Config remote access update", "Update remote access configuration")
    Permission.add("CONFIG_REMOTE_ACCESS_DELETE", "Config remote access delete", "Delete remote access configuration")
    Permission.add("CONFIG_REMOTE_NODE_ACCESS", "Config remote nodes access",
                   "Access to remote nodes configuration")
    Permission.add("CONFIG_REMOTE_NODE_CREATE", "Config remote node create", "Create remote node configuration")
    Permission.add("CONFIG_REMOTE_NODE_UPDATE", "Config remote node update", "Update remote node configuration")
    Permission.add("CONFIG_REMOTE_NODE_DELETE", "Config remote node delete", "Delete remote node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_ACCESS", "Config presenters nodes access",
                   "Access to presenters nodes configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_CREATE", "Config presenters node create",
                   "Create presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_UPDATE", "Config presenters node update",
                   "Update presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_DELETE", "Config presenters node delete",
                   "Delete presenters node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_ACCESS", "Config publishers nodes access",
                   "Access to publishers nodes configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_CREATE", "Config publishers node create",
                   "Create publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_UPDATE", "Config publishers node update",
                   "Update publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_DELETE", "Config publishers node delete",
                   "Delete publishers node configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_ACCESS", "Config publisher presets access",
                   "Access to publisher presets configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_CREATE", "Config publisher preset create",
                   "Create publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_UPDATE", "Config publisher preset update",
                   "Update publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_DELETE", "Config publisher preset delete",
                   "Delete publisher preset configuration")
    Permission.add("CONFIG_BOTS_NODE_ACCESS", "Config bots nodes access", "Access to bots nodes configuration")
    Permission.add("CONFIG_BOTS_NODE_CREATE", "Config bots node create", "Create bots node configuration")
    Permission.add("CONFIG_BOTS_NODE_UPDATE", "Config bots node update", "Update bots node configuration")
    Permission.add("CONFIG_BOTS_NODE_DELETE", "Config bots node delete", "Delete bots node configuration")
    Permission.add("CONFIG_BOT_PRESET_ACCESS", "Config bot presets access", "Access to bot presets configuration")
    Permission.add("CONFIG_BOT_PRESET_CREATE", "Config bot preset create", "Create bot preset configuration")
    Permission.add("CONFIG_BOT_PRESET_UPDATE", "Config bot preset update", "Update bot preset configuration")
    Permission.add("CONFIG_BOT_PRESET_DELETE", "Config bot preset delete", "Delete bot preset configuration")

    Permission.add("CONFIG_PRESENTERS_NODE_ACCESS", "Config presenters nodes access",
                   "Access to presenters nodes configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_CREATE", "Config presenters node create",
                   "Create presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_UPDATE", "Config presenters node update",
                   "Update presenters node configuration")
    Permission.add("CONFIG_PRESENTERS_NODE_DELETE", "Config presenters node delete",
                   "Delete presenters node configuration")

    Permission.add("PUBLISH_ACCESS", "Publish access", "Access to publish module")
    Permission.add("PUBLISH_CREATE", "Publish create", "Create product")
    Permission.add("PUBLISH_UPDATE", "Publish update", "Update product")
    Permission.add("PUBLISH_DELETE", "Publish delete", "Delete product")
    Permission.add("PUBLISH_PRODUCT", "Publish product", "Publish product")

    Permission.add("CONFIG_PUBLISHERS_NODE_ACCESS", "Config publishers nodes access",
                   "Access to publishers nodes configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_CREATE", "Config publishers node create",
                   "Create publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_UPDATE", "Config publishers node update",
                   "Update publishers node configuration")
    Permission.add("CONFIG_PUBLISHERS_NODE_DELETE", "Config publishers node delete",
                   "Delete publishers node configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_ACCESS", "Config publisher presets access",
                   "Access to publisher presets configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_CREATE", "Config publisher preset create",
                   "Create publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_UPDATE", "Config publisher preset update",
                   "Update publisher preset configuration")
    Permission.add("CONFIG_PUBLISHER_PRESET_DELETE", "Config publisher preset delete",
                   "Delete publisher preset configuration")

if __name__ == '__main__':
    run(db_manager.db)
    sys.exit()
