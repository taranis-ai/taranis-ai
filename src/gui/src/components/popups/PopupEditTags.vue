<template>
  <v-card>
    <v-card-title> Edit Tags </v-card-title>
    <v-card-text>
      <v-autocomplete
        v-model="updatedTags"
        :loading="loading"
        :items="tags"
        chips
        menu
        density="compact"
        closable-chips
        clearable
        variant="outlined"
        no-data-text="No tags found"
        item-value="name"
        item-title="name"
        label="Tags"
        multiple
        @keydown="onKeyDown"
      />
    </v-card-text>
    <v-card-actions class="mt-1">
      <v-row no-gutters>
        <v-col cols="5">
          <v-btn
            variant="outlined"
            block
            class="text-lowercase text-red-darken-3"
            prepend-icon="mdi-close"
            @click="close()"
          >
            abort
          </v-btn>
        </v-col>
        <v-col cols="5" offset="2">
          <v-btn
            variant="outlined"
            block
            class="text-lowercase text-primary"
            prepend-icon="mdi-content-save"
            @click="editTags()"
          >
            save
          </v-btn>
        </v-col>
      </v-row>
    </v-card-actions>
  </v-card>
</template>

<script>
import { onMounted, ref } from 'vue'

export default {
  name: 'PopupEditTags',
  props: {
    tags: {
      type: Array,
      default: () => []
    },
    dialog: Boolean
  },
  emits: ['close'],
  setup(props, { emit }) {
    const close = () => {
      emit('close')
    }
    const updatedTags = ref(props.tags)

    function editTags() {
      alert('TODO: Implement')
      console.debug('editTags')
    }

    function onKeyDown(event) {
      if (event.key === 'Tab' || event.key === 'Enter') {
        const value = event.target.value
        if (value && !updatedTags.value.includes(value)) {
          updatedTags.value.push(value)
        }
      }
    }

    onMounted(() => {
      console.debug(updatedTags.value)
    })

    return {
      updatedTags,
      onKeyDown,
      editTags,
      close
    }
  }
}
</script>
