<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" @click="addUser">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('user.add_btn')}}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('user.add_new') }}</span>
                        <span v-else>{{ $t('user.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('user.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="6" class="pa-1">
                            <v-text-field
                                :label="$t('user.username')"
                                name="username"
                                type="text"
                                v-model="user.username"
                                v-validate="'required'"
                                data-vv-name="username"
                                :error-messages="errors.collect('username')"
                            />
                        </v-col>
                        <v-col cols="6" class="pa-1">
                            <v-text-field
                                :label="$t('user.name')"
                                name="name"
                                v-model="user.name"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12" class="pa-1">
                            <v-data-table
                                v-model="selected_permissions"
                                :headers="headers"
                                :items="permissions"
                                item-key="id"
                                show-select
                                class="elevation-1"
                            >

                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('user.permissions')}}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{$t('user.validation_error')}}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{$t('user.error')}}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    import AuthMixin from "../../../services/auth/auth_mixin";
    import {createNewExternalUser} from "@/api/config";
    import {updateExternalUser} from "@/api/config";

    export default {
        name: "NewExternalUser",
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
            selected_permissions: [],
            permissions: [],
            user: {
                id: -1,
                username: "",
                name: "",
                roles: [],
                permissions: [],
                organizations: [],
            }
        }),
        methods: {
            addUser() {
                this.visible = true;
                this.edit = false
                this.show_error = false;
                this.user.username = "";
                this.user.name = ""
                this.user.roles = []
                this.user.organizations = []
                this.selected_permissions = []
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

                        this.user.permissions = [];
                        for (let i = 0; i < this.selected_permissions.length; i++) {
                            this.user.permissions.push(
                                {
                                    id: this.selected_permissions[i].id
                                }
                            )
                        }

                        if (this.edit) {

                            updateExternalUser(this.user).then(() => {

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

                            createNewExternalUser(this.user).then(() => {

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
            this.$store.dispatch('getAllExternalPermissions', {search: ''})
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