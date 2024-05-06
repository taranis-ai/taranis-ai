import { defineStore } from 'pinia'
import { getProfile, updateProfile, getUserDetails } from '@/api/user'
import { i18n } from '@/i18n/i18n'
import { vuetify } from '@/plugins/vuetify'
import { ref } from 'vue'
import { useFilterStore } from './FilterStore'

export const useUserStore = defineStore(
  'user',
  () => {
    const user_id = ref(null)
    const username = ref('')
    const name = ref('')
    const roles = ref([])
    const permissions = ref([])
    const organization = ref(null)
    const hotkeys = ref([])
    const split_view = ref(false)
    const compact_view = ref(false)
    const show_charts = ref(false)
    const dark_theme = ref(false)
    const language = ref('en')
    const drawer_visible = ref(true)
    const drawer_set_by_user = ref(false)
    const sseConnectionState = ref('CLOSED')
    const filterStore = useFilterStore()

    const reset_user = () => {
      user_id.value = null
      name.value = ''
      username.value = ''
      roles.value = []
      permissions.value = []
      organization.value = null
      hotkeys.value = []
      split_view.value = false
      compact_view.value = false
      show_charts.value = false
      dark_theme.value = false
      drawer_set_by_user.value = false
      drawer_visible.value = true
      language.value = 'en'
      sseConnectionState.value = 'CLOSED'
    }

    const loadUser = () => {
      getUserDetails().then((response) => {
        user_id.value = response.data.id
        name.value = response.data.name
        username.value = response.data.username
        roles.value = response.data.roles
        permissions.value = response.data.permissions
        organization.value = response.data.organization
        hotkeys.value = response.data.profile.hotkeys
        split_view.value = response.data.profile.split_view
        compact_view.value = response.data.profile.compact_view
        show_charts.value = response.data.profile.show_charts
        dark_theme.value = response.data.profile.dark_theme
        language.value = response.data.profile.language
        filterStore.setUserFilters(response.data.profile)
      })
    }

    const loadUserProfile = () => {
      getProfile().then((response) => {
        setUserProfile(response.data)
      })
    }

    const saveUserProfile = async (data) => {
      updateProfile(data).then(() => {
        setUserProfile(data)
      })
    }

    const hasPermission = (permission) => {
      return permissions.value.includes(permission)
    }

    const setUserProfile = (profile) => {
      split_view.value = profile.split_view
      compact_view.value = profile.compact_view
      show_charts.value = profile.show_charts
      dark_theme.value = profile.dark_theme
      language.value = profile.language

      i18n.global.locale.value = profile.language
      vuetify.theme.global.name.value = profile.dark_theme ? 'dark' : 'light'
    }

    return {
      user_id,
      username,
      name,
      roles,
      permissions,
      organization,
      drawer_visible,
      drawer_set_by_user,
      sseConnectionState,
      hotkeys,
      split_view,
      compact_view,
      show_charts,
      dark_theme,
      language,
      loadUser,
      reset_user,
      hasPermission,
      loadUserProfile,
      saveUserProfile,
      setUserProfile
    }
  },
  {
    persist: true
  }
)
