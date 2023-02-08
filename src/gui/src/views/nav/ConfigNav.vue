<template>
  <Navigation
    :links  = "links"
    :icon   = "'mdi-ballot-outline'"
    filter
  />
</template>

<script>
import Navigation from '../../components/common/Navigation'

export default {
  name: 'ConfigNav',
  components: {
    Navigation
  },
  data: () => ({
    links: [
      { icon: 'mdi-monitor-dashboard', title: 'nav_menu.dashboard', route: '/config' },
      { separator: '1' },
      { icon: 'mdi-account-group', title: 'nav_menu.users', route: '/config/users', permission: 'CONFIG_USER_ACCESS' },
      { icon: 'mdi-office-building', title: 'nav_menu.organizations', route: '/config/organizations', permission: 'CONFIG_ORGANIZATION_ACCESS' },
      { icon: 'mdi-account-arrow-right', title: 'nav_menu.roles', route: '/config/roles', permission: 'CONFIG_ROLE_ACCESS' },
      { icon: 'mdi-lock-check', title: 'nav_menu.acls', route: '/config/acls', permission: 'CONFIG_ACL_ACCESS' },
      { icon: 'mdi-server-network', title: 'nav_menu.nodes', route: '/config/nodes', permission: 'CONFIG_NODE_ACCESS' },
      { separator: '1' },
      { icon: 'mdi-animation-outline', title: 'nav_menu.osint_sources', route: '/config/collectors/sources', permission: 'CONFIG_OSINT_SOURCE_ACCESS' },
      { icon: 'mdi-folder-multiple', title: 'nav_menu.osint_source_groups', route: '/config/collectors/groups', permission: 'CONFIG_OSINT_SOURCE_GROUP_ACCESS' },
      { separator: '1' },
      { icon: 'mdi-file-document-outline', title: 'nav_menu.product_types', route: '/config/product/types', permission: 'CONFIG_PRODUCT_TYPE_ACCESS' },
      { separator: '1' },
      { icon: 'mdi-file-star-outline', title: 'nav_menu.publisher_presets', route: '/config/publishers/presets', permission: 'CONFIG_PUBLISHER_PRESET_ACCESS' },
      { separator: '1' },
      { icon: 'mdi-application-variable-outline', title: 'nav_menu.attributes', route: '/config/reportitems/attributes', permission: 'CONFIG_ATTRIBUTE_ACCESS' },
      { icon: 'mdi-file-table-outline', title: 'nav_menu.report_types', route: '/config/reportitems/types', permission: 'CONFIG_REPORT_TYPE_ACCESS' },
      { separator: '1' },
      { icon: 'mdi-format-list-text', title: 'nav_menu.word_lists', route: '/config/wordlists', permission: 'CONFIG_WORD_LIST_ACCESS' },
      { separator: '1' },
      { icon: 'mdi-remote-desktop', title: 'nav_menu.remote_access', route: '/config/remote/access', permission: 'CONFIG_REMOTE_ACCESS_ACCESS' },
      { icon: 'mdi-share-variant', title: 'nav_menu.remote_nodes', route: '/config/remote/nodes', permission: 'CONFIG_REMOTE_NODE_ACCESS' },
      { icon: 'mdi-robot', title: 'nav_menu.bots', route: '/config/bots', permission: 'CONFIG_NODE_ACCESS' },
      { icon: 'mdi-api', title: 'OpenAPI', route: '/config/openapi' }

    ]
  })
}
</script>
