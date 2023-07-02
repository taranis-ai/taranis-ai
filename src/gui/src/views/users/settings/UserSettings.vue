<template>
  <v-container fluid>
    <v-card variant="outlined">
      <v-card-title>
        <v-toolbar>
          <v-toolbar-title>
            {{ $t('settings.user_settings') }}
          </v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn
            color="success"
            variant="outlined"
            prepend-icon="mdi-content-save"
            @click="save()"
          >
            {{ $t('settings.save') }}
          </v-btn>
        </v-toolbar>
      </v-card-title>
      <v-card-text>
        <v-row justify="center" align="center">
          <v-col>
            <v-switch
              v-model="spellcheck"
              :label="$t('settings.spellcheck')"
            ></v-switch>
          </v-col>
          <v-col>
            <v-switch
              v-model="dark_theme"
              :label="$t('settings.dark_theme')"
            ></v-switch>
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="4">
            {{ language }}
            <v-autocomplete
              v-model="language"
              :items="locale_descriptions"
              :item-title="(item) => item.value + ' - ' + item.text"
              hint="Select your locale"
              :label="$t('settings.locale')"
            ></v-autocomplete>
          </v-col>
        </v-row>
        <h1 class="mt-5 mb-5">Hotkeys</h1>
        <v-row no-gutters class="ma-0">
          <v-tooltip v-for="shortcut in hotkeys" :key="shortcut.alias">
            <template #activator="{ props }">
              <v-btn
                :id="shortcut.alias"
                v-bind="props"
                class="blue lighten-5 ma-1"
                style="width: calc(100% / 3 - 8px)"
                :prepend-icon="shortcut.icon"
                @click.stop="pressKeyDialog(shortcut.alias)"
                @blur="pressKeyVisible = false"
              >
                <span v-if="shortcut.key">
                  {{ shortcut.key }}
                </span>
                <v-icon v-else color="error">mdi-alert</v-icon>
              </v-btn>
            </template>
            <span>
              {{ $t('settings.' + shortcut.alias) }}
            </span>
          </v-tooltip>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { ref, computed } from 'vue'
import { useSettingsStore } from '@/stores/SettingsStore'
import { storeToRefs } from 'pinia'
import { onMounted } from 'vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'UserSettings',
  setup() {
    const pressKeyVisible = ref(false)
    const hotkeyAlias = ref('')
    const shortcuts = ref([])

    const settingsStore = useSettingsStore()

    const { hotkeys, dark_theme, spellcheck, language } =
      storeToRefs(settingsStore)

    const locale_descriptions = computed(() => [
      { value: 'en-GB', text: 'English' },
      { value: 'de', text: 'Deutsch' },
      { value: 'sk', text: 'Slovensky' }
    ])

    const save = () => {
      settingsStore
        .saveUserProfile({
          spellcheck: spellcheck.value,
          dark_theme: dark_theme.value,
          hotkeys: shortcuts.value,
          language: language.value
        })
        .then(() => {
          notifySuccess('notification.successful_update')
        })
        .catch(() => {
          notifyFailure('notification.failed_update')
        })
    }

    const pressKeyDialog = (event) => {
      window.addEventListener('keydown', pressKey, false)

      pressKeyVisible.value = true
      hotkeyAlias.value = event
    }

    const pressKey = (event) => {
      const key = event
      const hotkeyIndex = hotkeys.value
        .map(function (e) {
          return e.alias
        })
        .indexOf(hotkeyAlias.value)

      window.removeEventListener('keydown', pressKey)

      pressKeyVisible.value = false

      // check doubles and clear
      // TODO: FIX
      shortcuts.value.forEach((doubleKey, i) => {
        if (doubleKey.key_code === key.keyCode && i !== hotkeyIndex) {
          shortcuts.value[i].key_code = 0
          shortcuts.value[i].key = 'undefined'
        }
      })

      // assigned new key
      hotkeys.value[hotkeyIndex].key_code = key.keyCode
      hotkeys.value[hotkeyIndex].key = key.code
    }

    onMounted(() => {
      settingsStore.loadUserProfile()
      shortcuts.value = hotkeys.value.map((shortcut) => {
        return {
          alias: shortcut.alias,
          key: shortcut.key || null,
          key_code: shortcut.key_code || null
        }
      })
    })

    return {
      pressKeyVisible,
      hotkeyAlias,
      shortcuts,
      language,
      locale_descriptions,
      dark_theme,
      spellcheck,
      hotkeys,
      save,
      pressKeyDialog,
      pressKey
    }
  }
}
</script>
