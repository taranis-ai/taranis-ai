<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addACL">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('acl.add_btn')}}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card>
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('acl.add_new') }}</span>
                        <span v-else>{{ $t('acl.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('acl.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12" class="pa-1">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('acl.name')"
                                          name="name"
                                          type="text"
                                          v-model="acl.name"
                                          v-validate="'required'"
                                          data-vv-name="name"
                                          :error-messages="errors.collect('name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12" class="pa-1">
                            <v-textarea :disabled="!canUpdate"
                                        :label="$t('acl.description')"
                                        name="description"
                                        v-model="acl.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="6" class="pa-1">
                            <v-combobox :disabled="!canUpdate"
                                        v-model="selected_type"
                                        :items="types"
                                        item-text="title"
                                        :label="$t('acl.item_type')"
                            />
                        </v-col>
                        <v-col cols="6" class="pa-1">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('acl.item_id')"
                                          name="item_id"
                                          type="text"
                                          v-model="acl.item_id"
                            />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12" class="d-flex">
                            <v-checkbox :disabled="!canUpdate" class="pr-8"
                                        :label="$t('acl.see')"
                                        name="see"
                                        v-model="acl.see"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                            <v-checkbox :disabled="!canUpdate" class="pr-8"
                                        :label="$t('acl.access')"
                                        name="access"
                                        v-model="acl.access"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                            <v-checkbox :disabled="!canUpdate" class="pr-8"
                                        :label="$t('acl.modify')"
                                        name="modify"
                                        v-model="acl.modify"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-checkbox :disabled="!canUpdate"
                                        :label="$t('acl.everyone')"
                                        name="everyone"
                                        v-model="acl.everyone"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-data-table :disabled="!canUpdate"
                                          v-model="selected_users"
                                          :headers="headers_user"
                                          :items="users"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('acl.users')}}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                        <v-col cols="12" class="pt-2">
                            <v-data-table :disabled="!canUpdate"
                                          v-model="selected_roles"
                                          :headers="headers_role"
                                          :items="roles"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('acl.roles')}}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{$t('acl.validation_error')}}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{$t('acl.error')}}
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
    import {createNewACLEntry} from "@/api/config";
    import {updateACLEntry} from "@/api/config";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewACL",
        components: {},
        props: {add_button: Boolean},
        data: () => ({

            headers_user: [
                {
                    text: 'Username',
                    align: 'start',
                    value: 'username',
                },
                {text: 'Name', value: 'name'},
            ],

            headers_role: [
                {
                    text: 'Name',
                    align: 'start',
                    value: 'name',
                },
                {text: 'Description', value: 'description'},
            ],

            types: [
                {id: "COLLECTOR", title: "Collector"},
                {id: "DELEGATION", title: "Delegation"},
                {id: "OSINT_SOURCE", title: "OSINT Source"},
                {id: "OSINT_SOURCE_GROUP", title: "OSINT Source Group"},
                {id: "PRODUCT_TYPE", title: "Product Type"},
                {id: "REPORT_ITEM", title: "Report Item"},
                {id: "REPORT_ITEM_TYPE", title: "Report Item Type"},
                {id: "WORD_LIST", title: "Word List"},
            ],
            selected_type: null,

            visible: false,
            show_validation_error: false,
            edit: false,
            show_error: false,
            selected_users: [],
            users: [],
            selected_roles: [],
            roles: [],
            acl: {
                id: -1,
                name: "",
                description: "",
                users: [],
                roles: [],
            }
        }),
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_ACL_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_ACL_UPDATE) || !this.edit
            },
        },
        methods: {
            addACL() {
                this.visible = true;
                this.edit = false;
                this.show_error = false;
                this.selected_type = null
                this.acl.id = -1
                this.acl.name = ""
                this.acl.description = ""
                this.acl.item_type = "";
                this.acl.item_id = "";
                this.acl.everyone = false;
                this.acl.see = false;
                this.acl.access = false;
                this.acl.modify = false;
                this.acl.users = []
                this.acl.roles = []
                this.selected_users = []
                this.selected_roles = []
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

                        if (this.selected_type !== null) {
                            this.acl.item_type = this.selected_type.id;
                        }

                        this.acl.users = [];
                        for (let i = 0; i < this.selected_users.length; i++) {
                            this.acl.users.push(
                                {
                                    id: this.selected_users[i].id
                                }
                            )
                        }

                        this.acl.roles = [];
                        for (let i = 0; i < this.selected_roles.length; i++) {
                            this.acl.roles.push(
                                {
                                    id: this.selected_roles[i].id
                                }
                            )
                        }

                        if (this.edit) {

                            updateACLEntry(this.acl).then(() => {

                                this.$validator.reset();
                                this.visible = false;


                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'acl.successful_edit'
                                    }
                                )

                            }).catch(() => {

                                this.show_error = true;
                            })

                        } else {

                            createNewACLEntry(this.acl).then(() => {

                                this.$validator.reset();
                                this.visible = false;

                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'acl.successful'
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
            this.$store.dispatch('getAllUsers', {search: ''})
                .then(() => {
                    this.users = this.$store.getters.getUsers.items
                });

            this.$store.dispatch('getAllRoles', {search: ''})
                .then(() => {
                    this.roles = this.$store.getters.getRoles.items
                });

            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;

                this.selected_users = data.users;
                this.selected_roles = data.roles;

                this.acl.id = data.id;
                this.acl.name = data.name;
                this.acl.description = data.description;
                this.acl.item_type = data.item_type;
                this.acl.item_id = data.item_id;
                this.acl.everyone = data.everyone;
                this.acl.see = data.see;
                this.acl.access = data.access;
                this.acl.modify = data.modify;

                for (let i = 0; i < this.types.length; i++) {
                    if (this.types[i].id === data.item_type) {
                        this.selected_type = this.types[i]
                    }
                }
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>