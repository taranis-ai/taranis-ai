<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addOrganization">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('organization.add_btn')}}</span>
        </v-btn>
        <v-dialog v-model="visible" persistent max-width="600" >
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>
                    <v-toolbar-title v-if="!edit">{{$t('organization.add_new')}}</v-toolbar-title>
                    <v-toolbar-title v-if="edit">{{$t('organization.edit')}}</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('organization.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-card-text>
                    <v-form @submit.prevent="add" id="form" ref="form">

                        <v-text-field :disabled="!canUpdate"
                                      :label="$t('organization.name')"
                                      name="name"
                                      type="text"
                                      v-model="organization.name"
                                      v-validate="'required'"
                                      data-vv-name="name"
                                      :error-messages="errors.collect('name')"
                                      :spellcheck="$store.state.settings.spellcheck"
                        ></v-text-field>
                        <v-text-field :disabled="!canUpdate"
                                    :label="$t('organization.description')"
                                    name="description"
                                    v-model="organization.description"
                                    :spellcheck="$store.state.settings.spellcheck"
                        ></v-text-field>
                        <v-text-field :disabled="!canUpdate"
                                :label="$t('organization.street')"
                                name="description"
                                v-model="organization.address.street"
                                :spellcheck="$store.state.settings.spellcheck"
                        ></v-text-field>
                        <v-text-field :disabled="!canUpdate"
                                :label="$t('organization.city')"
                                name="description"
                                v-model="organization.address.city"
                                :spellcheck="$store.state.settings.spellcheck"
                        ></v-text-field>
                        <v-text-field :disabled="!canUpdate"
                                :label="$t('organization.zip')"
                                name="description"
                                v-model="organization.address.zip"
                        ></v-text-field>
                        <v-text-field :disabled="!canUpdate"
                                :label="$t('organization.country')"
                                name="description"
                                v-model="organization.address.country"
                                :spellcheck="$store.state.settings.spellcheck"
                        ></v-text-field>

                    </v-form>
                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('organization.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>
                        {{$t('organization.error')}}
                    </v-alert>
                </v-card-text>

            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    import {createNewOrganization} from "@/api/config";
    import {updateOrganization} from "@/api/config";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewOrganization",
        data: () => ({
            visible: false,
            edit: false,
            show_validation_error: false,
            show_error: false,
            organization: {
                id: -1,
                name: "",
                description: "",
                address: {
                    street: "",
                    city: "",
                    zip: "",
                    country: ""
                },
            }
        }),
        mixins: [AuthMixin],
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_ORGANIZATION_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_ORGANIZATION_UPDATE) || !this.edit
            },
        },

        methods: {
            addOrganization() {
                this.visible = true
                this.edit = false
                this.show_error = false;
                this.organization.id = -1
                this.organization.name = ""
                this.organization.description = ""
                this.organization.address.street = ""
                this.organization.address.city = ""
                this.organization.address.zip = ""
                this.organization.address.country = ""
                this.$validator.reset()
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

                        if (this.edit) {
                            updateOrganization(this.organization).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'organization.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewOrganization(this.organization).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'organization.successful'
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
            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;
                this.organization.id = data.id
                this.organization.name = data.name
                this.organization.description = data.description
                this.organization.address.street = data.address.street
                this.organization.address.city = data.address.city
                this.organization.address.zip = data.address.zip
                this.organization.address.country = data.address.country
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>