<template>
  <iframe :src="targetUrl" :title="title" class="frontend-iframe"></iframe>
</template>

<script>
export default {
  name: 'FrontendProxy',
  props: {
    title: {
      type: String,
      default: 'Frontend'
    },
    targetUrl: {
      type: String,
      required: true
    }
  }
}
</script>
