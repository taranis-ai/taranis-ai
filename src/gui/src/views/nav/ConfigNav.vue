<template>
  <icon-navigation :links="links" />
</template>

<script>
import { ref } from 'vue'
import IconNavigation from '@/components/common/IconNavigation.vue'

export default {
  name: 'ConfigNav',
  components: {
    IconNavigation
  },
  setup() {
    const links = ref([
      {
        icon: 'mdi-view-dashboard-variant-outline',
        title: 'nav_menu.dashboard',
        route: '/config/dashboard'
      },
      {
        icon: 'mdi-account-group-outline',
        title: 'nav_menu.users',
        route: '/config/users',
        permission: 'CONFIG_USER_ACCESS'
      },
      {
        icon: 'mdi-office-building-outline',
        title: 'nav_menu.organizations',
        route: '/config/organizations',
        permission: 'CONFIG_ORGANIZATION_ACCESS'
      },
      {
        icon: 'mdi-account-arrow-right-outline',
        title: 'nav_menu.roles',
        route: '/config/roles',
        permission: 'CONFIG_ROLE_ACCESS'
      },
      {
        icon: 'mdi-lock-check-outline',
        title: 'nav_menu.acls',
        route: '/config/acls',
        permission: 'CONFIG_ACL_ACCESS',
        divider: true
      },
      {
        icon: 'mdi-account-hard-hat-outline',
        title: 'nav_menu.workers',
        route: '/config/workers',
        permission: 'CONFIG_WORKER_ACCESS'
      },
      {
        icon: 'mdi-calendar-clock',
        title: 'nav_menu.scheduler',
        route: '/config/scheduler',
        permission: 'CONFIG_WORKER_ACCESS'
      },
      {
        icon: 'mdi-progress-wrench',
        title: 'nav_menu.worker_types',
        route: '/config/workertypes',
        permission: 'CONFIG_WORKER_ACCESS'
      },
      {
        icon: 'mdi-animation-outline',
        title: 'nav_menu.osint_sources',
        route: '/config/sources',
        permission: 'CONFIG_OSINT_SOURCE_ACCESS'
      },
      {
        icon: 'mdi-folder-multiple-outline',
        title: 'nav_menu.osint_source_groups',
        route: '/config/sourcegroups',
        permission: 'CONFIG_OSINT_SOURCE_GROUP_ACCESS'
      },
      {
        icon: 'mdi-robot-outline',
        title: 'nav_menu.bots',
        route: '/config/bots',
        permission: 'CONFIG_BOT_ACCESS'
      },
      {
        icon: 'mdi-transit-connection-horizontal',
        title: 'nav_menu.connectors',
        route: '/config/connectors',
        permission: 'CONFIG_CONNECTOR_ACCESS',
        divider: true
      },
      {
        icon: 'mdi-file-table-outline',
        title: 'nav_menu.report_types',
        route: '/config/reportitems/types',
        permission: 'CONFIG_REPORT_TYPE_ACCESS'
      },
      {
        icon: 'mdi-application-variable-outline',
        title: 'nav_menu.attributes',
        route: '/config/attributes',
        permission: 'CONFIG_ATTRIBUTE_ACCESS'
      },
      {
        icon: 'mdi-file-document-outline',
        title: 'nav_menu.product_types',
        route: '/config/product/types',
        permission: 'CONFIG_PRODUCT_TYPE_ACCESS'
      },
      {
        icon: 'mdi-file-document-plus-outline',
        title: 'nav_menu.templates',
        route: '/config/product/templates',
        permission: 'CONFIG_PRODUCT_TYPE_ACCESS'
      },
      {
        icon: 'mdi-file-star-outline',
        title: 'nav_menu.publisher',
        route: '/config/publishers',
        permission: 'CONFIG_PUBLISHER_ACCESS'
      },
      {
        icon: 'mdi-format-list-text',
        title: 'nav_menu.word_lists',
        route: '/config/wordlists',
        permission: 'CONFIG_WORD_LIST_ACCESS',
        divider: true
      },
      { icon: 'mdi-api', title: 'nav_menu.openapi', route: '/config/openapi' },
      {
        icon: 'mdi-cog-outline',
        title: 'nav_menu.settings',
        route: '/config/settings'
      }
    ])

    return {
      links
    }
  }
}
</script>
