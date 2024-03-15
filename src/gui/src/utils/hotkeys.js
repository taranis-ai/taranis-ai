import { useHotkeys } from 'vue-use-hotkeys'
import { useAssessStore } from '@/stores/AssessStore'

export function assessHotkeys() {
  const assessStore = useAssessStore()

  useHotkeys('esc', (event, handler) => {
    event.preventDefault()
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
