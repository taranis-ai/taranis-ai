<template>
  <h2
    :class="[
      'news-item-title',
      {
        'status-unread': !read,
      },
    ]"
  >
    <sup v-if="!read" class="new-indicator"> * </sup>
    {{ title }}
  </h2>
</template>

<script>
export default {
  name: 'newsItemTitle',
  props: {
    title: String,
    read: Boolean
  }
}
</script>
