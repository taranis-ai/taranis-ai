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
            <v-card-title>{{ group.title }} (ID: {{ storyId }})</v-card-title>

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
                          :style="
                            existingIdsMap[storyId]?.has(item.id)
                              ? 'color: grey; opacity: 0.6'
                              : ''
                          "
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
                      <v-card-subtitle>Internal Story</v-card-subtitle>

                      <v-card-text>
                        <div class="text-caption text-muted mt-1">
                          ID: {{ cluster.id }} &mdash; Items:
                          {{ cluster.summary?.news_item_count ?? 0 }} &mdash;
                          Relevance: {{ cluster.summary?.relevance ?? 'n/a' }}
                        </div>
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
                            v-for="item in cluster.summary?.news_item_titles ||
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
const { resolveIngestIncomingStoryWrapper, resolveIngestUniqueNewsItems } =
  store

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

async function submitResolution(storyId) {
  const txt = mergedContents.value[storyId]
  if (!txt) return showToast('Get right side first')
  try {
    const data = JSON.parse(txt)
    await store.resolveStoryConflictById(storyId, data)
    const idx = storyConflicts.value.findIndex((x) => x.storyId === storyId)
    destroyMergely(storyConflicts.value[idx])
    storyConflicts.value.splice(idx, 1)
    openPanels.value = []
    prevPanels.value = []
    delete mergedContents.value[storyId]
    showToast(`Story ${storyId} resolved`, 'success')
  } catch {
    showToast(`Failed resolving ${storyId}`, 'error')
  }
}

function scrollToNextDiff(storyId) {
  try {
    storyConflicts.value
      .find((x) => x.storyId === storyId)
      .mergelyInstance.scrollToDiff('next')
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

const groupedNewsItemConflicts = computed(() => {
  const groups = {}
  for (const c of newsItemConflicts.value) {
    const id = c.incoming_story_id
    if (!groups[id])
      groups[id] = {
        title: c.incoming_story?.title || 'Untitled',
        fullStory: c.incoming_story,
        conflicts: []
      }
    groups[id].conflicts.push(c)
  }
  Object.values(groups).forEach((group) => {
    group.existingClusters = [
      ...new Set(group.conflicts.map((x) => x.existing_story_id))
    ].map((id) => ({ id, summary: storySummaries.value[id] }))
  })
  return groups
})

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
      cluster.summary?.news_item_titles?.forEach(
        (ni) => ni.id && set.add(ni.id)
      )
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

  const uniqueItems = incomingNewsItems.filter((item) => !existing.has(item.id))

  const skippedConflictingIds = incomingNewsItems
    .filter((item) => existing.has(item.id))
    .map((item) => item.id)

  keepInternalIngestNewsItems(storyId, uniqueItems, skippedConflictingIds)
}
async function keepInternalIngestNewsItems(
  storyId,
  uniqueItems,
  resolvedConflictIds
) {
  if (!uniqueItems.length && !resolvedConflictIds.length) {
    showToast('Nothing to ingest or resolve', 'info')
    return
  }

  try {
    const data = await resolveIngestUniqueNewsItems(
      storyId,
      uniqueItems,
      resolvedConflictIds
    )
    showToast(`Ingested ${data.added?.length || 0} item(s)`, 'success')
    await store.loadNewsItemConflicts()
  } catch (error) {
    console.error('Error ingesting unique news items:', error)
    showToast('Failed to ingest unique news items')
  }
}
async function replaceWithIncoming(storyId, newsItems) {
  const group = groupedNewsItemConflicts.value[storyId]
  const existingIds = group.existingClusters.map((c) => c.id)
  const newsItemIds = (newsItems || []).map((item) => item.id)
  await resolveIngestIncomingStoryWrapper({
    incoming_story: group.fullStory,
    existing_story_ids: existingIds,
    incoming_news_item_ids: newsItemIds
  })
  showToast(`Replaced clusters for ${storyId}`, 'success')
  await store.loadNewsItemConflicts()
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
</style>
