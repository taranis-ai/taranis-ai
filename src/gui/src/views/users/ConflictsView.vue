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
            <v-card-text>
              <v-row>
                <v-col cols="6">
                  <v-card outlined>
                    <v-card-subtitle>Incoming Story</v-card-subtitle>
                    <v-card-text>
                      <div class="text-h6 mb-2">{{ group.title }}</div>
                      <ul class="news-item-list">
                        <li
                          v-for="item in group.fullStory.news_items || []"
                          :key="item.id"
                          :class="{
                            'item-grey': existingIdsMap[storyId]?.has(item.id),
                            'item-blue': duplicateIncomingNewsItemIds.has(
                              item.id
                            )
                          }"
                        >
                          {{ item.title || 'Untitled' }}
                        </li>
                      </ul>
                    </v-card-text>
                  </v-card>
                </v-col>

                <v-col cols="6">
                  <div
                    v-for="cluster in group.existingClusters"
                    :key="cluster.id"
                  >
                    <v-card outlined class="mb-4">
                      <v-card-subtitle class="pb-0">
                        <div
                          class="d-flex flex-wrap justify-space-between align-start w-100"
                        >
                          <div style="min-width: 0; max-width: 70%">
                            <div class="font-weight-medium">Internal Story</div>
                            <div class="text-caption text-muted">
                              ID: {{ cluster.id }} — Items:
                              {{ cluster.summary?.news_item_count ?? 0 }} —
                              Relevance:
                              {{ cluster.summary?.relevance ?? 'n/a' }}
                            </div>
                          </div>
                          <div
                            class="d-flex flex-wrap justify-end"
                            style="gap: 6px; max-width: 30%"
                          >
                            <v-chip
                              v-if="duplicateInternalStoryIds.has(cluster.id)"
                              color="info"
                              text-color="white"
                              small
                              label
                            >
                              Appears in multiple conflicts
                            </v-chip>
                            <v-chip
                              v-if="conflictingStoryIds.has(cluster.id)"
                              color="error"
                              text-color="white"
                              small
                              label
                            >
                              Has conflicting update
                            </v-chip>
                            <v-chip
                              v-if="cluster.summary?.is_misp_story"
                              color="deep-purple"
                              text-color="white"
                              small
                              label
                            >
                              MISP
                            </v-chip>
                          </div>
                        </div>
                      </v-card-subtitle>
                      <v-card-text>
                        <div class="mb-2">
                          <div class="text-h6">
                            <a
                              :href="`/story/${cluster.id}`"
                              target="_blank"
                              rel="noopener noreferrer"
                              class="story-link"
                            >
                              {{ cluster.summary?.title || 'Loading...' }}
                            </a>
                          </div>
                        </div>
                        <ul class="news-item-list">
                          <li
                            v-for="item in cluster.summary?.news_item_data ||
                            []"
                            :key="item.id"
                            :style="
                              incomingIdsMap[storyId]?.has(item.id)
                                ? 'color: red'
                                : ''
                            "
                          >
                            {{ item.title }}
                          </li>
                        </ul>
                      </v-card-text>
                    </v-card>
                  </div>
                </v-col>
              </v-row>

              <div class="d-flex mt-4 align-center">
                <v-btn
                  color="error"
                  @click="
                    replaceWithIncoming(storyId, group.fullStory.news_items)
                  "
                >
                  Ingest Incoming Story & Ungroup Local Stories
                </v-btn>
                <v-spacer />
                <div class="mr-4 text-caption" v-if="!hasUniqueItems(storyId)">
                  No new News Items to ingest
                </div>
                <v-btn
                  color="primary"
                  :disabled="!hasUniqueItems(storyId)"
                  @click="handleKeepInternal(storyId)"
                >
                  Keep Internal & Ingest Unique News Items
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>
<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useConflictsStore } from '@/stores/ConnectorStore'
import Mergely from 'mergely'
import 'mergely/lib/mergely.css'

const store = useConflictsStore()
const { storyConflicts, proposalCount, newsItemConflicts, storySummaries } =
  storeToRefs(store)
const {
  resolveIngestIncomingStoryWrapper,
  resolveIngestUniqueNewsItems,
  loadNewsItemConflicts,
  loadSummariesPerConflict,
  resolveStoryConflictById
} = store

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
  const id = `mergely-editor-${conflict.storyId}`
  const el = document.getElementById(id)
  if (!el) return
  const waitVisible = (cb) => {
    const isVisible = () => {
      const rect = el.getBoundingClientRect()
      return rect.width && rect.height && el.offsetParent
    }
    const check = () => (isVisible() ? cb() : requestAnimationFrame(check))
    requestAnimationFrame(check)
  }
  waitVisible(() => {
    try {
      const doc = new Mergely(`#${id}`, {
        license: 'gpl',
        lhs: conflict.original,
        rhs: conflict.updated,
        wrap_lines: true
      })
      doc.once('updated', () => doc.scrollToDiff('next'))
      conflict.mergelyInstance = doc
    } catch (e) {
      console.error(e)
    }
  })
}

