<template>
    <div>
        <v-btn v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addACL">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('acl.add_btn')}}</span>
        </v-btn>

        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>

                    <v-toolbar dark color="primary" style="z-index: 10000">
                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title v-if="!edit">{{$t('acl.add_new')}}</v-toolbar-title>
                        <v-toolbar-title v-if="edit">{{$t('acl.edit')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn v-if="canUpdate" text dark type="submit" form="form">
                            <v-icon left>mdi-content-save</v-icon>
                            <span>{{$t('acl.save')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-card>
                            <v-card-text>
                                <v-text-field :disabled="!canUpdate"
                                        :label="$t('acl.name')"
                                        name="name"
                                        type="text"
                                        v-model="acl.name"
                                        v-validate="'required'"
                                        data-vv-name="name"
                                        :error-messages="errors.collect('name')"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-text-field>
                                <v-textarea :disabled="!canUpdate"
                                        :label="$t('acl.description')"
                                        name="description"
                                        v-model="acl.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-textarea>

                                <v-row>
                                    <v-col>
                                        <v-combobox :disabled="!canUpdate"
                                                v-model="selected_type"
                                                :items="types"
                                                item-text="title"
                                                :label="$t('acl.item_type')"
                                        />
                                    </v-col>
                                    <v-col>
                                        <v-text-field :disabled="!canUpdate"
                                                :label="$t('acl.item_id')"
                                                name="item_id"
                                                type="text"
                                                v-model="acl.item_id"
                                        ></v-text-field>
                                    </v-col>
                                </v-row>

                                <v-row>
                                    <v-checkbox :disabled="!canUpdate"
                                            :label="$t('acl.see')"
                                            style="margin-left:12px"
                                            name="see"
                                            v-model="acl.see"
                                            :spellcheck="$store.state.settings.spellcheck"
                                    ></v-checkbox>
                                    <v-checkbox :disabled="!canUpdate"
                                            :label="$t('acl.access')"
                                            style="margin-left:12px"
                                            name="access"
                                            v-model="acl.access"
                                            :spellcheck="$store.state.settings.spellcheck"
                                    ></v-checkbox>
                                    <v-checkbox :disabled="!canUpdate"
                                            :label="$t('acl.modify')"
                                            style="margin-left:12px"
                                            name="modify"
                                            v-model="acl.modify"
                                            :spellcheck="$store.state.settings.spellcheck"
                                    ></v-checkbox>
                                </v-row>

                                <v-checkbox :disabled="!canUpdate"
                                        :label="$t('acl.everyone')"
                                        name="everyone"
                                        v-model="acl.everyone"
                                        :spellcheck="$store.state.settings.spellcheck"
                                ></v-checkbox>
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

                                <v-spacer class="pt-4"></v-spacer>

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

                            </v-card-text>
                        </v-card>

                    </v-form>

                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('acl.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>{{$t('acl.error')}}
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
