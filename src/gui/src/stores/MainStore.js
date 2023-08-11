import { defineStore } from 'pinia'
import { getLocalConfig } from '@/services/config'
import { ref, computed } from 'vue'

export const useMainStore = defineStore(
  'main',
  () => {
    const user = ref({
      id: '',
      name: '',
      organization_name: '',
      permissions: []
    })
    const vertical_view = ref(false)
    const itemCountTotal = ref(0)
    const itemCountFiltered = ref(0)
    const drawerVisible = ref(true)
    const coreAPIURL = ref('/api')
    const sentryDSN = ref('')
    const gitInfo = ref('')
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
      coreAPIURL.value = config.TARANIS_NG_CORE_API ?? '/api'
      sentryDSN.value = config.TARANIS_NG_SENTRY_DSN ?? ''
    }

    // Actions
    const toggleDrawer = () => {
      drawerVisible.value = !drawerVisible.value
    }

    const resetItemCount = () => {
      itemCountTotal.value = 0
      itemCountFiltered.value = 0
    }

    const reset_user = () => {
      user.value = {
        id: '',
        name: '',
        organization_name: '',
        permissions: []
      }
    }

    return {
      user,
      vertical_view,
      drawerVisible,
      itemCountTotal,
      itemCountFiltered,
      coreAPIURL,
      gitInfo,
      buildDate,
      sentryDSN,
      notification,
      getItemCount,
      updateFromLocalConfig,
      toggleDrawer,
      resetItemCount,
      reset_user
    }
  },
  {
    persist: true
  }
)
