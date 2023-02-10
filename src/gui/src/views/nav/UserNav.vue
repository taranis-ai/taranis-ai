<template>
  <Navigation :links="links" icon="mdi-ballot-outline" />
</template>

<script>
import Navigation from '@/components/common/Navigation'

export default {
  name: 'UserNav',
  components: {
    Navigation
  },
  data: () => ({
    links: [
      { icon: 'mdi-account', title: 'nav_menu.user', route: '/user' },
      {
        icon: 'mdi-cog-outline',
        title: 'user_menu.settings',
        route: '/user/settings'
      },
      {
        icon: 'mdi-folder-multiple',
        title: 'nav_menu.asset_groups',
        route: '/user/assets'
      },
      {
        icon: 'mdi-email-multiple-outline',
        title: 'nav_menu.notification_templates',
        route: '/user/templates'
      }
    ]
  })
}
</script>
