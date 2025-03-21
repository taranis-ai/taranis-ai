import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getAllConflicts, resolveConflict } from '@/api/conflicts'

export const useConflictsStore = defineStore('conflicts', () => {
  const conflicts = ref([])

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
      const response = await resolveConflict(storyId, resolutionData)
      // Remove the resolved conflict from the list
      conflicts.value = conflicts.value.filter(
        (conflict) => conflict.storyId !== storyId
      )
      return response.data
    } catch (error) {
      console.error(`Error resolving conflict for story ${storyId}:`, error)
      throw error
    }
  }

  return {
    conflicts,
    loadConflicts,
    resolveConflictById
  }
})
