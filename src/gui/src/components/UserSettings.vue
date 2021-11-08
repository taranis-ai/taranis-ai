<template>
    <div>
        <v-row justify="center">
            <v-dialog v-model="visible" max-width="800" class="user-settings-dialog" @keydown.esc="close">
                <v-card>
                    <v-toolbar dark dense color="primary">
                        <v-btn icon dark @click="close()">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title class="title-limit">{{$t('settings.user_settings')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn text @click="save()">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('settings.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-tabs dark centered grow height="32">
                        <!-- TABS -->
                        <v-tab href="#tab-1">
                            <span>{{$t('settings.tab_general')}}</span>
                        </v-tab>
                        <v-tab href="#tab-2">
                            <span>{{$t('settings.tab_wordlists')}}</span>
                        </v-tab>
                        <v-tab href="#tab-3">
                            <span>{{$t('settings.tab_hotkeys')}}</span>
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
                                            v-model="dark_theme" @change="darkToggle"
                                            :label="$t('settings.dark_theme')"
                                        ></v-switch>
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
                                            <v-toolbar-title>{{$t('osint_source.word_lists')}}</v-toolbar-title>
                                        </v-toolbar>
                                    </template>

                                </v-data-table>
                            </v-container>
                        </v-tab-item>

                        <!-- #tab-3 -->
                        <v-tab-item value="tab-3" class="pa-0">
                            <v-container fluid class="">
                                <v-row no-gutters class="ma-0">
                                    <v-tooltip top v-for="shortcut in shortcuts" :key="shortcut.alias">
                                        <template v-slot:activator="{on}">
                                            <v-btn  :id=shortcut.alias v-on="on"
                                                    class="blue lighten-5 ma-1" style="width: calc(100% / 3 - 8px);"
                                                    text
                                                    @click.stop="pressKeyDialog(shortcut.alias)"
                                                    @blur="pressKeyVisible = false"
                                            >
                                                <v-icon left>{{shortcut.icon}}</v-icon>
                                                <span v-if="shortcut.key != 'undefined'" class="caption">{{shortcut.key}}</span>
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
            </v-dialog>

            <!-- Press Key Dialog -->
            <template>
                <div class="text-center">
                    <v-dialog
                            v-model="pressKeyVisible"
                            width="300"
                            persistent
                            v-on:keydown="pressKey"
                    >
                        <v-card color="primary" dark>
                            <v-card-text class="white--text">
                                {{$t('settings.press_key')}}<span class="font-weight-bold">{{$t('settings.' + hotkeyAlias)}}</span>
                                <v-progress-linear
                                        indeterminate
                                        color="white"
                                        class="mb-0"
                                ></v-progress-linear>
                            </v-card-text>
                        </v-card>
                    </v-dialog>
                </div>
            </template>
        </v-row>
    </div>
</template>

<script>
    import Permissions from "@/services/auth/permissions";
    import AuthMixin from "@/services/auth/auth_mixin";

    export default {
        name: "UserSettings",
        components: {
        },
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
                    value: 'name',
                },
                {text: 'Description', value: 'description'},
            ],
            word_lists: [],
            selected_word_lists: []
        }),
        methods: {
            close() {
                this.visible = false;
                this.$vuetify.theme.dark = this.$store.getters.getDarkTheme
            },

            save() {
                this.$store.dispatch('saveUserProfile', {
                    spellcheck: this.spellcheck,
                    dark_theme: this.dark_theme,
                    hotkeys: this.shortcuts,
                    word_lists: this.selected_word_lists,
                }).then(() => {
                    this.visible = false;
                });
            },

            darkToggle() {
                this.$vuetify.theme.dark = this.dark_theme
            },

            pressKeyDialog(event) {
                window.addEventListener("keydown", this.pressKey, false);

                this.pressKeyVisible = true;
                this.hotkeyAlias = event;
            },

            pressKey(event) {
                let key = event;
                let hotkeyIndex = this.shortcuts.map(function(e){ return e.alias; }).indexOf(this.hotkeyAlias);

                window.removeEventListener("keydown", this.pressKey);

                this.pressKeyVisible = false;

                // check doubles and clear
                this.shortcuts.forEach(
                    (doubleKey, i) => {
                        if( doubleKey.key_code == key.keyCode && i != hotkeyIndex ) {
                            this.shortcuts[i].key_code = 0;
                            this.shortcuts[i].key = 'undefined';
                        }
                    }
                );

                // assigned new key
                this.shortcuts[hotkeyIndex].key_code = key.keyCode;
                this.shortcuts[hotkeyIndex].key = key.code;
            },
        },
        mounted() {
            this.$root.$on('show-user-settings', () => {
                this.visible = true;
                this.spellcheck = this.$store.getters.getProfileSpellcheck
                this.dark_theme = this.$store.getters.getProfileDarkTheme
                this.selected_word_lists = this.$store.getters.getProfileWordLists
                this.shortcuts = this.$store.getters.getProfileHotkeys
            });

            if (this.checkPermission(Permissions.ASSESS_ACCESS)) {
                this.$store.dispatch('getAllUserWordLists', {search: ''})
                    .then(() => {
                        this.word_lists = this.$store.getters.getWordLists.items
                    });
            }
        }
    }
</script>