function destroyMergely(conflict) {
  if (conflict?.mergelyInstance?.remove) {
    try {
      conflict.mergelyInstance.remove()
    } catch {}
    conflict.mergelyInstance = null
  }
}

async function getMergedContentForConflict(storyId) {
  const c = storyConflicts.value.find((x) => x.storyId === storyId)
  if (!c?.mergelyInstance) return showToast(`Editor not ready for ${storyId}`)
  await nextTick()
  const text = c.mergelyInstance.get('rhs')
  try {
    JSON.parse(text)
    mergedContents.value[storyId] = text
    showToast(`Valid JSON for ${storyId}`, 'success')
  } catch {
    showToast(`Invalid JSON for ${storyId}`, 'error')
  }
}

const groupedNewsItemConflicts = computed(() => {
  const groups = {}
  for (const c of newsItemConflicts.value) {
    const id = c.incoming_story_id
    if (!groups[id]) {
      groups[id] = {
        title: c.incoming_story?.title || 'Untitled',
        fullStory: c.incoming_story,
        conflicts: []
      }
    }
    groups[id].conflicts.push(c)
  }
  Object.values(groups).forEach((group) => {
    group.existingClusters = [
      ...new Set(group.conflicts.map((x) => x.existing_story_id))
    ].map((id) => ({
      id,
      summary: storySummaries.value[id]
    }))
  })
  return groups
})

const allNewsItemConflictStories = computed(() =>
  Object.values(groupedNewsItemConflicts.value).map((group) => group.fullStory)
)

async function submitResolution(storyId) {
  const conflict = storyConflicts.value.find((x) => x.storyId === storyId)
  if (!conflict) return showToast('Conflict not found')

  const txt = mergedContents.value[storyId]
  if (!txt) return showToast('Get right side first')

  let editedResolution
  try {
    editedResolution = JSON.parse(txt)
  } catch {
    return showToast('Invalid JSON after editing', 'error')
  }

  let originalRHS
  try {
    originalRHS = JSON.parse(conflict.updated)
  } catch {
    return showToast('Invalid original RHS JSON (unedited)', 'error')
  }

  try {
    await resolveStoryConflictById(storyId, {
      resolution: editedResolution,
      incoming_story_original: originalRHS,
      remaining_stories: allNewsItemConflictStories.value
    })

    destroyMergely(conflict)
    const idx = storyConflicts.value.findIndex((x) => x.storyId === storyId)
    storyConflicts.value.splice(idx, 1)
    openPanels.value = []
    prevPanels.value = []
    delete mergedContents.value[storyId]
    showToast(`Story ${storyId} resolved`, 'success')
  } catch (err) {
    console.error(err)
    showToast(`Failed resolving ${storyId}`, 'error')
  }
}

function scrollToNextDiff(storyId) {
  try {
    storyConflicts.value
      .find((x) => x.storyId === storyId)
      ?.mergelyInstance.scrollToDiff('next')
  } catch {
    showToast('Scroll error', 'error')
  }
}

function onPanelsUpdated(panels) {
  prevPanels.value
    .filter((i) => !panels.includes(i))
    .forEach((i) => destroyMergely(storyConflicts.value[i]))
  panels
    .filter((i) => !prevPanels.value.includes(i))
    .forEach((i) =>
      nextTick(() => initMergelyForConflict(storyConflicts.value[i]))
    )
  prevPanels.value = [...panels]
}

async function reloadNewsItemConflictViewState() {
  await loadNewsItemConflicts()
  storySummaries.value = {}
  await loadSummariesPerConflict()
}

const conflictingStoryIds = computed(
  () => new Set(storyConflicts.value.map((c) => c.storyId))
)

const incomingIdsMap = computed(() => {
  const map = {}
  Object.entries(groupedNewsItemConflicts.value).forEach(([id, group]) => {
    map[id] = new Set(group.fullStory.news_items?.map((x) => x.id) || [])
  })
  return map
})

const existingIdsMap = computed(() => {
  const map = {}
  Object.entries(groupedNewsItemConflicts.value).forEach(([id, group]) => {
    const set = new Set()
    group.existingClusters.forEach((cluster) => {
      cluster.summary?.news_item_data?.forEach((ni) => ni.id && set.add(ni.id))
    })
    map[id] = set
  })
  return map
})

function hasUniqueItems(storyId) {
  const group = groupedNewsItemConflicts.value[storyId]
  const existing = existingIdsMap.value[storyId] || new Set()
  return group.fullStory.news_items?.some((item) => !existing.has(item.id))
}

