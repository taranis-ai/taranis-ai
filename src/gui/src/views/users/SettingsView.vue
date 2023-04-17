<template>
  <v-container>
    <v-card>
      <v-row class="pb-5">
        <h1>{{ $t('settings.user_settings') }}</h1>
        <v-btn color="success" @click="save()">
          <v-icon left>mdi-content-save</v-icon>
          <span>{{ $t('settings.save') }}</span>
        </v-btn>
      </v-row>

      <v-tabs dark centered grow height="32">
        <!-- TABS -->
        <v-tab href="#tab-1">
          <span>{{ $t('settings.tab_general') }}</span>
        </v-tab>
        <v-tab href="#tab-2" @click="loadWordList()">
          <span>{{ $t('settings.tab_wordlists') }}</span>
        </v-tab>
        <v-tab href="#tab-3">
          <span>{{ $t('settings.tab_hotkeys') }}</span>
        </v-tab>

        <!-- #tab-1 -->
        <v-tab-item value="tab-1" class="pa-0">
          <v-container fluid>
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
                  @change="darkToggle"
                  :label="$t('settings.dark_theme')"
                ></v-switch>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="4">
                <v-autocomplete
                  v-model="browser_locale"
                  :items="locale_descriptions"
                  :item-text="(item) => item.value + ' - ' + item.text"
                  hint="Select your locale"
                  :label="$t('settings.locale')"
                  solo
                  persistent-hint
                ></v-autocomplete>
              </v-col>
            </v-row>
          </v-container>
        </v-tab-item>

        <!-- #tab-2 -->
        <v-tab-item value="tab-2" class="pa-0">
          <v-container fluid>
            <v-data-table
              v-model="selected_word_lists"
              :headers="headers"
              :items="word_lists"
              item-key="id"
              show-select
              class="elevation-1"
            >
              <template v-slot:top>
                <v-toolbar flat color="white">
                  <v-toolbar-title>
                    {{ $t('osint_source.word_lists') }}
                  </v-toolbar-title>
                </v-toolbar>
              </template>
            </v-data-table>
          </v-container>
        </v-tab-item>

        <!-- #tab-3 -->
        <v-tab-item value="tab-3" class="pa-0">
          <v-container fluid>
            <v-row no-gutters class="ma-0">
              <v-tooltip
                top
                v-for="shortcut in shortcuts"
                :key="shortcut.alias"
              >
                <template v-slot:activator="{ on }">
                  <v-btn
                    :id="shortcut.alias"
                    v-on="on"
                    class="blue lighten-5 ma-1"
                    style="width: calc(100% / 3 - 8px)"
                    text
                    @click.stop="pressKeyDialog(shortcut.alias)"
                    @blur="pressKeyVisible = false"
                  >
                    <v-icon left>{{ shortcut.icon }}</v-icon>
                    <span v-if="shortcut.key != 'undefined'" class="caption">
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
          </v-container>
        </v-tab-item>
      </v-tabs>
    </v-card>
  </v-container>
</template>

<script>
import AuthMixin from '@/services/auth/auth_mixin'
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'UserSettings',
  components: {},
  mixins: [AuthMixin],
  data: () => ({
    visible: false,
    dark_theme: false,
    spellcheck: null,
    pressKeyVisible: false,
    shortcuts: [],
    hotkeyAlias: String,
    headers: [
      {
        text: 'Name',
        align: 'start',
        value: 'name'
      },
      { text: 'Description', value: 'description' }
    ],
    word_lists: [],
    selected_word_lists: []
  }),
  computed: {
    browser_locale: {
      get() {
        return this.getProfileBrowserLocale()
      },
      set(value) {
        this.$i18n.locale = value
        this.setLocale(value)
        console.warn('TODO: extend user profile to include locale')
        // TODO: extend user profile to include locale
        // this.saveUserProfile({ browser_locale: value })
      }
    },
    locale_descriptions() {
      return [
        { value: 'en', text: 'English' },
        { value: 'de', text: 'Deutsch' },
        { value: 'sk', text: 'Slovensky' }
      ]
    }
  },
  methods: {
    ...mapGetters('settings', [
      'getProfileSpellcheck',
      'getProfileDarkTheme',
      'getProfileHotkeys',
      'getProfileWordLists',
      'getProfileBrowserLocale'
    ]),
    ...mapActions('settings', ['saveUserProfile', 'setLocale']),
    ...mapActions('config', ['loadWordLists']),
    ...mapGetters('config', ['getWordLists']),
    save() {
      this.saveUserProfile({
        spellcheck: this.spellcheck,
        dark_theme: this.dark_theme,
        hotkeys: this.shortcuts,
        word_lists: this.selected_word_lists
      }).then(() => {
        this.visible = false
      })
    },

    darkToggle() {
      this.$vuetify.theme.dark = this.dark_theme
    },

    pressKeyDialog(event) {
      window.addEventListener('keydown', this.pressKey, false)

      this.pressKeyVisible = true
      this.hotkeyAlias = event
    },

    loadWordList() {
      this.loadWordLists().then(() => {
        this.word_lists = this.getWordLists().items
      })
    },

    pressKey(event) {
      const key = event
      const hotkeyIndex = this.shortcuts
        .map(function (e) {
          return e.alias
        })
        .indexOf(this.hotkeyAlias)

      window.removeEventListener('keydown', this.pressKey)

      this.pressKeyVisible = false

      // check doubles and clear
      this.shortcuts.forEach((doubleKey, i) => {
        if (doubleKey.key_code === key.keyCode && i !== hotkeyIndex) {
          this.shortcuts[i].key_code = 0
          this.shortcuts[i].key = 'undefined'
        }
      })

      // assigned new key
      this.shortcuts[hotkeyIndex].key_code = key.keyCode
      this.shortcuts[hotkeyIndex].key = key.code
    }
  },
  mounted() {
    this.visible = true
    this.spellcheck = this.getProfileSpellcheck()
    this.dark_theme = this.getProfileDarkTheme()
    this.selected_word_lists = this.getProfileWordLists()
    this.shortcuts = this.getProfileHotkeys()
    this.loadWordList()
  }
}
</script>
