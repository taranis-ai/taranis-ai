<template>
    <div>
        <v-btn  v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addGroup">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('osint_source_group.add')}}</span>
        </v-btn>

        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>

                    <v-toolbar dark color="primary" style="z-index: 10000">
                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('osint_source_group.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('osint_source_group.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn v-if="canUpdate" text dark type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('osint_source_group.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-card>
                            <v-card-text>

                                <span v-if="edit">ID: {{group.id}}</span>

                                <v-text-field :disabled="!canUpdate"
                                        :label="$t('osint_source_group.title')"
                                        name="title"
                                        type="text"
                                        v-model="group.name"
                                        v-validate="'required'"
                                        data-vv-name="title"
                                        :error-messages="errors.collect('title')"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-textarea :disabled="!canUpdate"
                                        :label="$t('osint_source_group.description')"
                                        name="description"
                                        v-model="group.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-textarea>
                                <v-data-table :disabled="!canUpdate"
                                        v-model="selected_osint_sources"
                                        :headers="headers"
                                        :items="osint_sources"
                                        item-key="id"
                                        :show-select="canUpdate"
                                        class="elevation-1"
                                >
                                    <template v-slot:top>
                                        <v-toolbar flat color="white">
                                            <v-toolbar-title>{{$t('osint_source_group.osint_sources')}}
                                            </v-toolbar-title>
                                        </v-toolbar>
                                    </template>

                                </v-data-table>

                            </v-card-text>
                        </v-card>

                    </v-form>

                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('osint_source_group.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>{{$t('osint_source_group.error')}}
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
    import {createNewOSINTSourceGroup} from "@/api/config";
    import {updateOSINTSourceGroup} from "@/api/config";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewOSINTSourceGroup",
        components: {},
        props: {add_button: Boolean},
        data: () => ({

            headers: [
                {
                    text: 'Name',
                    align: 'start',
                    value: 'name',
                },
                {text: 'Description', value: 'description'},
            ],

            visible: false,
            show_validation_error: false,
            edit: false,
            show_error: false,
            selected_osint_sources: [],
            osint_sources: [],
            group: {
                id: "",
                name: "",
                description: "",
                osint_sources: [],
            }
        }),
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_OSINT_SOURCE_GROUP_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_OSINT_SOURCE_GROUP_UPDATE) || !this.edit
            },
        },
        methods: {
            addGroup() {
                this.visible = true;
                this.edit = false;
                this.show_error = false;
                this.group.name = ""
                this.group.description = ""
                this.group.osint_sources = []
                this.selected_osint_sources = []
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

                        this.group.osint_sources = [];
                        for (let i = 0; i < this.selected_osint_sources.length; i++) {
                            this.group.osint_sources.push(
                                {
                                    id: this.selected_osint_sources[i].id
                                }
                            )
                        }

                        if (this.edit) {
                            updateOSINTSourceGroup(this.group).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'osint_source_group.successful_edit'
                                    }
                                )

                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewOSINTSourceGroup(this.group).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'osint_source_group.successful'
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
            this.$store.dispatch('getAllOSINTSources', {search:''})
                .then(() => {
                    this.osint_sources = this.$store.getters.getOSINTSources.items
                });

            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;

                this.selected_osint_sources = data.osint_sources;

                this.group.id = data.id;
                this.group.name = data.name;
                this.group.description = data.description;
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>
