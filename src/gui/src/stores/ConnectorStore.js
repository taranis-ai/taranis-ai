import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getAllConflicts, updateStory, getProposals } from '@/api/connectors'

export const useConflictsStore = defineStore('conflicts', () => {
  const conflicts = ref([])
  const proposalCount = ref(0)

  async function loadConflicts() {
    try {
      const response = await getAllConflicts()
      conflicts.value = response.data.conflicts
    } catch (error) {
      console.error('Error loading conflicts:', error)
    }
  }

  async function resolveConflictById(storyId, resolutionData) {
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

  return {
    conflicts,
    loadConflicts,
    fetchProposalCount,
    resolveConflictById
  }
})
