import { useAssessStore } from '@/stores/AssessStore'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { usePublishStore } from '@/stores/PublishStore'
import { useMainStore } from '@/stores/MainStore'
import { useAuthStore } from '@/stores/AuthStore'
import { useUserStore } from '@/stores/UserStore'
import { watch } from 'vue'
import { useEventSource } from '@vueuse/core'
import { sseConnected } from '@/api/user'

function defaultHandler(data) {
  console.info('Default handler:', data)
}

export function sseHandler() {
  const assessStore = useAssessStore()
  const analyzeStore = useAnalyzeStore()
  const publishStore = usePublishStore()
  const mainStore = useMainStore()
  const authStore = useAuthStore()
  const userStore = useUserStore()
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

  const { status, data, event } = useEventSource(sseEndpoint, events, {
    autoReconnect: {
      retries: 3,
      delay: 1000,
      onFailed() {
        console.error(`Failed to connect to ${sseEndpoint} after 3 retries`)
        mainStore.sseConnectionError = true
        userStore.sseConnectionState = 'ERROR'
      }
    }
  })

  if (mainStore.sseConnectionError) {
    return
  }

  userStore.sseConnectionState = status.value

  if (status.value === 'CONNECTING') {
    setTimeout(() => {
      sseConnected()
    }, 1000)
  }

  watch(data, (val) => {
    console.debug(`SSE Data: ${val} - Event: ${event.value}`)
    if (event.value in eventHandlers) {
      eventHandlers[event.value](val)
    }
  })
}
