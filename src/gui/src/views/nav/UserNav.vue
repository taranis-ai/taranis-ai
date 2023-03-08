<template>
  <icon-navigation :links="links" icon="mdi-ballot-outline" />
</template>

<script>
import IconNavigation from '@/components/common/IconNavigation'

export default {
  name: 'UserNav',
  components: {
    IconNavigation
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
        icon: 'mdi-email-multiple-outline',
        title: 'nav_menu.notification_templates',
        route: '/user/templates'
      }
    ]
  })
}
</script>