function handleKeepInternal(storyId) {
  const group = groupedNewsItemConflicts.value[storyId]
  if (!group) return
  const incomingNewsItems = group.fullStory.news_items || []
  const existing = existingIdsMap.value[storyId] || new Set()
  const skippedConflictingIds = incomingNewsItems
    .filter((item) => existing.has(item.id))
    .map((item) => item.id)
  keepInternalIngestNewsItems(storyId, incomingNewsItems, skippedConflictingIds)
}

async function keepInternalIngestNewsItems(
  storyId,
  incomingNewsItems,
  resolvedConflictIds
) {
  if (!incomingNewsItems.length && !resolvedConflictIds.length) {
    showToast('Nothing to ingest or resolve', 'info')
    return
  }
  try {
    const data = await resolveIngestUniqueNewsItems(
      storyId,
      incomingNewsItems,
      resolvedConflictIds,
      Object.entries(groupedNewsItemConflicts.value).map(
        ([_, otherGroup]) => otherGroup.fullStory
      )
    )
    showToast(`Ingested ${data.added?.length || 0} item(s)`, 'success')
    await reloadNewsItemConflictViewState()
  } catch (error) {
    console.error('Error ingesting unique news items:', error)
    showToast('Failed to ingest unique news items')
  }
}

async function replaceWithIncoming(storyId, newsItems) {
  const group = groupedNewsItemConflicts.value[storyId]
  const existingIds = group.existingClusters.map((c) => c.id)
  const newsItemIds = (newsItems || []).map((item) => item.id)
  snackbarMessage.value = 'Reevaluating conflicts...'
  snackbarColor.value = 'info'
  snackbar.value = true
  try {
    await resolveIngestIncomingStoryWrapper({
      resolving_story_id: storyId,
      incoming_story: group.fullStory,
      existing_story_ids: existingIds,
      incoming_news_item_ids: newsItemIds,
      remaining_stories: Object.entries(groupedNewsItemConflicts.value).map(
        ([_, otherGroup]) => otherGroup.fullStory
      )
    })
    snackbarMessage.value = `Replaced clusters for ${storyId}`
    snackbarColor.value = 'success'
    await reloadNewsItemConflictViewState()
  } catch (err) {
    console.error(err)
    snackbarMessage.value = 'Failed to resolve conflict'
    snackbarColor.value = 'error'
  } finally {
    setTimeout(() => {
      snackbar.value = false
    }, 3000)
  }
}

const duplicateInternalStoryIds = computed(() => {
  const mapping = {}
  for (const group of Object.values(groupedNewsItemConflicts.value)) {
    const incomingId = group.fullStory.id
    for (const conflict of group.conflicts) {
      const internalId = conflict.existing_story_id
      if (!internalId) continue
      if (!mapping[internalId]) {
        mapping[internalId] = new Set()
      }
      mapping[internalId].add(incomingId)
    }
  }
  return new Set(
    Object.entries(mapping)
      .filter(([_, set]) => set.size > 1)
      .map(([storyId]) => storyId)
  )
})

const duplicateIncomingNewsItemIds = computed(() => {
  const idCounts = {}
  Object.values(groupedNewsItemConflicts.value).forEach((group) => {
    for (const item of group.fullStory.news_items || []) {
      if (!item?.id) continue
      idCounts[item.id] = (idCounts[item.id] || 0) + 1
    }
  })
  return new Set(
    Object.entries(idCounts)
      .filter(([_, count]) => count > 1)
      .map(([id]) => id)
  )
})

onMounted(async () => {
  await store.loadStoryConflicts()
  await store.fetchProposalCount()
  await reloadNewsItemConflictViewState()
})
</script>

<style scoped>
.mergely-editor {
  border: 1px solid #ccc;
  height: 1000px;
}
.merged-pre {
  white-space: pre-wrap;
  word-break: break-word;
}
.proposal-link {
  color: inherit;
  text-decoration: none;
}
:deep(.internal-story-title a:hover) {
  text-decoration: underline;
  color: #1976d2;
}
.story-link {
  text-decoration: none;
  color: inherit;
  transition: color 0.2s ease;
}

.story-link:hover {
  text-decoration: underline;
  color: #1976d2;
}

.internal-story-meta {
  line-height: 1.3;
}

.text-muted {
  color: #6c757d;
  font-size: 0.85rem;
}

.news-item-list {
  padding-left: 1.25rem;
  margin: 0;
}

.news-item-list li {
  margin-bottom: 0.25rem;
}

.item-grey {
  color: grey;
  opacity: 0.6;
}

.item-red {
  color: red;
}

.item-blue {
  color: #074b86;
  font-weight: 500;
}
</style>
