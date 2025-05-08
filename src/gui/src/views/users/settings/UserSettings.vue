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
            @click="saveUserSettings()"
          >
            {{ $t('button.save') }}
          </v-btn>
        </v-toolbar>
      </v-card-title>
      <v-card-text>
        <v-row justify="center" align="center">
          <v-col>
            <v-switch
              v-model="split_view"
              inset
              color="success"
              :label="$t('settings.split_view')"
            />
          </v-col>
          <v-col>
            <v-switch
              v-model="dark_theme"
              inset
              color="success"
              :label="$t('settings.dark_theme')"
            />
          </v-col>
          <v-col>
            <v-switch
              v-model="sseStatus"
              :label="sseLabel"
              :hint="sseConnectionState"
              persistent-hint
              color="success"
              inset
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-switch
              v-model="compact_view"
              inset
              color="success"
              :label="$t('settings.compact_view')"
            />
          </v-col>
          <v-col>
            <v-switch
              v-model="show_charts"
              inset
              color="success"
              :label="$t('settings.show_charts')"
            />
          </v-col>
          <v-col>
            <v-switch
              v-model="infinite_scroll"
              inset
              color="success"
              :label="$t('settings.infinite_scroll')"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-switch
              v-model="advanced_story_options"
              inset
              color="success"
              :label="$t('settings.advanced_story_options')"
            />
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
              menu-icon="mdi-chevron-down"
            />
          </v-col>
          <v-col cols="4" offset="1">
            {{ $t('settings.end_of_shift') }}
            <VueDatePicker
              v-model="end_of_shift"
              :clearable="false"
              time-picker
              auto-apply
              :label="$t('settings.end_of_shift')"
            />
          </v-col>
        </v-row>
        <hot-keys-legend />
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/UserStore'
import { useMainStore } from '@/stores/MainStore'
import HotKeysLegend from './HotKeysLegend.vue'
import { storeToRefs } from 'pinia'
import { sseHandler } from '@/utils/sse'

export default {
  name: 'UserSettings',
  components: {
    HotKeysLegend
  },
  setup() {
    const userStore = useUserStore()

    const {
      hotkeys,
      dark_theme,
      split_view,
      language,
      compact_view,
      show_charts,
      sseConnectionState,
      infinite_scroll,
      advanced_story_options,
      end_of_shift
    } = storeToRefs(userStore)

    const { sseConnectionError, coreSSEURL } = storeToRefs(useMainStore())

    const locale_descriptions = computed(() => [
      { value: 'en', text: 'English' },
      { value: 'de', text: 'Deutsch' },
      { value: 'sk', text: 'Slovensky' }
    ])

    const sseLabel = computed(() => {
      if (sseConnectionState.value === 'CONNECTING')
        return 'SSE Connecting... to ' + coreSSEURL.value
      if (sseConnectionState.value === 'OPEN')
        return 'SSE Connected to ' + coreSSEURL.value
      if (sseConnectionState.value === 'CLOSED')
        return 'SSE is not Connected. SSEURL: ' + coreSSEURL.value
      return 'Error Connecting to SSE ' + coreSSEURL.value
    })

    const sseStatus = computed({
      get: () => {
        return sseConnectionError.value === false
      },
      set: (val) => {
        console.debug('Setting sseStatus to', val)
        if (val) {
          sseConnectionError.value = false
          sseHandler()
        } else {
          sseConnectionError.value = 'Disabled by user'
        }
      }
    })

    function saveUserSettings() {
      userStore.saveUserProfile({
        split_view: split_view.value,
        compact_view: compact_view.value,
        show_charts: show_charts.value,
        dark_theme: dark_theme.value,
        hotkeys: hotkeys.value,
        language: language.value,
        infinite_scroll: infinite_scroll.value,
        advanced_story_options: advanced_story_options.value,
        end_of_shift: end_of_shift.value
      })
    }

    onMounted(() => {
      userStore.loadUserProfile()
    })

    return {
      language,
      locale_descriptions,
      sseLabel,
      sseStatus,
      dark_theme,
      split_view,
      compact_view,
      show_charts,
      infinite_scroll,
      advanced_story_options,
      end_of_shift,
      hotkeys,
      sseConnectionState,
      saveUserSettings
    }
  }
}
</script>
