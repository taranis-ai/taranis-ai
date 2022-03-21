<template>
    <Navigation
            :links  = "links"
            :icon   = "'mdi-publish'"
    />
</template>

<script>
import Navigation from '../../components/common/Navigation'

export default {
  name: 'AnalyzeNav',
  components: {
    Navigation
  },
  data: () => ({
    links: [
    ]
  })
}
</script>
