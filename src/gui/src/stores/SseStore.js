import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { usePublishStore } from '@/stores/PublishStore'
import { useMainStore } from '@/stores/MainStore'

export const useSseStore = defineStore('sse', () => {
  const isConnected = ref(false)
  const reconnectionAttempts = ref(0)
  const maxReconnectionAttempts = 5
  let sseConnection = null

  const connectSSE = () => {
    if (sseConnection !== null && isConnected.value) {
      console.debug(
        'An SSE connection is already active. Skipping new connection.'
      )
      return
    }

    const assessStore = useAssessStore()
    const analyzeStore = useAnalyzeStore()
    const publishStore = usePublishStore()
    const mainStore = useMainStore()
    const sseEndpoint = `${mainStore.coreSSEURL}?jwt=${localStorage.ACCESS_TOKEN}`

    sseConnection = new EventSource(sseEndpoint)
    isConnected.value = true

    sseConnection.onerror = (event) => {
      isConnected.value = false
      console.error('SSE connection error:', event)
      sseConnection.close()
      if (reconnectionAttempts.value < maxReconnectionAttempts) {
        setTimeout(connectSSE, 5000)
        reconnectionAttempts.value += 1
      }
    }

    const eventHandlers = {
      'news-items-updated': assessStore.sseNewsItemsUpdated,
      'report-item-updated': analyzeStore.sseReportItemUpdate,
      'product-rendered': publishStore.sseProductRendered,
      connected: handleConnection
    }

    const events = Object.keys(eventHandlers)

    events.forEach((event) => {
      sseConnection.addEventListener(event, (e) => {
        const handler = eventHandlers[event]
        if (handler) {
          handler(JSON.parse(e.data))
        }
      })
    })
  }

  const handleConnection = (e) => {
    console.debug('SSE connection event:', e)
  }

  const resetSSE = () => {
    if (sseConnection) {
      sseConnection.close()
      console.debug('SSE connection closed.')
    }
    isConnected.value = false
    reconnectionAttempts.value = 0
  }

  return {
    isConnected,
    reconnectionAttempts,
    maxReconnectionAttempts,
    connectSSE,
    resetSSE
  }
})
