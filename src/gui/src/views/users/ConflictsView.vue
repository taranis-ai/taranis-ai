<template>
  <v-container>
    <v-card outlined>
      <v-card-title>
        Conflicts of the same stories (internal vs external)
        <v-chip v-if="proposalCount" class="ml-2" color="primary" small>
          You should resolve {{ proposalCount }} proposal(s) before proceeding.
        </v-chip>
      </v-card-title>

      <v-card-text>
        <v-alert
          v-if="!storyConflicts.length"
          type="info"
          outlined
          elevation="2"
        >
          No conflicts to resolve.
        </v-alert>

        <v-expansion-panels
          v-model="openPanels"
          multiple
          @update:modelValue="onPanelsUpdated"
        >
          <v-expansion-panel
            v-for="conflict in storyConflicts"
            :key="conflict.storyId"
          >
            <v-expansion-panel-title>
              <div class="d-flex justify-space-between align-center w-100">
                <span>Story ID: {{ conflict.storyId }}</span>
                <v-btn
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
                    View Event With Proposal(s)
                  </a>
                </v-btn>
                <v-btn v-else small color="grey" text-color="white" outlined>
                  No Proposal
                </v-btn>
              </div>
            </v-expansion-panel-title>

            <v-expansion-panel-text>
              <div
                :id="`mergely-editor-${conflict.storyId}`"
                class="mergely-editor"
                style="height: 300px"
              ></div>

              <div class="mt-4 d-flex align-center">
                <v-btn
                  color="primary"
                  @click="getMergedContentForConflict(conflict.storyId)"
                >
                  Get Right Side
                </v-btn>

                <v-btn
                  color="secondary"
                  class="mx-2"
                  @click="scrollToNextDiff(conflict.storyId)"
                >
                  Next Diff
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

    <v-card outlined class="mt-6">
      <v-card-title>
        Conflicting News Items
        <v-chip
          v-if="newsItemConflicts.length"
          class="ml-2"
          color="warning"
          small
        >
          {{ newsItemConflicts.length }} conflict(s) detected
        </v-chip>
      </v-card-title>

      <v-card-text>
        <v-alert
          v-if="!newsItemConflicts.length"
          type="info"
          outlined
          elevation="2"
        >
          No news item conflicts.
        </v-alert>

        <div
          v-for="(group, storyId) in groupedNewsItemConflicts"
          :key="storyId"
          class="mb-6"
        >
          <v-card outlined>
            <v-card-title class="d-flex justify-space-between">
              <div>
                <div class="text-h6 mb-1">{{ group.title }}</div>
                <div class="text-caption text-grey-darken-1">
                  ID: {{ storyId }}
                </div>
              </div>
              <v-btn
                size="small"
                variant="text"
                color="primary"
                @click="toggleStoryPreview(storyId)"
              >
                {{
                  expandedStories.includes(storyId) ? 'Hide JSON' : 'Show JSON'
                }}
              </v-btn>
            </v-card-title>

            <v-card-text>
              <v-alert type="warning" variant="outlined" dense text>
                <strong>{{ group.conflicts.length }}</strong> conflicting news
                item(s)
              </v-alert>

              <v-alert
                type="info"
                variant="tonal"
                density="compact"
                class="mb-3"
                icon="mdi-information-outline"
              >
                <p class="text-body-2 mb-0">
                  Check items to <strong>include</strong> in the incoming story.
                  Uncheck items to <strong>exclude</strong> from the incoming
                  story and keep them in the existing story.
                </p>
              </v-alert>

              <v-list dense>
                <v-list-item
                  v-for="conflict in group.conflicts"
                  :key="conflict.news_item_id"
                >
                  <template #prepend>
                    <v-checkbox
                      v-model="selectedNewsItems[storyId]"
                      :value="conflict.news_item_id"
                      hide-details
                      multiple
                      density="compact"
                    />
                  </template>

                  <div class="d-flex flex-column">
                    <div class="d-flex align-center">
                      <v-chip
                        v-if="
                          typeof storySummaries[conflict.existing_story_id]
                            ?.relevance === 'number'
                        "
                        class="mr-2"
                        color="blue-grey"
                        size="x-small"
                        label
                      >
                        Relevance:
                        {{
                          storySummaries[
                            conflict.existing_story_id
                          ].relevance.toFixed(2)
                        }}
                      </v-chip>
                      {{
                        storySummaries[conflict.existing_story_id]?.title ||
                        'Loading title…'
                      }}
                    </div>

                    <div class="d-flex flex-wrap text-body-2 mt-1">
                      <div class="mr-4">
                        <strong>News item ID:</strong>
                        <a
                          :href="`/story/${conflict.existing_story_id}`"
                          target="_blank"
                          class="text-decoration-none text-primary"
                        >
                          {{ conflict.news_item_id }}
                        </a>
                      </div>

                      <div class="mr-4">
                        {{
                          storySummaries[conflict.existing_story_id]
                            ? storySummaries[conflict.existing_story_id]
                                .news_item_count +
                              ' ' +
                              (storySummaries[conflict.existing_story_id]
                                .news_item_count === 1
                                ? 'item contains the story with the conflicting news item'
                                : 'items contains the story with the conflicting news item')
                            : 'Loading items…'
                        }}
                      </div>
                    </div>
                  </div>
                </v-list-item>
              </v-list>
              <v-btn
                color="success"
                class="mt-3"
                @click="submitNewsItemResolution(storyId)"
              >
                Submit Resolved Story
              </v-btn>
              <v-btn
                color="info"
                class="mt-3 ml-2"
                @click="submitAndRedirectNewsItemResolution(storyId)"
              >
                Submit & View Story
              </v-btn>

              <v-expand-transition>
                <div v-if="expandedStories.includes(storyId)">
                  <v-card class="mt-4" outlined>
                    <v-card-title class="text-subtitle-1">
                      Full Incoming Story (JSON)
                    </v-card-title>
                    <v-card-text>
                      <pre style="white-space: pre-wrap">
                        {{ JSON.stringify(group.fullStory, null, 2) }}
                      </pre>
                    </v-card-text>
                  </v-card>
                </div>
              </v-expand-transition>
            </v-card-text>
          </v-card>
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
import { ref, onMounted, nextTick, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useConflictsStore } from '@/stores/ConnectorStore'
import Mergely from 'mergely'
import 'mergely/lib/mergely.css'

