import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getAllStoryConflicts,
  updateStory,
  getProposals,
  getAllNewsItemConflicts,
  fetchStorySummary,
  submitNewsItemConflictResolution
} from '@/api/connectors'

export const useConflictsStore = defineStore('conflicts', () => {
  const storyConflicts = ref([])
  const newsItemConflicts = ref([])
  const proposalCount = ref(0)
  const storySummaries = ref({})

  async function loadStoryConflicts() {
    try {
      const response = await getAllStoryConflicts()
      storyConflicts.value = response.data.conflicts
    } catch (error) {
      console.error('Error loading conflicts:', error)
    }
  }

  async function resolveStoryConflictById(storyId, resolutionData) {
    try {
      const response = await updateStory(storyId, resolutionData)
      return response.data
    } catch (error) {
      console.error(`Error resolving conflict for story ${storyId}:`, error)
      throw error
    }
  }

  async function fetchProposalCount() {
    try {
      const response = await getProposals()
      proposalCount.value = response.data.count
    } catch (error) {
      console.error('Error getting proposal count:', error)
    }
  }

  async function loadNewsItemConflicts() {
    try {
      const response = await getAllNewsItemConflicts()
      newsItemConflicts.value = response.data.conflicts
    } catch (error) {
      console.error('Error loading news item conflicts:', error)
    }
  }

  async function loadSummariesPerConflict() {
    const ids = [
      ...new Set(newsItemConflicts.value.map((c) => c.existing_story_id))
    ]
    for (const id of ids) {
      try {
        if (!storySummaries.value[id]) {
          const summary = await fetchStorySummary(id)
          storySummaries.value = {
            ...storySummaries.value,
            [id]: summary
          }
        }
      } catch (err) {
        console.error(`Failed to fetch summary for story ${id}`, err)
      }
    }
  }

  async function resolveNewsItemConflict(payload) {
    try {
      const response = await submitNewsItemConflictResolution(payload)
      return response.data
    } catch (error) {
      console.error('Error resolving news item conflict:', error)
      throw error
    }
  }

  return {
    storyConflicts,
    newsItemConflicts,
    proposalCount,
    storySummaries,
    loadStoryConflicts,
    fetchProposalCount,
    resolveStoryConflictById,
    loadNewsItemConflicts,
    loadSummariesPerConflict,
    resolveNewsItemConflict
  }
})
