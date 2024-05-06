import { useHotkeys } from 'vue-use-hotkeys'
import { useAssessStore } from '@/stores/AssessStore'
import { useRouter, useRoute } from 'vue-router'

// TODO: Consider switching to https://vueuse.org/core/useMagicKeys/

export function omniSearchHotkey() {
  useHotkeys('ctrl+k', (event, handler) => {
    event.preventDefault()
    console.debug(`You pressed ${handler.key}`)
    const searchInput = document.getElementById('omni-search')
    if (searchInput) {
      searchInput.focus()
    }
  })
}

export function assessHotkeys() {
  const assessStore = useAssessStore()
  const router = useRouter()

  omniSearchHotkey()

  useHotkeys('esc', (event, handler) => {
    console.debug(`You pressed ${handler.key}`)
    assessStore.clearSelection()
  })

  useHotkeys('ctrl+a', (event, handler) => {
    event.preventDefault()
    console.debug(`You pressed ${handler.key}`)
    assessStore.selectAllItems()
  })

  useHotkeys('ctrl+space', (event, handler) => {
    event.preventDefault()
    console.debug(`You pressed ${handler.key}`)
    assessStore.markSelectionAsRead()
  })

  useHotkeys('ctrl+i', (event, handler) => {
    event.preventDefault()
    console.debug(`You pressed ${handler.key}`)
    assessStore.markSelectionAsImportant()
  })

  useHotkeys('ctrl+e', (event, handler) => {
    event.preventDefault()
    if (assessStore.storySelection.length !== 1) {
      return
    }
    console.debug(`You pressed ${handler.key}`)
    router.push({
      name: 'storyedit',
      params: { storyId: assessStore.storySelection[0] }
    })
  })
}

export function storyHotkeys() {
  const assessStore = useAssessStore()
  const router = useRouter()
  const route = useRoute()
  const story_id = route.params.id

  omniSearchHotkey()

  useHotkeys('ctrl+space', (event, handler) => {
    event.preventDefault()
    console.debug(`You pressed ${handler.key}`)
    assessStore.markStoryAsRead(story_id)
  })

  useHotkeys('ctrl+i', (event, handler) => {
    event.preventDefault()
    console.debug(`You pressed ${handler.key}`)
    assessStore.markStoryAsImportant(story_id)
  })

  useHotkeys('ctrl+e', (event, handler) => {
    event.preventDefault()
    console.debug(`You pressed ${handler.key}`)
    router.push({
      name: 'storyedit',
      params: { storyId: story_id }
    })
  })
}