const store = useConflictsStore()
const { storyConflicts, proposalCount, newsItemConflicts, storySummaries } =
  storeToRefs(store)

const openPanels = ref([])
const prevPanels = ref([])
const mergedContents = ref({})
const expandedStories = ref([])
const snackbar = ref(false)
const snackbarMessage = ref('')
const snackbarColor = ref('error')
const selectedNewsItems = ref({})

function showToast(message, color = 'error') {
  snackbarMessage.value = message
  snackbarColor.value = color
  snackbar.value = true
}

function initMergelyForConflict(conflict) {
  const containerId = `mergely-editor-${conflict.storyId}`
  const el = document.getElementById(containerId)
  if (!el) return

  const waitUntilVisible = (cb) => {
    const isVisible = () => {
      const rect = el.getBoundingClientRect()
      return rect.width > 0 && rect.height > 0 && el.offsetParent !== null
    }
    const check = () => {
      if (isVisible()) cb()
      else requestAnimationFrame(check)
    }
    requestAnimationFrame(check)
  }

  waitUntilVisible(() => {
    try {
      const doc = new Mergely(`#${containerId}`, {
        license: 'gpl',
        lhs: conflict.original,
        rhs: conflict.updated,
        wrap_lines: true
      })
      doc.once('updated', () => doc.scrollToDiff('next'))
      conflict.mergelyInstance = doc
    } catch (err) {
      console.error(`Failed to init Mergely for ${conflict.storyId}:`, err)
    }
  })
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
  const conflict = storyConflicts.value.find((c) => c.storyId === storyId)
  if (!conflict?.mergelyInstance)
    return showToast(`Editor not loaded for ${storyId}`, 'error')

  await nextTick()
  const content = conflict.mergelyInstance.get('rhs')
  try {
    JSON.parse(content)
    mergedContents.value[storyId] = content
    showToast(`Valid JSON extracted from story ${storyId}`, 'success')
  } catch {
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
    await store.resolveStoryConflictById(storyId, resolutionData)
    const index = storyConflicts.value.findIndex((c) => c.storyId === storyId)
    if (index !== -1) {
      destroyMergely(storyConflicts.value[index])
      storyConflicts.value.splice(index, 1)
      openPanels.value = []
      await nextTick()
      prevPanels.value = []
      delete mergedContents.value[storyId]
    }
    showToast(`Story ${storyId} resolved!`, 'success')
  } catch {
    showToast(`Resolution failed for ${storyId}`, 'error')
  }
}

