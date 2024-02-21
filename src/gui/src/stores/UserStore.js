import { defineStore } from 'pinia'
import { getProfile, updateProfile, getUserDetails } from '@/api/user'
import { i18n } from '@/i18n/i18n'
import { vuetify } from '@/plugins/vuetify'
import { ref } from 'vue'

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
    const spellcheck = ref(true)
    const dark_theme = ref(false)
    const language = ref('en')

    const reset_user = () => {
      user_id.value = null
      name.value = ''
      username.value = ''
      roles.value = []
      permissions.value = []
      organization.value = null
      hotkeys.value = []
      spellcheck.value = true
      dark_theme.value = false
      language.value = 'en'
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
        spellcheck.value = response.data.profile.spellcheck
        dark_theme.value = response.data.profile.dark_theme
        language.value = response.data.profile.language
      })
    }

    const loadUserProfile = () => {
      getProfile().then((response) => {
        setUserProfile(response.data)
      })
    }

    const saveUserProfile = async (data) => {
      updateProfile(data).then((response) => {
        setUserProfile(response.data)
      })
    }

    const setUserProfile = (profile) => {
      spellcheck.value = profile.spellcheck
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
      hotkeys,
      spellcheck,
      dark_theme,
      language,
      loadUser,
      reset_user,
      loadUserProfile,
      saveUserProfile,
      setUserProfile
    }
  },
  {
    persist: true
  }
)
