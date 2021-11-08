<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addUser">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('user.add_btn') }}</span>
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
                    <v-btn v-if="canUpdate" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('user.save') }}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="6" class="pa-1">
                            <v-text-field :disabled="!canUpdate"
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
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('user.name')"
                                          name="name"
                                          v-model="user.name"
                            />
                        </v-col>
                        <v-col cols="6" class="pa-1">
                            <v-text-field
                                ref="password"
                                type="password"
                                v-model="pwd"
                                v-validate=" checkPassEdit ? 'required' : '' "
                                :error-messages="errors.collect('password_check')"
                                :label="$t('user.password')"
                                data-vv-name="password_check"
                            />
                        </v-col>
                        <v-col cols="6" class="pa-1">
                            <v-text-field
                                v-model="repwd"
                                type="password"
                                v-validate=" checkPassEdit ? 'required|confirmed:password' : '' "
                                :error-messages="errors.collect('password_check')"
                                :label="$t('user.password_check')"
                                data-vv-name="password_check"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
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
                                        <v-toolbar-title>{{ $t('user.organizations') }}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                        <v-col cols="12" class="pt-2">
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
                                        <v-toolbar-title>{{ $t('user.roles') }}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                        <v-col cols="12" class="pt-2">
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
                                        <v-toolbar-title>{{ $t('user.permissions') }}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col>
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{ $t('user.validation_error') }}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{ $t('user.error') }}
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
import {createNewUser, updateUser} from "@/api/config";
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
        pwd: "",
        repwd: "",
        pwdvld: true,
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
        checkPassEdit() {
            if (this.edit) {
                return this.pwd !== "" || this.repwd !== "";

            } else {
                return true;
            }
        },
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
            this.pwd = ""
            this.repwd = ""
            this.$validator.reset();
        },

        cancel() {
            this.$validator.reset();
            this.visible = false;
            this.pwd = "";
            this.repwd = "";
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

                    if (this.edit === false || this.pwd !== "") {
                        this.user.password = this.pwd
                    }
                    this.pwd = "";
                    this.repwd = "";

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

            this.pwd = "";
            this.repwd = "";

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