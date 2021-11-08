<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addGroup">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('osint_source_group.add') }}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('osint_source_group.add_new') }}</span>
                        <span v-else>{{ $t('osint_source_group.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text dark type="submit" form="form_osint_group">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('osint_source_group.save') }}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form_osint_group" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12" class="caption grey--text" v-if="edit">ID: {{ group.id }}</v-col>
                        <v-col cols="12">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('osint_source_group.title')"
                                          name="title"
                                          type="text"
                                          v-model="group.name"
                                          v-validate="'required'"
                                          data-vv-name="title"
                                          :error-messages="errors.collect('title')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-textarea :disabled="!canUpdate"
                                        :label="$t('osint_source_group.description')"
                                        name="description"
                                        v-model="group.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-data-table :disabled="!canUpdate"
                                          v-model="selected_osint_sources"
                                          :headers="headers"
                                          :items="getOSINTSources"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{ $t('osint_source_group.osint_sources') }}
                                        </v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{ $t('osint_source_group.validation_error') }}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{ $t('osint_source_group.error') }}
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
import {createNewOSINTSourceGroup, updateOSINTSourceGroup} from "@/api/config";
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
            default: false,
            description: "",
            osint_sources: [],
        }
    }),
    computed: {
        canCreate() {
            return this.checkPermission(Permissions.CONFIG_OSINT_SOURCE_GROUP_CREATE)
        },
        canUpdate() {
            return !this.group.default && (this.checkPermission(Permissions.CONFIG_OSINT_SOURCE_GROUP_UPDATE) || !this.edit)
        },
        getOSINTSources() {
            if (this.canUpdate) {
                return this.osint_sources
            } else {
                return this.selected_osint_sources
            }
        }
    },
    methods: {
        addGroup() {
            this.visible = true;
            this.edit = false;
            this.show_error = false;
            this.group.name = ""
            this.group.description = ""
            this.group.default = false
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

                            this.$root.$emit('osint-source-group-added')

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
        this.$store.dispatch('getAllOSINTSources', {search: ''})
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
            this.group.default = data.default
        });
    },
    beforeDestroy() {
        this.$root.$off('show-edit')
    }
}
</script>