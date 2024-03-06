<template>
  <v-container fluid>
    <v-card variant="outlined">
      <v-card-title>
        <v-toolbar>
          <span class="align-self-center ml-3">
            {{ $t('settings.user_settings') }}
          </span>
          <v-spacer></v-spacer>
          <v-btn
            color="success"
            variant="outlined"
            prepend-icon="mdi-content-save"
            @click="save()"
          >
            {{ $t('button.save') }}
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
        <h2 style="background-color: #ffff00">
          HotKeys are currently not working, see
          <a
            href="https://github.com/taranis-ai/taranis-ai/issues/137"
            target="_blank"
          >
            Issue #137
          </a>
          for details
        </h2>
        <span> Press the button to change the hotkey. </span>
        <v-row no-gutters class="ma-0">
          <v-tooltip v-for="shortcut in hotkeys" :key="shortcut.alias">
            <template #activator="{ props }">
              <v-btn
                :id="shortcut.alias"
                v-bind="props"
                class="blue lighten-5 ma-1"
                style="width: calc(100% / 3 - 8px)"
                :prepend-icon="shortcut.icon"
                :disabled="disableHotkeys"
                @click.stop="pressKeyDialog(shortcut.alias)"
                @blur="pressKeyVisible = false"
              >
                <span v-if="shortcut.key">
                  {{ shortcut.key }}
                </span>
                <v-icon v-else color="error" icon="mdi-alert" />
              </v-btn>
            </template>
            <span>
              {{ shortcut.alias }}
            </span>
          </v-tooltip>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { ref, computed } from 'vue'
import { useUserStore } from '@/stores/UserStore'
import { storeToRefs } from 'pinia'
import { onMounted } from 'vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'UserSettings',
  setup() {
    const pressKeyVisible = ref(false)
    const hotkeyAlias = ref('')
    const shortcuts = ref([])

    const userStore = useUserStore()

    const disableHotkeys = true

    const { hotkeys, dark_theme, spellcheck, language } = storeToRefs(userStore)

    const locale_descriptions = computed(() => [
      { value: 'en', text: 'English' },
      { value: 'de', text: 'Deutsch' },
      { value: 'sk', text: 'Slovensky' }
    ])

    const save = () => {
      userStore
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
      userStore.loadUserProfile()
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
      disableHotkeys,
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
