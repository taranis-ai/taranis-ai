<template>
  <v-card>
    <v-card-title> Edit Tags </v-card-title>
    <v-card-text>
      <v-combobox
        v-model="updatedTags"
        :items="tags"
        chips
        density="compact"
        closable-chips
        clearable
        variant="outlined"
        no-data-text="No tags found"
        hint="Press 'Enter' to add a new tag"
        persistent-hint
        item-value="name"
        item-title="name"
        label="Tags"
        multiple
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
import { notifySuccess, notifyFailure } from '@/utils/helpers'

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

    function editTags() {
      updateStoryTags(props.storyId, updatedTags.value)
        .then((result) => {
          notifySuccess(result)
          close()
        })
        .catch((result) => {
          notifyFailure(result)
          close()
        })
    }

    return {
      updatedTags,
      editTags,
      close
    }
  }
}
</script>
