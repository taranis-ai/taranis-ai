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
    const sseEndpoint = `${mainStore.coreAPIURL}/sse?jwt=${localStorage.ACCESS_TOKEN}`

    sseConnection = new EventSource(sseEndpoint)

    sseConnection.onopen = () => {
      isConnected.value = true
      console.debug('SSE connection opened.')
    }

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
      'product-rendered': publishStore.sseProductRendered
    }

    const events = Object.keys(eventHandlers)

    events.forEach((event) => {
      sseConnection.addEventListener(event, (e) => {
        const handler = eventHandlers[event]
        if (handler) {
          handler()
          console.debug(`Event received - ${event}:`, e.data)
        }
      })
    })
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
