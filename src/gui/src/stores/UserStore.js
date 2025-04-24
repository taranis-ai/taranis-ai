import { defineStore } from 'pinia'
import { getProfile, updateProfile, getUserDetails } from '@/api/user'
import { i18n } from '@/i18n/i18n'
import { vuetify } from '@/plugins/vuetify'
import { ref, computed } from 'vue'
import { useFilterStore } from './FilterStore'
import { notifyFailure, notifySuccess } from '@/utils/helpers'

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
    const advanced_story_options = ref(false)
    const end_of_shift = ref({ hours: 18, minutes: 0 })
    const language = ref('en')
    const sseConnectionState = ref('CLOSED')
    const filterStore = useFilterStore()

    const nextEndOfShift = computed(() => {
      const nextEOF = new Date()
      nextEOF.setDate(nextEOF.getDate() - 1)
      nextEOF.setHours(
        end_of_shift.value.hours,
        end_of_shift.value.minutes,
        0,
        0
      )
      return nextEOF
    })

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
      advanced_story_options.value = false
      end_of_shift.value = { hours: 18, minutes: 0 }
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
        setUserProfile(response.data.profile)
      })
    }

    function loadUserProfile() {
      getProfile().then((response) => {
        setUserProfile(response.data)
      })
    }

    async function saveUserProfile(data) {
      try {
        const response = await updateProfile(data)
        setUserProfile(data)
        notifySuccess(response.data.message)
      } catch (error) {
        notifyFailure(error)
      }
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
      end_of_shift.value = profile.end_of_shift || { hours: 18, minutes: 0 }
      infinite_scroll.value = profile.infinite_scroll
      advanced_story_options.value = profile.advanced_story_options

      i18n.global.locale.value = profile.language
      vuetify.theme.global.name.value = profile.dark_theme ? 'dark' : 'light'
      filterStore.setUserFilters(profile)
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
      advanced_story_options,
      end_of_shift,
      nextEndOfShift,
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
