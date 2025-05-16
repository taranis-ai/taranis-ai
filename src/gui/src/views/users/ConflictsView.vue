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
        News Item Conflict Resolution
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
              <v-alert type="info" variant="outlined" class="mb-4">
                <div class="text-subtitle-2 mb-1">
                  Incoming Story News Items
                </div>
                <ul class="pl-4">
                  <li
                    v-for="item in group.fullStory.news_items || []"
                    :key="item.id"
                  >
                    {{ item.title || 'Untitled' }}
                  </li>
                </ul>
              </v-alert>

              <v-table dense>
                <thead>
                  <tr>
                    <th>News Item Title</th>
                    <th>Existing Story</th>
                    <th>Decision</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="conflict in group.conflicts"
                    :key="conflict.news_item_id"
                  >
                    <td>
                      {{
                        group.fullStory.news_items?.find(
                          (item) => item.id === conflict.news_item_id
                        )?.title || 'Untitled'
                      }}
                    </td>
                    <td>
                      <div>
                        <a
                          :href="`/story/${conflict.existing_story_id}`"
                          target="_blank"
                        >
                          {{
                            storySummaries[conflict.existing_story_id]?.title ||
                            'Loading…'
                          }}
                        </a>
                        <ul class="text-caption text-grey-darken-1 pl-4 mt-1">
                          <li>
                            Relevance:
                            {{
                              storySummaries[conflict.existing_story_id]
                                ?.relevance ?? 'N/A'
                            }}
                          </li>
                          <li>
                            News Items:
                            {{
                              storySummaries[conflict.existing_story_id]
                                ?.news_item_count ?? 'N/A'
                            }}
                          </li>
                          <li
                            v-for="(t, i) in storySummaries[
                              conflict.existing_story_id
                            ]?.news_item_titles || []"
                            :key="i"
                          >
                            {{ t }}
                          </li>
                        </ul>
                      </div>
                    </td>
                    <td>
                      <v-radio-group
                        v-model="newsItemDecisions[conflict.news_item_id]"
                        row
                      >
                        <v-radio label="Keep in Incoming" value="incoming" />
                        <v-radio label="Keep in Existing" value="existing" />
                        <v-radio label="Dissolve Story" value="dissolve" />
                      </v-radio-group>
                    </td>
                  </tr>
                </tbody>
              </v-table>

              <v-btn
                color="success"
                class="mt-4"
                @click="submitNewsItemResolution(storyId)"
              >
                Submit Resolution
              </v-btn>
              <v-btn
                color="info"
                class="mt-4 ml-2"
                @click="submitAndRedirectNewsItemResolution(storyId)"
              >
                Submit & View Story
              </v-btn>

              <v-expand-transition>
                <div v-if="expandedStories.includes(storyId)">
                  <v-card class="mt-4" outlined>
                    <v-card-title class="text-subtitle-1"
                      >Full Incoming Story (JSON)</v-card-title
                    >
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
const newsItemDecisions = ref({})

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
      existing_story_id: conflict.existing_story_id,
      title: conflict.title || 'Untitled'
    })
  }
  return grouped
})

async function submitNewsItemResolution(storyId) {
  const group = groupedNewsItemConflicts.value[storyId]
  if (!group) return showToast('Story group not found.')

  const news_item_resolutions = group.conflicts.map((conflict) => ({
    news_item_id: conflict.news_item_id,
    decision: newsItemDecisions.value[conflict.news_item_id] || 'incoming'
  }))

  const resolution_data = {
    incoming_story: group.fullStory,
    news_item_resolutions
  }

  try {
    await store.resolveNewsItemConflict({ story_id: storyId, resolution_data })
    showToast(`Resolved news items for story ${storyId}`, 'success')
    await store.loadNewsItemConflicts()
  } catch (err) {
    showToast('Failed to resolve conflict.')
    console.error(err)
  }
}

async function submitAndRedirectNewsItemResolution(storyId) {
  const group = groupedNewsItemConflicts.value[storyId]
  if (!group) return showToast('Story group not found.')

  const news_item_resolutions = group.conflicts.map((conflict) => ({
    news_item_id: conflict.news_item_id,
    decision: newsItemDecisions.value[conflict.news_item_id] || 'incoming'
  }))

  const resolution_data = {
    incoming_story: group.fullStory,
    news_item_resolutions
  }

  const newTab = window.open('about:blank', '_blank')

  try {
    await store.resolveNewsItemConflict({ story_id: storyId, resolution_data })
    showToast(`Resolved news items for story ${storyId}`, 'success')
    await store.loadNewsItemConflicts()
    newTab.location.href = `/story/${group.fullStory.id}`
  } catch (err) {
    newTab.close()
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

  for (const conflict of newsItemConflicts.value) {
    const id = conflict.news_item_id
    if (!newsItemDecisions.value[id]) {
      if (
        conflict.existing_story_id &&
        storySummaries.value[conflict.existing_story_id]
      ) {
        newsItemDecisions.value[id] = 'existing'
      } else {
        newsItemDecisions.value[id] = 'incoming'
      }
    }
  }
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
