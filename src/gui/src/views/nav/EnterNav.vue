<template>
  <icon-navigation
    v-if="links.length > 0"
    :links="links"
    :icon="'mdi-location-enter'"
  />
</template>

<script>
import IconNavigation from '@/components/common/IconNavigation'

export default {
  name: 'EnterNav',
  components: {
    IconNavigation
  },
  data: () => ({
    groups: [],
    links: []
  }),
  mounted () {
  }
}
</script>
