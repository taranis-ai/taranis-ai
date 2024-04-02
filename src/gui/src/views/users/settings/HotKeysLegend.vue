<template>
  <v-card>
    <v-card-title>
      <v-toolbar dense flat title="Keyboard Shortcuts" />
    </v-card-title>
    <v-card-subtitle>
      <h2 style="background-color: #ffff00">
        HotKeys are currently static only
        <a
          href="https://github.com/taranis-ai/taranis-ai/issues/137"
          target="_blank"
        >
          Issue #137
        </a>
        tracks progress on this feature.
      </h2>
    </v-card-subtitle>
    <v-list :items="hotkeys" item-props />
  </v-card>
</template>

<script>
export default {
  name: 'HotKeysLegend',
  setup() {
    const hotkeys = [
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
      { title: 'Esc', subtitle: 'Deselects all currently selected items.' },
      { type: 'divider' }
    ]

    return {
      hotkeys
    }
  }
}
</script>
