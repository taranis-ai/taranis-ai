<template>
    <Navigation
      :links  = "links"
      :icon   = "'mdi-publish'"
    />
</template>

<script>
import Navigation from '../../components/common/Navigation'

export default {
  name: 'PublishNav',
  components: {
    Navigation
  },
  data: () => ({
    links: [
    ]
  })
}
</script>
