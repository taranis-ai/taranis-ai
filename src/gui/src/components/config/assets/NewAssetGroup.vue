<template>
    <div>
        <v-btn depressed small color="white--text ma-2 mt-3 mr-5" @click="addGroup">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('asset_group.add')}}</span>
        </v-btn>
        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>

                    <v-toolbar dark color="primary">
                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('asset_group.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('asset_group.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn text type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('asset_group.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-card-text>
                        <v-form @submit.prevent="add" id="form" ref="form">


                            <v-text-field
                                    :label="$t('asset_group.name')"
                                    name="name"
                                    type="text"
                                    v-model="group.name"
                                    v-validate="'required'"
                                    data-vv-name="name"
                                    :error-messages="errors.collect('name')"
                                    :spellcheck="$store.state.settings.spellcheck"
                            ></v-text-field>
                            <v-textarea
                                    :label="$t('asset_group.description')"
                                    name="description"
                                    v-model="group.description"
                                    :spellcheck="$store.state.settings.spellcheck"
                            ></v-textarea>
                            <v-data-table
                                    v-model="selected_users"
                                    :headers="headers"
                                    :items="users"
                                    item-key="id"
                                    show-select
                                    class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('asset_group.allowed_users')}}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>

                            <v-spacer class="pt-4"></v-spacer>

                            <v-data-table
                                    v-model="selected_templates"
                                    :headers="headers_template"
                                    :items="templates"
                                    item-key="id"
                                    show-select
                                    class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('asset_group.notification_templates')}}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>

                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{$t('asset_group.validation_error')}}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>{{$t('asset_group.error')}}
                            </v-alert>
                        </v-form>
                    </v-card-text>

                </v-card>
            </v-dialog>
        </v-row>
    </div>
</template>

<script>
    import {createNewAssetGroup} from "@/api/assets";
    import {updateAssetGroup} from "@/api/assets";

    export default {
        name: "NewAssetGroup",
        data: () => ({
            visible: false,
            edit: false,
            headers: [
                {
                    text: 'Username',
                    align: 'start',
                    value: 'username',
                },
                {text: 'Name', value: 'name'},
            ],
            headers_template: [
                {
                    text: 'Name',
                    align: 'start',
                    value: 'name',
                },
                {text: 'Description', value: 'description'},
            ],
            selected_users: [],
            users: [],
            templates: [],
            selected_templates: [],
            show_validation_error: false,
            show_error: false,
            group: {
                id: "",
                name: "",
                description: "",
                users: [],
                templates: []
            }
        }),
        methods: {
            addGroup() {
                this.visible = true
                this.edit = false
                this.show_error = false;
                this.group.name = ""
                this.group.description = ""
                this.group.users = []
                this.group.templates = []
                this.selected_users = [];
                this.selected_templates = [];
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

                        this.group.users = [];
                        for (let i = 0; i < this.selected_users.length; i++) {
                            this.group.users.push(
                                {
                                    id: this.selected_users[i].id
                                }
                            )
                        }

                        this.group.templates = [];
                        for (let i = 0; i < this.selected_templates.length; i++) {
                            this.group.templates.push(
                                {
                                    id: this.selected_templates[i].id
                                }
                            )
                        }

                        if (this.edit) {
                            updateAssetGroup(this.group).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'asset_group.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewAssetGroup(this.group).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'asset_group.successful'
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
        mounted() {
            this.$store.dispatch('getAllExternalUsers', {search: ''})
                .then(() => {
                    this.users = this.$store.getters.getUsers.items
                });

            this.$store.dispatch('getAllNotificationTemplates', {search: ''})
                .then(() => {
                    this.templates = this.$store.getters.getNotificationTemplates.items
                });

            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;
                this.group.id = data.id;
                this.group.name = data.name;
                this.group.description = data.description;
                this.selected_users = data.users;
                this.selected_templates = data.templates;
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>
