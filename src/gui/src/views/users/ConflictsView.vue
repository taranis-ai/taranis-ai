<template>
  <v-container>
    <v-card outlined>
      <v-card-title>
        Resolve Conflicts
        <v-chip class="ml-2" color="primary" small>
          You should resolve {{ proposalCount }} proposal(s) before proceeding.
        </v-chip>
      </v-card-title>

      <v-card-text>
        <div v-if="conflicts.length === 0">
          <p>No conflicts to resolve.</p>
        </div>
        <div v-else>
          <div
            v-for="conflict in conflicts"
            :key="conflict.storyId"
            class="mb-6"
          >
            <h3>Conflict for Story: {{ conflict.storyId }}</h3>
            <p>
              This story has a proposal:

              <strong v-if="conflict.hasProposals">
                <a
                  :href="conflict.hasProposals"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ conflict.hasProposals }}
                </a>
              </strong>
              <span v-else>No</span> <span v-else>No</span>
            </p>

            <div
              :id="'mergely-editor-' + conflict.storyId"
              style="height: 300px"
            ></div>

            <v-btn
              color="primary"
              class="mt-2"
              @click="getMergedContentForConflict(conflict.storyId)"
            >
              Get Right Side
            </v-btn>
            <v-btn
              color="success"
              class="mt-2 ml-2"
              @click="submitResolution(conflict.storyId)"
            >
              Submit Resolution
            </v-btn>

            <div v-if="mergedContents[conflict.storyId]">
              <h4>Merged Content:</h4>
              <pre>{{ mergedContents[conflict.storyId] }}</pre>
            </div>
            <v-divider class="my-4"></v-divider>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <v-snackbar
      v-model="snackbar"
      :timeout="3000"
      :color="snackbarColor"
      top
      right
    >
      {{ snackbarMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useConflictsStore } from '@/stores/ConnectorStore'
import Mergely from 'mergely'
import 'mergely/lib/mergely.css'

const store = useConflictsStore()
const { conflicts, proposalCount } = storeToRefs(store)
const mergedContents = ref({})

const snackbar = ref(false)
const snackbarMessage = ref('')
const snackbarColor = ref('error')

function showToast(message, color = 'error') {
  snackbarMessage.value = message
  snackbarColor.value = color
  snackbar.value = true
}

function initMergelyForConflict(conflict) {
  const containerId = `#mergely-editor-${conflict.storyId}`
  const doc = new Mergely(containerId, {
    license: 'gpl',
    lhs: conflict.original,
    rhs: conflict.updated
  })

  doc.once('updated', () => {
    doc.scrollToDiff('next')
  })

  conflict.mergelyInstance = doc
}

async function getMergedContentForConflict(storyId) {
  const conflict = conflicts.value.find((c) => c.storyId === storyId)
  if (conflict?.mergelyInstance) {
    await nextTick()
    mergedContents.value[storyId] = conflict.mergelyInstance.get('rhs')
  } else {
    console.error(`Editor not ready for story ${storyId}`)
    showToast(`Editor not loaded for ${storyId}`, 'error')
  }
}

async function submitResolution(storyId) {
  const merged = mergedContents.value[storyId]
  if (!merged) return showToast('Get the right side first.')

  try {
    const resolutionData = JSON.parse(merged)
    await store.resolveConflictById(storyId, resolutionData)
    showToast(`Story ${storyId} resolved!`, 'success')
  } catch (err) {
    console.error(`Resolution failed for ${storyId}`, err)
    showToast(`Resolution failed for ${storyId}`, 'error')
  }
}

onMounted(async () => {
  await store.loadConflicts()
  await store.fetchProposalCount()
  await nextTick()
  conflicts.value.forEach(initMergelyForConflict)
})
</script>
