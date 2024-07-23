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
    const infinite_scroll = ref(false)
    const end_of_shift = ref(null)
    const language = ref('en')
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
      infinite_scroll.value = false
      end_of_shift.value = null
      language.value = 'en'
      sseConnectionState.value = 'CLOSED'
    }

    function loadUser() {
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
        infinite_scroll.value = response.data.profile.infinite_scroll
        end_of_shift.value = response.data.profile.end_of_shift
        language.value = response.data.profile.language
        filterStore.setUserFilters(response.data.profile)
      })
    }

    function loadUserProfile() {
      getProfile().then((response) => {
        setUserProfile(response.data)
      })
    }

    async function saveUserProfile(data) {
      updateProfile(data).then(() => {
        setUserProfile(data)
      })
    }

    function hasPermission(permission) {
      return permissions.value.includes(permission)
    }

    function setUserProfile(profile) {
      split_view.value = profile.split_view
      compact_view.value = profile.compact_view
      show_charts.value = profile.show_charts
      dark_theme.value = profile.dark_theme
      language.value = profile.language
      end_of_shift.value = profile.end_of_shift
      infinite_scroll.value = profile.infinite_scroll

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
      sseConnectionState,
      infinite_scroll,
      end_of_shift,
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
