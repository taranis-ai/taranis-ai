<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addRole">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('role.add_btn')}}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('role.add_new') }}</span>
                        <span v-else>{{ $t('role.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('role.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12" class="pa-1">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('role.title')"
                                          name="title"
                                          type="text"
                                          v-model="role.name"
                                          v-validate="'required'"
                                          data-vv-name="title"
                                          :error-messages="errors.collect('title')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12" class="pa-1">
                            <v-textarea :disabled="!canUpdate"
                                        :label="$t('role.description')"
                                        name="description"
                                        v-model="role.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12" class="pt-2">
                            <v-data-table :disabled="!canUpdate"
                                          v-model="selected_permissions"
                                          :headers="headers"
                                          :items="permissions"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          disable-pagination
                                          hide-default-footer
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('role.permissions')}}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{$t('role.validation_error')}}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{$t('role.error')}}
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
    import {createNewRole} from "@/api/config";
    import {updateRole} from "@/api/config";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewRole",
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
            role: {
                id: -1,
                name: "",
                description: "",
                permissions: [],
            }
        }),
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_ROLE_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_ROLE_UPDATE) || !this.edit
            },
        },
        methods: {
            addRole() {
                this.visible = true;
                this.edit = false;
                this.show_error = false;
                this.role.id = ""
                this.role.name = ""
                this.role.description = ""
                this.role.permissions = []
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

                        this.role.permissions = [];
                        for (let i = 0; i < this.selected_permissions.length; i++) {
                            this.role.permissions.push(
                                {
                                    id: this.selected_permissions[i].id
                                }
                            )
                        }

                        if (this.edit) {

                            updateRole(this.role).then(() => {

                                this.$validator.reset();
                                this.visible = false;


                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'role.successful_edit'
                                    }
                                )

                            }).catch(() => {

                                this.show_error = true;
                            })

                        } else {

                            createNewRole(this.role).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'role.successful'
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
            this.$store.dispatch('getAllPermissions', {search: ''})
                .then(() => {
                    this.permissions = this.$store.getters.getAllPermissions.items
                });

            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;

                this.selected_permissions = data.permissions;

                this.role.id = data.id;
                this.role.name = data.name;
                this.role.description = data.description;
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>