import { defineStore } from 'pinia'
import { getProfile, updateProfile } from '@/api/user'
import { i18n } from '@/i18n/i18n'
import { vuetify } from '@/plugins/vuetify'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    hotkeys: [
      // source group navigation
      {
        character: 'K',
        alias: 'source_group_up',
        icon: 'mdi-arrow-up-bold-box-outline'
      },
      {
        character: 'J',
        alias: 'source_group_down',
        icon: 'mdi-arrow-up-bold-box-outline'
      },
      // new item navigation
      {
        key_code: 38,
        key: 'ArrowUp',
        alias: 'collection_up',
        icon: 'mdi-arrow-up-bold-box-outline'
      },
      {
        key_code: 40,
        key: 'ArrowDown',
        alias: 'collection_down',
        icon: 'mdi-arrow-down-bold-box-outline'
      },
      {
        key_code: 37,
        key: 'ArrowLeft',
        alias: 'close_item',
        icon: 'mdi-close-circle-outline'
      },
      {
        key_code: 39,
        key: 'ArrowRight',
        alias: 'show_item',
        icon: 'mdi-text-box'
      },
      {
        character: 'k',
        alias: 'collection_up',
        icon: 'mdi-arrow-up-bold-box-outline'
      },
      {
        character: 'j',
        alias: 'collection_down',
        icon: 'mdi-arrow-down-bold-box-outline'
      },
      {
        character: 'h',
        alias: 'close_item',
        icon: 'mdi-close-circle-outline'
      },
      { character: 'l', alias: 'show_item', icon: 'mdi-text-box' },
      {
        key_code: 13,
        key: 'Enter',
        alias: 'show_item',
        icon: 'mdi-text-box'
      },
      {
        key_code: 27,
        key: 'Escape',
        alias: 'close_item',
        icon: 'mdi-close-circle-outline'
      },
      { key_code: 35, key: 'End', alias: 'end' },
      { key_code: 36, key: 'Home', alias: 'home' },
      // news item actions
      { character: 'r', alias: 'read_item', icon: 'mdi-eye' },
      { character: 'i', alias: 'important_item', icon: 'mdi-star' },
      { character: 'u', alias: 'like_item', icon: 'mdi-thumb-up' },
      { character: 'U', alias: 'dislike_item', icon: 'mdi-thumb-down' },
      {
        key_code: 46,
        key: 'Delete',
        alias: 'delete_item',
        icon: 'mdi-delete'
      },
      {
        character: 's',
        alias: 'selection',
        icon: 'mdi-checkbox-multiple-marked-outline'
      },
      { character: 'g', alias: 'group', icon: 'mdi-group' },
      { character: 'c', alias: 'cluster', icon: 'mdi:animation' },
      { character: 'G', alias: 'ungroup', icon: 'mdi-ungroup' },
      { character: 'n', alias: 'new_product', icon: 'mdi-file-outline' },
      {
        character: 'a',
        alias: 'story_open',
        icon: 'mdi-arrow-right-drop-circle'
      },
      { character: 'o', alias: 'open_item_source', icon: 'mdi-open-in-app' },
      {
        key_code: 191,
        key: 'Slash',
        alias: 'open_search',
        icon: 'mdi-card-search'
      },
      { character: 'R', alias: 'reload' },
      // filter actions
      { character: 'f', alias: 'enter_filter_mode' }
    ],
    spellcheck: true,
    dark_theme: false,
    language: 'en'
  }),
  actions: {
    async loadUserProfile() {
      const response = await getProfile()
      this.setUserProfile(response.data)
    },
    async saveUserProfile(data) {
      const response = await updateProfile(data)
      this.setUserProfile(response.data)
    },
    setUserProfile(profile) {
      this.spellcheck = profile.spellcheck
      this.dark_theme = profile.dark_theme
      this.language = profile.language

      i18n.global.locale.value = profile.language
      vuetify.theme.global.name.value = profile.dark_theme ? 'dark' : 'light'

      for (const hotkey of profile.hotkeys) {
        const stateHotkey = this.hotkeys.find((h) => h.alias === hotkey.alias)
        if (stateHotkey) {
          stateHotkey.key = hotkey.key
          stateHotkey.key_code = hotkey.key_code
        }
      }
    }
  }
})
