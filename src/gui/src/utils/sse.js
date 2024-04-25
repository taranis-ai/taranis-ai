import { useAssessStore } from '@/stores/AssessStore'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { usePublishStore } from '@/stores/PublishStore'
import { useMainStore } from '@/stores/MainStore'
import { useAuthStore } from '@/stores/AuthStore'
import { watch } from 'vue'
import { useEventSource } from '@vueuse/core'
import { notifyFailure } from '@/utils/helpers'

function defaultHandler(event) {
  console.debug('Default handler:', event)
}

export function sseHandler() {
  const assessStore = useAssessStore()
  const analyzeStore = useAnalyzeStore()
  const publishStore = usePublishStore()
  const mainStore = useMainStore()
  const authStore = useAuthStore()
  const sseEndpoint = `${mainStore.coreSSEURL}?jwt=${authStore.jwt}`

  if (mainStore.sseConnectionError) {
    return
  }

  const eventHandlers = {
    'news-items-updated': assessStore.sseNewsItemsUpdated,
    'report-item-updated': analyzeStore.sseReportItemUpdate,
    'product-rendered': publishStore.sseProductRendered,
    connected: defaultHandler,
    triggered: defaultHandler
  }

  const events = Object.keys(eventHandlers)

  const { status, data } = useEventSource(sseEndpoint, events, {
    autoReconnect: {
      retries: 3,
      delay: 1000,
      onFailed() {
        notifyFailure(`Failed to connect to ${sseEndpoint} after 3 retries`)
        mainStore.sseConnectionError = true
      }
    }
  })

  watch(status, (val) => {
    console.debug('SSE Status:', val)
  })

  watch(data, (val) => {
    console.debug('Data:', val)
  })
}
