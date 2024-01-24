<template>
  <v-card>
    <v-card-title> Edit Tags </v-card-title>
    <v-card-text>
      <edit-tags v-model="updatedTags" />
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
import { useAssessStore } from '@/stores/AssessStore'
import EditTags from '@/components/assess/EditTags.vue'

export default {
  name: 'PopupEditTags',
  components: {
    EditTags
  },
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
    const assessStore = useAssessStore()

    const close = () => {
      emit('close')
    }
    const updatedTags = ref(props.tags)

    async function editTags() {
      await assessStore.updateTags(props.storyId, updatedTags.value)
      close()
    }

    return {
      updatedTags,
      editTags,
      close
    }
  }
}
</script>
