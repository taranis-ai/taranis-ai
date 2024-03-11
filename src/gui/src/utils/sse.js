import { useAssessStore } from '@/stores/AssessStore'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { usePublishStore } from '@/stores/PublishStore'

let sseConnection = null

export function connectSSE() {
  const coreAPIURL = import.meta.env.VITE_TARANIS_CORE_SSE
  if (!coreAPIURL) {
    console.error('SSE URL is not defined.')
    return
  }

  const sseEndpoint = `${coreAPIURL}/sse`
  sseConnection = new EventSource(sseEndpoint)
  const assessStore = useAssessStore()
  const analyzeStore = useAnalyzeStore()
  const publishStore = usePublishStore()

  sseConnection.onopen = () => console.debug('SSE connection opened.')

  sseConnection.onerror = (event) => {
    console.error('SSE connection error:', event)
    sseConnection.close()
    setTimeout(connectSSE, 5000)
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

export function reconnectSSE() {
  if (sseConnection) {
    sseConnection.close()
    console.debug('SSE connection closed.')
  }
  connectSSE()
}
