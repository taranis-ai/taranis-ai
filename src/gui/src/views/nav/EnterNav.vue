<template>
  <Navigation
    v-if="links.length > 0"
    :links="links"
    :icon="'mdi-location-enter'"
  />
</template>

<script>
import Navigation from '../../components/common/Navigation'

export default {
  name: 'EnterNav',
  components: {
    Navigation
  },
  data: () => ({
    groups: [],
    links: []
  }),
  mounted () {
  }
}
</script>
