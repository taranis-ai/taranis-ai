<template>
  <v-card title="Keyboard Shurtcuts">
    <v-card-subtitle>
      HotKeys are currently static only
      <a
        href="https://github.com/taranis-ai/taranis-ai/issues/137"
        target="_blank"
      >
        Issue #137
      </a>
      tracks progress on this feature.
    </v-card-subtitle>
    <v-list :items="hotkeys" item-props />
  </v-card>
</template>

<script>
export default {
  name: 'HotKeysLegend',
  setup() {
    const hotkeys = [
      { type: 'subheader', title: 'General' },
      {
        title: 'Ctrl + Shift + L',
        subtitle: 'Open the HotKeys Legend.'
      },
      {
        title: 'Ctrl + K',
        subtitle: 'Focus the Search Bar.'
      },
      { type: 'subheader', title: 'Assess' },
      {
        title: 'Ctrl + Space',
        subtitle:
          'Mark all selected items as read (if all are read already, mark them as unread).'
      },
      {
        title: 'Ctrl + I',
        subtitle: 'Mark all selected items as important.'
      },
      { title: 'Ctrl + A', subtitle: 'Select all items currently loaded.' },
      {
        title: 'Ctrl + Shift + S',
        subtitle: 'Add selected items to last report.'
      },
      { title: 'Ctrl + E', subtitle: 'Open Edit View of Story' },
      { type: 'divider' },
      { type: 'subheader', title: 'Stories' },
      {
        title: 'Ctrl + M',
        subtitle: 'Create a new story.'
      },
      {
        title: 'Ctrl + Space',
        subtitle:
          'Mark all selected items as read (if all are read already, mark them as unread).'
      },
      {
        title: 'Ctrl + I',
        subtitle: 'Mark all selected items as important.'
      },
      {
        title: 'Ctrl + Shift + S',
        subtitle: 'Add open story to last report.'
      },
      { title: 'Ctrl + E', subtitle: 'Open Edit View of Story' },
      { type: 'divider' },
      { type: 'subheader', title: 'Reports' },
      {
        title: 'Ctrl + M',
        subtitle: 'Create a new report.'
      }
    ]
    return {
      hotkeys
    }
  }
}
</script>
