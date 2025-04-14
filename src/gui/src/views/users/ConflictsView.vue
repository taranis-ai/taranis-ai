<template>
  <v-container>
    <v-card outlined>
      <v-card-title>Resolve Conflicts</v-card-title>
      <v-card-text>
        <div v-if="conflictsStore.conflicts.length === 0">
          <p>No conflicts to resolve.</p>
        </div>
        <div v-else>
          <div
            v-for="conflict in conflictsStore.conflicts"
            :key="conflict.storyId"
            class="mb-6"
          >
            <h3>Conflict for Story: {{ conflict.storyId }}</h3>
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
  </v-container>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useConflictsStore } from '@/stores/ConnectorStore'
import Mergely from 'mergely'
import 'mergely/lib/mergely.css'

const conflictsStore = useConflictsStore()
const mergedContents = ref({})

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
  const conflict = conflictsStore.conflicts.find((c) => c.storyId === storyId)
  if (conflict && conflict.mergelyInstance) {
    await nextTick()
    const merged = conflict.mergelyInstance.get('rhs')
    mergedContents.value[storyId] = merged
  } else {
    console.error(`Mergely instance for story ${storyId} not available`)
  }
}

async function submitResolution(storyId) {
  const merged = mergedContents.value[storyId]
  if (!merged) {
    alert('Please get the merged content first.')
    return
  }

  let resolutionData
  try {
    resolutionData = JSON.parse(merged)
  } catch (jsonError) {
    console.error(
      `Invalid JSON for merged content for story ${storyId}:`,
      jsonError
    )
    alert(`Merged content is not valid JSON for story ${storyId}.`)
    return
  }

  try {
    await conflictsStore.resolveConflictById(storyId, resolutionData)
    alert(`Conflict for story ${storyId} resolved successfully!`)
  } catch (error) {
    console.error(`Error resolving conflict for story ${storyId}:`, error)
    alert(`Error resolving conflict for story ${storyId}`)
  }
}

onMounted(async () => {
  try {
    await conflictsStore.loadConflicts()
    await nextTick()
    conflictsStore.conflicts.forEach((conflict) => {
      initMergelyForConflict(conflict)
    })
  } catch (err) {
    console.error('Initialization error:', err)
  }
})
</script>

<style scoped>
/* Component-specific styling if needed */
</style>