function onPanelsUpdated(panels) {
  prevPanels.value
    .filter((i) => !panels.includes(i))
    .forEach((i) => {
      const conflict = storyConflicts.value[i]
      if (conflict) destroyMergely(conflict)
    })
  panels
    .filter((i) => !prevPanels.value.includes(i))
    .forEach((i) => {
      const storyConflict = storyConflicts.value[i]
      if (storyConflict) nextTick(() => initMergelyForConflict(storyConflict))
    })
  prevPanels.value = [...panels]
}

function scrollToNextDiff(storyId) {
  const conflict = storyConflicts.value.find((c) => c.storyId === storyId)
  if (conflict?.mergelyInstance) {
    try {
      conflict.mergelyInstance.scrollToDiff('next')
    } catch (err) {
      showToast(`Failed to scroll diff for ${storyId}`, 'error')
      console.error(err)
    }
  } else {
    showToast(`Editor not initialized for ${storyId}`, 'error')
  }
}

const groupedNewsItemConflicts = computed(() => {
  const grouped = {}
  for (const conflict of newsItemConflicts.value) {
    const storyId = conflict.incoming_story_id
    if (!grouped[storyId])
      grouped[storyId] = {
        title: conflict.incoming_story?.title || 'Untitled Story',
        fullStory: conflict.incoming_story,
        conflicts: []
      }
    grouped[storyId].conflicts.push({
      news_item_id: conflict.news_item_id,
      existing_story_id: conflict.existing_story_id
    })
  }
  return grouped
})

async function submitNewsItemResolution(storyId) {
  const group = groupedNewsItemConflicts.value[storyId]
  if (!group) return showToast('Story group not found.')

  const selected = selectedNewsItems.value[storyId] || []

  const conflictingIds = group.conflicts.map((c) => c.news_item_id)
  const unchecked = conflictingIds.filter((id) => !selected.includes(id))

  const payload = {
    resolution_data: {
      incoming_story: group.fullStory,
      checked_news_items: selected,
      unchecked_news_items: unchecked
    }
  }

  try {
    await store.resolveNewsItemConflict(payload)
    showToast(`News item conflicts resolved for story ${storyId}`, 'success')
    delete selectedNewsItems.value[storyId]
    await store.loadNewsItemConflicts()
  } catch (err) {
    showToast('Failed to resolve conflict.')
    console.error(err)
  }
}
async function submitAndRedirectNewsItemResolution(storyId) {
  const group = groupedNewsItemConflicts.value[storyId]
  if (!group) return showToast('Story group not found.')

  const selected = selectedNewsItems.value[storyId] || []
  const conflictingIds = group.conflicts.map((c) => c.news_item_id)
  const unchecked = conflictingIds.filter((id) => !selected.includes(id))

  const payload = {
    resolution_data: {
      incoming_story: group.fullStory,
      checked_news_items: selected,
      unchecked_news_items: unchecked
    }
  }

  // Open a blank tab immediately on click
  const newTab = window.open('about:blank', '_blank')

  try {
    await store.resolveNewsItemConflict(payload)
    showToast(`News item conflicts resolved for story ${storyId}`, 'success')
    delete selectedNewsItems.value[storyId]
    await store.loadNewsItemConflicts()

    const newStoryId = group.fullStory.id
    newTab.location.href = `/story/${newStoryId}`
  } catch (err) {
    newTab.close() // clean up the blank tab if the call failed
    showToast('Failed to resolve conflict.')
    console.error(err)
  }
}

function toggleStoryPreview(storyId) {
  const idx = expandedStories.value.indexOf(storyId)
  if (idx !== -1) expandedStories.value.splice(idx, 1)
  else expandedStories.value.push(storyId)
}

onMounted(async () => {
  await store.loadStoryConflicts()
  await store.fetchProposalCount()
  await store.loadNewsItemConflicts()
  await store.loadSummariesPerConflict()
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
