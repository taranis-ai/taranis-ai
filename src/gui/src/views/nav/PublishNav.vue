<template>
    <icon-navigation
      :links  = "links"
      :icon   = "'mdi-publish'"
    />
</template>

<script>
import IconNavigation from '@/components/common/IconNavigation'

export default {
  name: 'PublishNav',
  components: {
    IconNavigation
  },
  data: () => ({
    links: [
    ]
  })
}
</script>
