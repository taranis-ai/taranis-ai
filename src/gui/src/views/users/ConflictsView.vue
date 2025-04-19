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
        <v-alert v-if="!conflicts.length" type="info" outlined elevation="2">
          No conflicts to resolve.
        </v-alert>

        <v-expansion-panels
          v-model="openPanels"
          multiple
          @update:modelValue="onPanelsUpdated"
        >
          <v-expansion-panel
            v-for="conflict in conflicts"
            :key="conflict.storyId"
          >
            <v-expansion-panel-title>
              <div class="d-flex justify-space-between align-center w-100">
                <span>Story ID: {{ conflict.storyId }}</span>
                <v-chip
                  v-if="conflict.hasProposals"
                  small
                  color="orange"
                  text-color="white"
                  outlined
                >
                  <a
                    :href="conflict.hasProposals"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="proposal-link"
                  >
                    View Proposal
                  </a>
                </v-chip>
                <v-chip v-else small color="grey" text-color="white" outlined>
                  No Proposal
                </v-chip>
              </div>
            </v-expansion-panel-title>

            <v-expansion-panel-text>
              <div
                :id="`mergely-editor-${conflict.storyId}`"
                class="mergely-editor"
                style="height: 300px"
              ></div>

              <div class="mt-4 d-flex">
                <v-btn
                  color="primary"
                  @click="getMergedContentForConflict(conflict.storyId)"
                >
                  Get Right Side
                </v-btn>
                <v-spacer />
                <v-btn
                  color="success"
                  @click="submitResolution(conflict.storyId)"
                >
                  Submit Resolution
                </v-btn>
              </div>

              <v-card
                v-if="mergedContents[conflict.storyId]"
                class="mt-4"
                outlined
              >
                <v-card-subtitle>Merged Content</v-card-subtitle>
                <v-card-text>
                  <pre class="merged-pre">{{
                    mergedContents[conflict.storyId]
                  }}</pre>
                </v-card-text>
              </v-card>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
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

const openPanels = ref([])
const prevPanels = ref([])
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
  const el = document.querySelector(containerId)

  if (!el) {
    console.warn(`Mergely container not found for ${conflict.storyId}`)
    return
  }

  try {
    const doc = new Mergely(containerId, {
      license: 'gpl',
      lhs: conflict.original,
      rhs: conflict.updated
    })

    doc.once('updated', () => {
      doc.scrollToDiff('next')
    })

    conflict.mergelyInstance = doc
  } catch (err) {
    console.error(`Failed to init Mergely for ${conflict.storyId}`, err)
  }
}

function destroyMergely(conflict) {
  if (conflict?.mergelyInstance?.remove) {
    try {
      conflict.mergelyInstance.remove()
    } catch (err) {
      console.warn(`Failed to remove Mergely for ${conflict.storyId}`, err)
    }
    conflict.mergelyInstance = null
  }
}

async function getMergedContentForConflict(storyId) {
  const conflict = conflicts.value.find((c) => c.storyId === storyId)
  if (!conflict?.mergelyInstance) {
    console.error(`Editor not ready for story ${storyId}`)
    showToast(`Editor not loaded for ${storyId}`, 'error')
    return
  }

  await nextTick()
  const content = conflict.mergelyInstance.get('rhs')

  try {
    JSON.parse(content)
    mergedContents.value[storyId] = content
    showToast(`Valid JSON extracted from story ${storyId}`, 'success')
  } catch (err) {
    console.error(`Invalid JSON in right-side content for ${storyId}:`, err)
    showToast(
      `Right-side content is not valid JSON for story ${storyId}`,
      'error'
    )
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

function onPanelsUpdated(panels) {
  prevPanels.value
    .filter((i) => !panels.includes(i))
    .forEach((index) => {
      const conflict = conflicts.value[index]
      if (conflict) destroyMergely(conflict)
    })

  panels
    .filter((i) => !prevPanels.value.includes(i))
    .forEach((index) => {
      const conflict = conflicts.value[index]
      if (conflict) {
        nextTick(() => initMergelyForConflict(conflict))
      }
    })

  prevPanels.value = [...panels]
}

onMounted(async () => {
  await store.loadConflicts()
  await store.fetchProposalCount()
})
</script>

<style scoped>
.mergely-editor {
  border: 1px solid #ccc;
}
.merged-pre {
  white-space: pre-wrap;
  word-break: break-word;
}
.proposal-link {
  color: inherit;
  text-decoration: none;
}
</style>
