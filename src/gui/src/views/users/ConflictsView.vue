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
              Get Merged Content
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
import { useConflictsStore } from '@/stores/ConflictsStore'

// Helper functions to dynamically load external assets
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src
    s.async = true
    s.type = 'text/javascript'
    s.onload = resolve
    s.onerror = () => reject(new Error(`Failed to load script: ${src}`))
    document.head.appendChild(s)
  })
}

function loadCSS(href) {
  return new Promise((resolve, reject) => {
    const l = document.createElement('link')
    l.rel = 'stylesheet'
    l.type = 'text/css'
    l.href = href
    l.onload = resolve
    l.onerror = () => reject(new Error(`Failed to load CSS: ${href}`))
    document.head.appendChild(l)
  })
}

const conflictsStore = useConflictsStore()
const mergedContents = ref({})

async function initMergelyGlobally() {
  if (!window.jQuery) {
    await loadScript(
      'https://cdnjs.cloudflare.com/ajax/libs/mergely/5.0.0/mergely.min.js'
    )
  }
  await loadCSS(
    'https://cdnjs.cloudflare.com/ajax/libs/mergely/5.0.0/mergely.css'
  )
  await loadScript(
    'https://cdnjs.cloudflare.com/ajax/libs/mergely/5.0.0/mergely.min.js'
  )
}

function initMergelyForConflict(conflict) {
  const containerId = `#mergely-editor-${conflict.storyId}`
  const doc = new Mergely(containerId)
  doc.once('updated', () => {
    doc.lhs(JSON.stringify(conflict.original, null, 2))
    doc.rhs(JSON.stringify(conflict.updated, null, 2))
    doc.once('updated', () => {
      doc.scrollToDiff('next')
    })
  })
  conflict.mergelyInstance = doc
}

function getMergedContentForConflict(storyId) {
  const conflict = conflictsStore.conflicts.find((c) => c.storyId === storyId)
  if (conflict && conflict.mergelyInstance) {
    const merged = conflict.mergelyInstance.get('merged')
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
  try {
    await conflictsStore.resolveConflictById(storyId, JSON.parse(merged))
    alert(`Conflict for story ${storyId} resolved successfully!`)
  } catch (error) {
    alert(`Error resolving conflict for story ${storyId}`)
  }
}

onMounted(async () => {
  try {
    await initMergelyGlobally()
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
