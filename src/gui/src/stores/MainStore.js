import { defineStore } from 'pinia'
import { getLocalConfig } from '@/services/config'
import { ref, computed } from 'vue'

export const useMainStore = defineStore(
  'main',
  () => {
    const vertical_view = ref(false)
    const itemCountTotal = ref(0)
    const itemCountFiltered = ref(0)
    const drawerVisible = ref(true)
    const drawerSetByUser = ref(false)
    const coreAPIURL = ref('/api')
    const sentryDSN = ref('')
    const gitInfo = ref('')
    const upstreamRepoUrl = ref('')
    const buildDate = ref(new Date().toISOString())
    const notification = ref({ message: '', type: '', show: false })

    // Getters
    const getItemCount = computed(() => {
      return { total: itemCountTotal.value, filtered: itemCountFiltered.value }
    })

    const updateFromLocalConfig = async () => {
      const config = await getLocalConfig()
      buildDate.value = config.BUILD_DATE ?? new Date().toISOString()
      gitInfo.value = config.GIT_INFO ?? ''
      coreAPIURL.value = config.TARANIS_CORE_API ?? '/api'
      sentryDSN.value = config.TARANIS_SENTRY_DSN ?? ''
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

    return {
      vertical_view,
      drawerVisible,
      drawerSetByUser,
      itemCountTotal,
      itemCountFiltered,
      coreAPIURL,
      gitInfo,
      buildDate,
      sentryDSN,
      notification,
      getItemCount,
      upstreamTreeUrl,
      gitUpstreamTreeUrl,
      updateFromLocalConfig,
      toggleDrawer,
      resetItemCount
    }
  },
  {
    persist: true
  }
)
