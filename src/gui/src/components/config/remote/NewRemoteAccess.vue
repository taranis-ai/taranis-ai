<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addRemoteAccess">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('remote_access.add')}}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card>
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('remote_access.add_new') }}</span>
                        <span v-else>{{ $t('remote_access.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('remote_access.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('remote_access.name')"
                                          name="title"
                                          type="text"
                                          v-model="remote_access.name"
                                          v-validate="'required'"
                                          data-vv-name="name"
                                          :error-messages="errors.collect('name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-textarea :disabled="!canUpdate"
                                        :label="$t('remote_access.description')"
                                        name="description"
                                        v-model="remote_access.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('remote_access.access_key')"
                                          name="access_key"
                                          type="text"
                                          v-model="remote_access.access_key"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-checkbox
                                :disabled="!canUpdate"
                                :label="$t('remote_access.enabled')"
                                v-model="remote_access.enabled"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-data-table :disabled="!canUpdate"
                                          v-model="selected_osint_sources"
                                          :headers="headers_sources"
                                          :items="osint_sources"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('remote_access.osint_sources')}}
                                        </v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                        <v-col cols="12" class="pt-2">
                            <v-data-table :disabled="!canUpdate"
                                          v-model="selected_report_item_types"
                                          :headers="headers_types"
                                          :items="report_item_types"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('remote_access.report_item_types')}}
                                        </v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">

                        </v-col>
                    </v-row>
                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('remote_access.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>
                        {{$t('remote_access.error')}}
                    </v-alert>

                    <!--<v-card>
                        <v-card-text>

                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('remote_access.name')"
                                          name="title"
                                          type="text"
                                          v-model="remote_access.name"
                                          v-validate="'required'"
                                          data-vv-name="name"
                                          :error-messages="errors.collect('name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            ></v-text-field>
                            <v-textarea :disabled="!canUpdate"
                                        :label="$t('remote_access.description')"
                                        name="description"
                                        v-model="remote_access.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            ></v-textarea>
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('remote_access.access_key')"
                                          name="access_key"
                                          type="text"
                                          v-model="remote_access.access_key"
                                          :spellcheck="$store.state.settings.spellcheck"
                            ></v-text-field>
                            <v-checkbox
                                :disabled="!canUpdate"
                                :label="$t('remote_access.enabled')"
                                v-model="remote_access.enabled"
                            ></v-checkbox>
                            <v-data-table :disabled="!canUpdate"
                                          v-model="selected_osint_sources"
                                          :headers="headers_sources"
                                          :items="osint_sources"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('remote_access.osint_sources')}}
                                        </v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>

                            <v-data-table :disabled="!canUpdate"
                                          v-model="selected_report_item_types"
                                          :headers="headers_types"
                                          :items="report_item_types"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('remote_access.report_item_types')}}
                                        </v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>

                        </v-card-text>
                    </v-card>-->

                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    import AuthMixin from "../../../services/auth/auth_mixin";
    import {createNewRemoteAccess} from "@/api/config";
    import {updateRemoteAccess} from "@/api/config";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewRemoteAccess",
        components: {},
        props: {add_button: Boolean},
        data: () => ({

            headers_sources: [
                {
                    text: 'Name',
                    align: 'start',
                    value: 'name',
                },
                {text: 'Description', value: 'description'},
            ],

            headers_types: [
                {
                    text: 'Name',
                    align: 'start',
                    value: 'title',
                },
                {text: 'Description', value: 'description'},
            ],

            visible: false,
            show_validation_error: false,
            edit: false,
            show_error: false,
            selected_osint_sources: [],
            osint_sources: [],
            report_item_types: [],
            selected_report_item_types: [],
            remote_access: {
                id: -1,
                name: "",
                description: "",
                access_key: "",
                enabled: false,
                osint_sources: [],
                report_item_types: [],
            }
        }),
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_REMOTE_ACCESS_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_REMOTE_ACCESS_UPDATE) || !this.edit
            },
        },
        methods: {
            addRemoteAccess() {
                this.visible = true;
                this.edit = false;
                this.show_error = false;
                this.remote_access.id = -1
                this.remote_access.name = ""
                this.remote_access.description = ""
                this.remote_access.access_key = ""
                this.remote_access.enabled = false
                this.remote_access.osint_sources = []
                this.remote_access.report_item_types = []
                this.selected_osint_sources = []
                this.selected_report_item_types = []
                this.$validator.reset();
            },

            cancel() {
                this.$validator.reset();
                this.visible = false
            },

            add() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.show_validation_error = false;
                        this.show_error = false;

                        this.remote_access.osint_sources = [];
                        for (let i = 0; i < this.selected_osint_sources.length; i++) {
                            this.remote_access.osint_sources.push(
                                {
                                    id: this.selected_osint_sources[i].id
                                }
                            )
                        }

                        this.remote_access.report_item_types = [];
                        for (let i = 0; i < this.selected_report_item_types.length; i++) {
                            this.remote_access.report_item_types.push(
                                {
                                    id: this.selected_report_item_types[i].id
                                }
                            )
                        }

                        if (this.edit) {
                            updateRemoteAccess(this.remote_access).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'remote_access.successful_edit'
                                    }
                                )

                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewRemoteAccess(this.remote_access).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'remote_access.successful'
                                    }
                                )

                            }).catch(() => {

                                this.show_error = true;
                            })
                        }

                    } else {

                        this.show_validation_error = true;
                    }
                })
            }
        },
        mixins: [AuthMixin],
        mounted() {
            this.$store.dispatch('getAllOSINTSources', {search: ''})
                .then(() => {
                    this.osint_sources = this.$store.getters.getOSINTSources.items
                });

            this.$store.dispatch('getAllReportItemTypesConfig', {search: ''})
                .then(() => {
                    this.report_item_types = this.$store.getters.getReportItemTypesConfig.items
                });

            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;

                this.selected_osint_sources = data.osint_sources;
                this.selected_report_item_types = data.report_item_types;

                this.remote_access.id = data.id;
                this.remote_access.name = data.name;
                this.remote_access.description = data.description;
                this.remote_access.access_key = data.access_key;
                this.remote_access.enabled = data.enabled;
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>