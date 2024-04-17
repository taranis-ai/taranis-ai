import { useHotkeys } from 'vue-use-hotkeys'
import { useAssessStore } from '@/stores/AssessStore'
import { useRouter } from 'vue-router'

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
      params: { id: assessStore.storySelection[0] }
    })
  })
}

export function storyHotkeys() {
  const assessStore = useAssessStore()

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
}
