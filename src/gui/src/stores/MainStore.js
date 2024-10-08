import { defineStore } from 'pinia'
import { getLocalConfig } from '@/services/config'
import { ref, computed } from 'vue'

export const useMainStore = defineStore(
  'main',
  () => {
    const itemCountTotal = ref(0)
    const itemCountFiltered = ref(0)
    const drawerVisible = ref(true)
    const drawerSetByUser = ref(false)
    const coreAPIURL = ref('/api')
    const coreSSEURL = ref('/sse')
    const sentryDSN = ref('')
    const gitInfo = ref('')
    const upstreamRepoUrl = ref('')
    const buildDate = ref(new Date().toISOString())
    const notification = ref({ message: '', type: '', show: false })
    const sseConnectionError = ref(false)
    const hotkeyDialogVisible = ref(false)

    // Getters
    const getItemCount = computed(() => {
      return { total: itemCountTotal.value, filtered: itemCountFiltered.value }
    })

    const updateFromLocalConfig = async () => {
      const config = await getLocalConfig()
      buildDate.value = config.BUILD_DATE ?? new Date().toISOString()
      gitInfo.value = config.GIT_INFO ?? ''

      if (/^https?:\/\//.test(config.TARANIS_CORE_API)) {
        coreAPIURL.value = config.TARANIS_CORE_API
      } else {
        coreAPIURL.value =
          [import.meta.env.BASE_URL, config.TARANIS_CORE_API]
            .join('/')
            .replace(/\/{2,}/g, '/') ?? '/api'
      }

      coreSSEURL.value =
        config.TARANIS_SSE_URL ??
        coreAPIURL.value.replace('/api', '/sse') ??
        '/sse'
      sentryDSN.value = config.TARANIS_GUI_SENTRY_DSN ?? ''
      upstreamRepoUrl.value =
        config.TARANIS_UPSTREAM_REPO_URL ??
        'https://github.com/taranis-ai/taranis-ai'
    }

    const upstreamTreeUrl = computed(() => {
      return gitUpstreamTreeUrl(gitInfo.value)
    })

    // Actions
    const gitUpstreamTreeUrl = (gitBranchInfo) => {
      if (gitBranchInfo?.HEAD) {
        return `${upstreamRepoUrl.value}/tree/${gitBranchInfo.HEAD}`
      }
      return upstreamRepoUrl.value
    }

    const toggleDrawer = () => {
      drawerVisible.value = !drawerVisible.value
      drawerSetByUser.value = true
    }

    const resetItemCount = () => {
      itemCountTotal.value = 0
      itemCountFiltered.value = 0
    }

    const setItemCount = (total, filtered) => {
      itemCountTotal.value = total
      itemCountFiltered.value = filtered
    }

    const reset = () => {
      itemCountTotal.value = 0
      itemCountFiltered.value = 0
      drawerVisible.value = true
      drawerSetByUser.value = false
      coreAPIURL.value = '/api'
      coreSSEURL.value = '/sse'
      sentryDSN.value = ''
      gitInfo.value = ''
      buildDate.value = new Date().toISOString()
      notification.value = { message: '', type: '', show: false }
      sseConnectionError.value = false
      hotkeyDialogVisible.value = false
    }

    return {
      drawerVisible,
      drawerSetByUser,
      itemCountTotal,
      itemCountFiltered,
      coreAPIURL,
      coreSSEURL,
      gitInfo,
      buildDate,
      sentryDSN,
      notification,
      getItemCount,
      upstreamTreeUrl,
      sseConnectionError,
      hotkeyDialogVisible,
      gitUpstreamTreeUrl,
      updateFromLocalConfig,
      toggleDrawer,
      setItemCount,
      resetItemCount,
      reset
    }
  },
  {
    persist: true
  }
)
