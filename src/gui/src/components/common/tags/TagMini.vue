<template>
    <v-chip  
        label 
        x-small dark left
        class="mr-1 px-1 text-caption text-weight-bold text-uppercase tag-mini">
        {{ label }}
    </v-chip >
</template>

<script>
export default {
  name: 'TagMini',
  props: {
    label: String
  },
  data: () => ({
  }),
  computed: {
  }
}
</script>
