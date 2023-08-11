<template>
  <icon-navigation :links="links" />
</template>

<script>
import IconNavigation from '@/components/common/IconNavigation.vue'

export default {
  name: 'ConfigNav',
  components: {
    IconNavigation
  },
  data: () => ({
    links: [
      {
        icon: 'mdi-monitor-dashboard',
        title: 'nav_menu.dashboard',
        route: '/config/dashboard'
      },
      {
        icon: 'mdi-account-group',
        title: 'nav_menu.users',
        route: '/config/users',
        permission: 'CONFIG_USER_ACCESS'
      },
      {
        icon: 'mdi-office-building',
        title: 'nav_menu.organizations',
        route: '/config/organizations',
        permission: 'CONFIG_ORGANIZATION_ACCESS'
      },
      {
        icon: 'mdi-account-arrow-right',
        title: 'nav_menu.roles',
        route: '/config/roles',
        permission: 'CONFIG_ROLE_ACCESS'
      },
      {
        icon: 'mdi-lock-check',
        title: 'nav_menu.acls',
        route: '/config/acls',
        permission: 'CONFIG_ACL_ACCESS',
        divider: true
      },
      {
        icon: 'mdi-account-hard-hat',
        title: 'nav_menu.workers',
        route: '/config/workers',
        permission: 'CONFIG_WORKER_ACCESS'
      },
      {
        icon: 'mdi-robot',
        title: 'nav_menu.bots',
        route: '/config/bots',
        permission: 'CONFIG_NODE_ACCESS'
      },
      {
        icon: 'mdi-arrow-collapse-all',
        title: 'nav_menu.collectors',
        route: '/config/collectors',
        permission: 'CONFIG_NODE_ACCESS',
        divider: true
      },
      {
        icon: 'mdi-animation-outline',
        title: 'nav_menu.osint_sources',
        route: '/config/sources',
        permission: 'CONFIG_OSINT_SOURCE_ACCESS'
      },
      {
        icon: 'mdi-folder-multiple',
        title: 'nav_menu.osint_source_groups',
        route: '/config/sourcegroups',
        permission: 'CONFIG_OSINT_SOURCE_GROUP_ACCESS',
        divider: true
      },
      {
        icon: 'mdi-file-document-outline',
        title: 'nav_menu.product_types',
        route: '/config/product/types',
        permission: 'CONFIG_PRODUCT_TYPE_ACCESS'
      },
      {
        icon: 'mdi-file-star-outline',
        title: 'nav_menu.publisher_presets',
        route: '/config/publishers/presets',
        permission: 'CONFIG_PUBLISHER_PRESET_ACCESS'
      },
      {
        icon: 'mdi-application-variable-outline',
        title: 'nav_menu.attributes',
        route: '/config/reportitems/attributes',
        permission: 'CONFIG_ATTRIBUTE_ACCESS'
      },
      {
        icon: 'mdi-file-table-outline',
        title: 'nav_menu.report_types',
        route: '/config/reportitems/types',
        permission: 'CONFIG_REPORT_TYPE_ACCESS'
      },
      {
        icon: 'mdi-format-list-text',
        title: 'nav_menu.word_lists',
        route: '/config/wordlists',
        permission: 'CONFIG_WORD_LIST_ACCESS',
        divider: true
      },
      { icon: 'mdi-api', title: 'nav_menu.openapi', route: '/config/openapi' }
    ]
  })
}
</script>
