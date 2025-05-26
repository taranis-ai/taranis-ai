import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getAllStoryConflicts,
  updateStory,
  getProposals,
  getAllNewsItemConflicts,
  fetchStorySummary,
  submitNewsItemConflictResolution,
  ungroupNewsItems as cleanInternallyIngestIncoming,
  addIncomingStory,
  addUniqueNewsItems
} from '@/api/connectors'

export const useConflictsStore = defineStore('conflicts', () => {
  const storyConflicts = ref([])
  const newsItemConflicts = ref([])
  const proposalCount = ref(0)
  const storySummaries = ref({})

  async function loadStoryConflicts() {
    try {
      const { data } = await getAllStoryConflicts()
      storyConflicts.value = data.conflicts
    } catch (error) {
      console.error('Error loading story conflicts:', error)
    }
  }

  async function resolveStoryConflictById(storyId, resolutionData) {
    try {
      const { data } = await updateStory(storyId, resolutionData)
      return data
    } catch (error) {
      console.error(`Error resolving story ${storyId}:`, error)
      throw error
    }
  }

  async function fetchProposalCount() {
    try {
      const { data } = await getProposals()
      proposalCount.value = data.count
    } catch (error) {
      console.error('Error fetching proposal count:', error)
    }
  }

  async function loadNewsItemConflicts() {
    try {
      const { data } = await getAllNewsItemConflicts()
      newsItemConflicts.value = data.conflicts
    } catch (error) {
      console.error('Error loading news-item conflicts:', error)
    }
  }

  async function loadSummariesPerConflict() {
    const ids = [
      ...new Set(
        newsItemConflicts.value.flatMap((c) => [
          c.existing_story_id,
          c.incoming_story_id
        ])
      )
    ]
    for (const id of ids) {
      if (!storySummaries.value[id]) {
        try {
          const summary = await fetchStorySummary(id)
          storySummaries.value[id] = summary
        } catch (err) {
          console.error(`Error fetching summary ${id}:`, err)
        }
      }
    }
  }

  async function resolveNewsItemConflict(payload) {
    try {
      const { data } = await submitNewsItemConflictResolution(payload)
      return data
    } catch (error) {
      console.error('Error resolving news-item conflict:', error)
      throw error
    }
  }

  async function ingestIncomingStory(storyPayload) {
    const { incoming_story, existing_story_ids, incoming_news_item_ids } =
      storyPayload

    try {
      await cleanInternallyIngestIncoming(storyPayload)
    } catch (error) {
      console.error('Error ungrouping news items:', error)
      throw error
    }
  }

  async function ingestUniqueNewsItems(
    storyId,
    uniqueItems,
    resolvedConflictIds = []
  ) {
    if (!Array.isArray(uniqueItems) && !Array.isArray(resolvedConflictIds)) {
      console.warn('No input provided')
      return
    }

    const payload = {
      story_id: storyId,
      news_items: uniqueItems,
      resolved_conflict_item_ids: resolvedConflictIds
    }

    try {
      const { data } = await addUniqueNewsItems(payload)
      console.log(
        `Added: ${data.added?.length || 0}, Skipped: ${resolvedConflictIds.length}`
      )
      await loadNewsItemConflicts()
      return data
    } catch (error) {
      console.error('Error ingesting unique news items:', error)
      throw error
    }
  }

  return {
    storyConflicts,
    newsItemConflicts,
    proposalCount,
    storySummaries,
    loadStoryConflicts,
    resolveStoryConflictById,
    fetchProposalCount,
    loadNewsItemConflicts,
    loadSummariesPerConflict,
    resolveNewsItemConflict,
    ingestIncomingStory,
    ingestUniqueNewsItems
  }
})
