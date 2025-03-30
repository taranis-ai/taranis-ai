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
import { useConflictsStore } from '@/stores/ConnectorStore'

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

function removeKeysDeep(obj, keysToRemove = ['updated', 'last_change']) {
  if (Array.isArray(obj)) {
    return obj.map((item) => removeKeysDeep(item, keysToRemove))
  } else if (obj && typeof obj === 'object') {
    const newObj = {}
    for (const key in obj) {
      if (!keysToRemove.includes(key)) {
        newObj[key] = removeKeysDeep(obj[key], keysToRemove)
      }
    }
    return newObj
  }
  return obj
}

function stableStringify(obj, indent = 2) {
  if (obj === null || typeof obj !== 'object') {
    return JSON.stringify(obj)
  }
  if (Array.isArray(obj)) {
    const arrayItems = obj.map((item) => stableStringify(item, indent))
    return '[\n' + arrayItems.join(',\n') + '\n]'
  }
  const keys = Object.keys(obj).sort()
  const keyValues = keys.map((key) => {
    return (
      ' '.repeat(indent) +
      JSON.stringify(key) +
      ': ' +
      stableStringify(obj[key], indent + 2)
    )
  })
  return '{\n' + keyValues.join(',\n') + '\n' + ' '.repeat(indent - 2) + '}'
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
}

function initMergelyForConflict(conflict) {
  const containerId = `#mergely-editor-${conflict.storyId}`
  const doc = new Mergely(containerId)
  doc.once('updated', () => {
    // Remove keys "updated" and "last_change" before stringifying.
    const lhsContent = stableStringify(removeKeysDeep(conflict.original), 2)
    const rhsContent = stableStringify(removeKeysDeep(conflict.updated), 2)
    doc.lhs(lhsContent)
    doc.rhs(rhsContent)
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
