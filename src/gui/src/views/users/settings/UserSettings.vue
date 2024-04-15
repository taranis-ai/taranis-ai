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
              v-model="split_view"
              color="success"
              :label="$t('settings.split_view')"
            ></v-switch>
          </v-col>
          <v-col>
            <v-switch
              v-model="dark_theme"
              color="success"
              :label="$t('settings.dark_theme')"
            ></v-switch>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-switch
              v-model="compact_view"
              color="success"
              :label="$t('settings.compact_view')"
            ></v-switch>
          </v-col>
          <v-col>
            <v-switch
              v-model="show_charts"
              color="success"
              :label="$t('settings.show_charts')"
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
        <hot-keys-legend />
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script>
import { computed } from 'vue'
import { useUserStore } from '@/stores/UserStore'
import { storeToRefs } from 'pinia'
import { onMounted } from 'vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import HotKeysLegend from './HotKeysLegend.vue'

export default {
  name: 'UserSettings',
  components: {
    HotKeysLegend
  },
  setup() {
    const userStore = useUserStore()

    const disableHotkeys = true

    const {
      hotkeys,
      dark_theme,
      split_view,
      language,
      compact_view,
      show_charts
    } = storeToRefs(userStore)

    const locale_descriptions = computed(() => [
      { value: 'en', text: 'English' },
      { value: 'de', text: 'Deutsch' },
      { value: 'sk', text: 'Slovensky' }
    ])

    const save = () => {
      userStore
        .saveUserProfile({
          split_view: split_view.value,
          compact_view: compact_view.value,
          show_charts: show_charts.value,
          dark_theme: dark_theme.value,
          hotkeys: hotkeys.value,
          language: language.value
        })
        .then(() => {
          notifySuccess('notification.successful_update')
        })
        .catch(() => {
          notifyFailure('notification.failed_update')
        })
    }

    onMounted(() => {
      userStore.loadUserProfile()
    })

    return {
      disableHotkeys,
      language,
      locale_descriptions,
      dark_theme,
      split_view,
      compact_view,
      show_charts,
      hotkeys,
      save
    }
  }
}
</script>
