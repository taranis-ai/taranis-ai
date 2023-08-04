<template>
  <icon-navigation :links="links" />
</template>

<script>
import IconNavigation from '@/components/common/IconNavigation.vue'

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
      }
    ]
  })
}
</script>
