<template>
    <div>
        <v-btn v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addUser">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('user.add_btn')}}</span>
        </v-btn>

        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>

                    <v-toolbar dark color="primary" style="z-index: 10000">
                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('user.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('user.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn v-if="canUpdate" text dark type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('user.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-card>
                            <v-card-text>
                                <v-row>
                                    <v-col>
                                        <v-text-field :disabled="!canUpdate"
                                                :label="$t('user.username')"
                                                name="username"
                                                type="text"
                                                v-model="user.username"
                                                v-validate="'required'"
                                                data-vv-name="username"
                                                :error-messages="errors.collect('username')"
                                        ></v-text-field>
                                    </v-col>
                                    <v-col>
                                        <v-text-field :disabled="!canUpdate"
                                                :label="$t('user.name')"
                                                name="name"
                                                v-model="user.name"
                                        ></v-text-field>
                                    </v-col>
                                </v-row>

                                <v-data-table :disabled="!canUpdate"
                                        v-model="selected_organizations"
                                        :headers="headers"
                                        :items="organizations"
                                        item-key="id"
                                        :show-select="canUpdate"
                                        class="elevation-1"
                                >

                                    <template v-slot:top>
                                        <v-toolbar flat color="white">
                                            <v-toolbar-title>{{$t('user.organizations')}}</v-toolbar-title>
                                        </v-toolbar>
                                    </template>

                                </v-data-table>

                                <v-spacer class="mt-8"/>

                                <v-data-table :disabled="!canUpdate"
                                        v-model="selected_roles"
                                        :headers="headers"
                                        :items="roles"
                                        item-key="id"
                                        :show-select="canUpdate"
                                        class="elevation-1"
                                >

                                    <template v-slot:top>
                                        <v-toolbar flat color="white">
                                            <v-toolbar-title>{{$t('user.roles')}}</v-toolbar-title>
                                        </v-toolbar>
                                    </template>

                                </v-data-table>

                                <v-data-table :disabled="!canUpdate"
                                        v-model="selected_permissions"
                                        :headers="headers"
                                        :items="permissions"
                                        item-key="id"
                                        :show-select="canUpdate"
                                        class="elevation-1"
                                >

                                    <template v-slot:top>
                                        <v-toolbar flat color="white">
                                            <v-toolbar-title>{{$t('user.permissions')}}</v-toolbar-title>
                                        </v-toolbar>
                                    </template>

                                </v-data-table>

                            </v-card-text>
                        </v-card>

                    </v-form>

                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('user.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>{{$t('user.error')}}
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
    import {createNewUser} from "@/api/config";
    import {updateUser} from "@/api/config";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewUser",
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
            selected_roles: [],
            selected_permissions: [],
            selected_organizations: [],
            roles: [],
            permissions: [],
            organizations: [],
            user: {
                id: -1,
                username: "",
                name: "",
                roles: [],
                permissions: [],
                organizations: [],
            }
        }),
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_USER_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_USER_UPDATE) || !this.edit
            },
        },
        methods: {
            addUser() {
                this.visible = true;
                this.edit = false
                this.show_error = false;
                this.user.username = "";
                this.user.name = ""
                this.user.roles = []
                this.user.organizations = []
                this.selected_roles = []
                this.selected_permissions = []
                this.selected_organizations = []
                this.$validator.reset();
            },

            cancel() {
                this.$validator.reset();
                this.visible = false;
            },

            add() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.show_validation_error = false;
                        this.show_error = false;

                        this.user.organizations = [];
                        for (let i = 0; i < this.selected_organizations.length; i++) {
                            this.user.organizations.push(
                                {
                                    id: this.selected_organizations[i].id
                                }
                            )
                        }

                        this.user.roles = [];
                        for (let i = 0; i < this.selected_roles.length; i++) {
                            this.user.roles.push(
                                {
                                    id: this.selected_roles[i].id
                                }
                            )
                        }

                        this.user.permissions = [];
                        for (let i = 0; i < this.selected_permissions.length; i++) {
                            this.user.permissions.push(
                                {
                                    id: this.selected_permissions[i].id
                                }
                            )
                        }

                        if (this.edit) {

                            updateUser(this.user).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'user.successful_edit'
                                    }
                                )

                            }).catch(() => {

                                this.show_error = true;
                            })

                        } else {

                            createNewUser(this.user).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'user.successful'
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
            this.$store.dispatch('getAllOrganizations', {search: ''})
                .then(() => {
                    this.organizations = this.$store.getters.getOrganizations.items
                });

            this.$store.dispatch('getAllRoles', {search: ''})
                .then(() => {
                    this.roles = this.$store.getters.getRoles.items
                });

            this.$store.dispatch('getAllPermissions', {search: ''})
                .then(() => {
                    this.permissions = this.$store.getters.getAllPermissions.items
                });

            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;

                this.selected_roles = data.roles;
                this.selected_permissions = data.permissions;
                this.selected_organizations = data.organizations;

                this.user.id = data.id;
                this.user.username = data.username;
                this.user.name = data.name;
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>
