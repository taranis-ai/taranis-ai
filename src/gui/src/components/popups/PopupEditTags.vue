<template>
  <v-card>
    <v-card-title> Edit Tags </v-card-title>
    <v-card-text>
      <v-autocomplete
        v-model="updatedTags"
        v-model:search="search"
        :items="tags"
        chips
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
import { ref } from 'vue'
import { updateStoryTags } from '@/api/assess'

export default {
  name: 'PopupEditTags',
  props: {
    storyId: {
      type: Number,
      required: true
    },
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
    const search = ref('')

    function editTags() {
      updateStoryTags(props.storyId, updatedTags.value)
    }

    function onKeyDown(event) {
      if (event.key === 'Tab' || event.key === 'Enter') {
        const value = event.target.value
        if (value && !updatedTags.value.includes(value)) {
          updatedTags.value.push(value)
          search.value = ''
        }
      }
    }

    return {
      updatedTags,
      search,
      onKeyDown,
      editTags,
      close
    }
  }
}
</script>
