<template>
    <div>
        <v-btn v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addRemoteNode">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('remote_node.add')}}</span>
        </v-btn>

        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>

                    <v-toolbar dark color="primary" style="z-index: 10000">
                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('remote_node.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('remote_node.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn v-if="canUpdate" text dark type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('remote_node.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-card>
                            <v-card-text>

                                <v-text-field :disabled="!canUpdate"
                                              :label="$t('remote_node.name')"
                                              name="title"
                                              type="text"
                                              v-model="remote_node.name"
                                              v-validate="'required'"
                                              data-vv-name="name"
                                              :error-messages="errors.collect('name')"
                                              :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-textarea :disabled="!canUpdate"
                                            :label="$t('remote_node.description')"
                                            name="description"
                                            v-model="remote_node.description"
                                            :spellcheck="$store.state.settings.spellcheck"
                                ></v-textarea>
                                <v-text-field :disabled="!canUpdate"
                                              :label="$t('remote_node.remote_url')"
                                              name="access_key"
                                              type="text"
                                              v-model="remote_node.remote_url"
                                              :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-text-field :disabled="!canUpdate"
                                              :label="$t('remote_node.event_url')"
                                              name="access_key"
                                              type="text"
                                              v-model="remote_node.events_url"
                                              :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-text-field :disabled="!canUpdate"
                                              :label="$t('remote_node.access_key')"
                                              name="access_key"
                                              type="text"
                                              v-model="remote_node.access_key"
                                              :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-checkbox
                                        :disabled="!canUpdate"
                                        :label="$t('remote_node.enabled')"
                                        v-model="remote_node.enabled"
                                ></v-checkbox>

                                <v-checkbox
                                        :disabled="!canUpdate"
                                        :label="$t('remote_node.sync_news_items')"
                                        v-model="remote_node.sync_news_items"
                                ></v-checkbox>
                                <v-combobox :disabled="!canUpdate"
                                            v-model="selected_osint_source_group"
                                            :items="osint_source_groups"
                                            item-text="name"
                                            :label="$t('remote_node.osint_source_group')"
                                ></v-combobox>

                                <v-checkbox
                                        :disabled="!canUpdate"
                                        :label="$t('remote_node.sync_report_items')"
                                        v-model="remote_node.sync_report_items"
                                ></v-checkbox>

                                <v-btn v-if="canConnect" @click="connect">
                                    <v-icon left>mdi-lan-connect</v-icon>
                                    <span>{{$t('remote_node.connect')}}</span>
                                </v-btn>
                                <v-spacer class="mt-2"></v-spacer>
                                <v-alert v-if="show_connect_info" dense type="success" text>
                                    {{$t('remote_node.connect_info')}}
                                </v-alert>
                                <v-alert v-if="show_connect_error" dense type="error" text>
                                    {{$t('remote_node.connect_error')}}
                                </v-alert>

                            </v-card-text>
                        </v-card>

                    </v-form>

                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('remote_node.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>{{$t('remote_node.error')}}
                    </v-alert>
                </v-card>
            </v-dialog>
        </v-row>
    </div>

</template>

<style>
    .div-wrapper .theme--light.v-card {
        border-left: 5px solid rgb(255, 172, 33);
    }

    .tabs [role='tablist'] {
        background-color: #f5ebd5 !important;

    }

    .div-wrapper .v-card-title-dialog {
        background-color: rgba(207, 158, 37, 0.2);
        border-radius: 0;
        font-size: 1.2em;
        font-weight: bold;
        padding: 0;
        padding-left: 1em;
    }

    .tabs .v-window-item {
    }

    .icon-field-offset {
        margin-left: 8px;
    }
</style>

<script>
    import AuthMixin from "../../../services/auth/auth_mixin";
    import {createNewRemoteNode} from "@/api/config";
    import {updateRemoteNode} from "@/api/config";
    import {connectRemoteNode} from "@/api/config";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewRemoteNode",
        components: {},
        props: {add_button: Boolean},
        data: () => ({
            visible: false,
            show_validation_error: false,
            edit: false,
            show_error: false,
            osint_source_groups: [],
            selected_osint_source_group: null,
            connected: false,
            show_connect_error: false,
            show_connect_info: false,
            remote_node: {
                id: -1,
                name: "",
                description: "",
                remote_url: "",
                events_url: "",
                access_key: "",
                enabled: false,
                sync_news_items: false,
                sync_report_items: false,
                osint_source_group_id: null
            }
        }),
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_REMOTE_NODE_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_REMOTE_NODE_UPDATE) || !this.edit
            },
            canConnect() {
                return ((this.checkPermission(Permissions.CONFIG_REMOTE_NODE_UPDATE) || !this.edit) && this.connected === false)
                    && this.remote_node.enabled === true
            },
        },
        methods: {
            addRemoteNode() {
                this.visible = true;
                this.edit = false;
                this.show_error = false;
                this.connected = false
                this.show_connect_error = false
                this.show_connect_info = false
                this.remote_node.id = -1
                this.remote_node.name = ""
                this.remote_node.description = ""
                this.remote_node.remote_url = ""
                this.remote_node.events_url = ""
                this.remote_node.enabled = false
                this.remote_node.sync_news_items = false
                this.remote_node.sync_report_items = false
                this.remote_node.osint_source_group_id = null
                this.selected_osint_source_group = null
                this.$validator.reset();
            },

            cancel() {
                this.$validator.reset();
                this.visible = false
                this.$root.$emit('update-data')
            },

            connect() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.show_validation_error = false;
                        this.show_error = false;

                        if (this.selected_osint_source_group !== null) {
                            this.remote_node.osint_source_group_id = this.selected_osint_source_group.id
                        }

                        if (this.edit) {
                            updateRemoteNode(this.remote_node).then(() => {

                                this.$validator.reset();
                                this.makeConnection();

                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewRemoteNode(this.remote_node).then(() => {

                                this.$validator.reset();
                                this.makeConnection();

                            }).catch(() => {

                                this.show_error = true;
                            })
                        }

                    } else {

                        this.show_validation_error = true;
                    }
                })
            },

            makeConnection() {
                connectRemoteNode(this.remote_node).then(() => {
                    this.show_connect_info = true
                    this.show_connect_error = false
                    this.connected = true
                }).catch(() => {
                    this.show_connect_error = true
                    this.show_connect_info = false
                    this.connected = false
                })
            },

            add() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.show_validation_error = false;
                        this.show_error = false;

                        if (this.selected_osint_source_group !== null) {
                            this.remote_node.osint_source_group_id = this.selected_osint_source_group.id
                        }

                        if (this.edit) {
                            updateRemoteNode(this.remote_node).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'remote_node.successful_edit'
                                    }
                                )

                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewRemoteNode(this.remote_node).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'remote_node.successful'
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
            this.$store.dispatch('getAllOSINTSourceGroups', {search: ''})
                .then(() => {
                    this.osint_source_groups = this.$store.getters.getOSINTSourceGroups.items
                });

            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;
                this.connected = data.event_id !== null && data.enabled === true
                this.show_connect_error = false
                this.show_connect_info = false

                for (let i = 0; i < this.osint_source_groups.length; i++) {
                    if (this.osint_source_groups[i].id === data.osint_source_group_id) {
                        this.selected_osint_source_group = this.osint_source_groups[i]
                        break
                    }
                }

                this.remote_node.id = data.id;
                this.remote_node.name = data.name;
                this.remote_node.description = data.description;
                this.remote_node.remote_url = data.remote_url;
                this.remote_node.events_url = data.events_url;
                this.remote_node.access_key = data.access_key;
                this.remote_node.enabled = data.enabled;
                this.remote_node.sync_news_items = data.sync_news_items;
                this.remote_node.sync_report_items = data.sync_report_items;

                if (this.connected === true) {
                    this.connect()
                }
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>
