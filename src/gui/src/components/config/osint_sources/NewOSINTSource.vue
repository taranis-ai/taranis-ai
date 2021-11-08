<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addSource">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('osint_source.add_btn') }}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('osint_source.add_new') }}</span>
                        <span v-else>{{ $t('osint_source.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text type="submit" form="form_osint_source">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('osint_source.save') }}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form_osint_source" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12" class="caption grey--text" v-if="edit">ID: {{ source.id }}</v-col>
                        <v-col cols="12">
                            <v-combobox :disabled="edit"
                                        v-model="selected_node"
                                        :items="nodes"
                                        item-text="name"
                                        :label="$t('osint_source.node')"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-combobox v-if="selected_node" :disabled="edit"
                                        v-model="selected_collector"
                                        :items="selected_node.collectors"
                                        item-text="name_with_id"
                                        :label="$t('osint_source.collector')"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-text-field v-if="selected_collector" :disabled="!canUpdate"
                                          :label="$t('osint_source.name')"
                                          name="name"
                                          type="text"
                                          v-model="source.name"
                                          v-validate="'required'"
                                          data-vv-name="name"
                                          :error-messages="errors.collect('name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-textarea v-if="selected_collector" :disabled="!canUpdate"
                                        :label="$t('osint_source.description')"
                                        name="description"
                                        v-model="source.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <FormParameters v-if="selected_collector" :disabled="!canUpdate"
                                            ui="text"
                                            :sources="selected_collector.parameters"
                                            :values="values"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-data-table v-if="selected_collector" :disabled="!canUpdate"
                                          v-model="selected_osint_source_groups"
                                          :headers="headers_groups"
                                          :items="getOSINTSourceGroups"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          @item-selected="itemSelected"
                                          @toggle-select-all="selectAll"
                                          class="elevation-1"
                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>
                                            {{ $t('osint_source.osint_source_groups') }}
                                        </v-toolbar-title>
                                        <v-spacer/>
                                        <AddGroup></AddGroup>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                        <v-col cols="12" class="pt-2">
                            <v-data-table v-if="selected_collector" :disabled="!canUpdate"
                                          v-model="selected_word_lists"
                                          :headers="headers"
                                          :items="word_lists"
                                          item-key="id"
                                          :show-select="canUpdate"
                                          class="elevation-1"
                            >

                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{ $t('osint_source.word_lists') }}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{ $t('osint_source.validation_error') }}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{ $t('osint_source.error') }}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
import {createNewOSINTSource, updateOSINTSource} from "@/api/config";
import FormParameters from "../../common/FormParameters";
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";
import AddGroup from "@/components/config/osint_sources/NewOSINTSourceGroup";

export default {
    name: "NewOSINTSource",
    components: {
        FormParameters,
        AddGroup
    },
    data: () => ({
        headers_groups: [
            {
                text: 'Name',
                align: 'start',
                value: 'name',
            },
            {text: 'Description', value: 'description'},
        ],
        selected_osint_source_groups: [],
        osint_source_groups: [],
        headers: [
            {
                text: 'Name',
                align: 'start',
                value: 'name',
            },
            {text: 'Description', value: 'description'},
        ],
        visible: false,
        edit: false,
        show_validation_error: false,
        show_error: false,
        selected_node: null,
        selected_collector: null,
        nodes: [],
        values: [],
        word_lists: [],
        selected_word_lists: [],
        source: {
            id: "",
            name: "",
            description: "",
            collector_id: "",
            parameter_values: [],
            word_lists: []
        }
    }),
    mixins: [AuthMixin],
    computed: {
        canCreate() {
            return this.checkPermission(Permissions.CONFIG_OSINT_SOURCE_CREATE)
        },
        canUpdate() {
            return this.checkPermission(Permissions.CONFIG_OSINT_SOURCE_UPDATE) || !this.edit
        },
        getOSINTSourceGroups() {
            if (this.canUpdate) {
                return this.osint_source_groups
            } else {
                return this.selected_osint_source_groups
            }
        }
    },
    methods: {
        addSource() {
            this.visible = true
            this.edit = false
            this.show_error = false;
            this.selected_node = null
            this.selected_collector = null
            this.source.id = ""
            this.source.name = ""
            this.source.description = ""
            this.source.collector_id = ""
            this.values = []
            this.source.parameter_values = []
            this.source.word_list = []
            this.selected_word_lists = []
            this.selected_osint_source_groups = []
            for (let i = 0; i < this.osint_source_groups.length; i++) {
                this.osint_source_groups[i].isSelectable = true
            }
            this.$validator.reset();
        },

        cancel() {
            this.$validator.reset();
            this.visible = false
        },

        selectAll(data) {
            for (let i = 0; i < this.osint_source_groups.length; i++) {
                this.osint_source_groups[i].isSelectable = true
            }
            if (data.value === false) {
                this.osint_source_groups[0].isSelectable = false
                this.selected_osint_source_groups = [this.osint_source_groups[0]]
            }
        },

        itemSelected(data) {
            if (data.value === true && this.selected_osint_source_groups.length === 1) {
                for (let i = 0; i < this.osint_source_groups.length; i++) {
                    if (this.selected_osint_source_groups[0].id === this.osint_source_groups[i].id) {
                        this.osint_source_groups[i].isSelectable = true
                        break;
                    }
                }
            } else if (data.value === false && this.selected_osint_source_groups.length === 2) {
                for (let i = 0; i < this.osint_source_groups.length; i++) {
                    for (let j = 0; j < this.selected_osint_source_groups.length; j++) {
                        if (this.selected_osint_source_groups[j].id === this.osint_source_groups[i].id &&
                            this.selected_osint_source_groups[j].id !== data.item.id) {
                            this.osint_source_groups[i].isSelectable = false
                            return;
                        }
                    }
                }
            }
        },

        add() {
            this.$validator.validateAll().then(() => {

                if (!this.$validator.errors.any()) {

                    this.show_validation_error = false;
                    this.show_error = false;

                    this.source.collector_id = this.selected_collector.id;

                    this.source.parameter_values = [];
                    for (let i = 0; i < this.selected_collector.parameters.length; i++) {
                        this.source.parameter_values[i] = {
                            value: this.values[i],
                            parameter: this.selected_collector.parameters[i]
                        }
                    }

                    this.source.osint_source_groups = [];
                    for (let i = 0; i < this.selected_osint_source_groups.length; i++) {
                        this.source.osint_source_groups.push(
                            {
                                id: this.selected_osint_source_groups[i].id
                            }
                        )
                    }

                    this.source.word_lists = [];
                    for (let i = 0; i < this.selected_word_lists.length; i++) {
                        this.source.word_lists.push(
                            {
                                id: this.selected_word_lists[i].id
                            }
                        )
                    }

                    if (this.edit) {
                        updateOSINTSource(this.source).then(() => {

                            this.$validator.reset();
                            this.visible = false;
                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'osint_source.successful_edit'
                                }
                            )
                        }).catch(() => {

                            this.show_error = true;
                        })
                    } else {
                        createNewOSINTSource(this.source).then(() => {

                            this.$validator.reset();
                            this.visible = false;
                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'osint_source.successful'
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
        },

        loadAllOSINTSourceGroups() {
            this.$store.dispatch('getAllOSINTSourceGroups', {search: ''})
                .then(() => {
                    this.osint_source_groups = []
                    for (let i = 0; i < this.$store.getters.getOSINTSourceGroups.items.length; i++) {
                        let item = this.$store.getters.getOSINTSourceGroups.items[i]
                        if (item.default !== true) {
                            this.osint_source_groups.push(item)
                        }
                    }
                });
        }
    },
    mounted() {
        this.$store.dispatch('getAllCollectorsNodes', {search: ''})
            .then(() => {
                this.nodes = this.$store.getters.getCollectorsNodes.items
                for (let i = 0; i < this.nodes.length; i++) {
                    for (let j = 0; j < this.nodes[i].collectors.length; j++) {
                        this.nodes[i].collectors[j].name_with_id = this.nodes[i].collectors[j].name + " (ID: " + this.nodes[i].collectors[j].id + ")"
                    }
                }
            });

        this.$store.dispatch('getAllWordLists', {search: ''})
            .then(() => {
                this.word_lists = this.$store.getters.getWordLists.items
            });

        this.loadAllOSINTSourceGroups()
        this.$root.$on('osint-source-group-added', () => {
            this.loadAllOSINTSourceGroups()
        });

        this.$root.$on('show-edit', (data) => {

            this.visible = true;
            this.edit = true
            this.show_error = false;

            this.source.id = data.id
            this.source.name = data.name
            this.source.description = data.description
            this.selected_word_lists = data.word_lists
            this.selected_osint_source_groups = data.osint_source_groups
            this.source.word_lists = []
            this.source.collector_id = data.collector_id

            this.source.parameter_values = []
            for (let i = 0; i < data.parameter_values.length; i++) {
                this.source.parameter_values.push({
                    value: data.parameter_values[i].value,
                    parameter: data.parameter_values[i].parameter
                })
            }

            let found = false
            for (let i = 0; i < this.nodes.length; i++) {
                for (let j = 0; j < this.nodes[i].collectors.length; j++) {
                    if (this.nodes[i].collectors[j].id === this.source.collector_id) {
                        this.selected_node = this.nodes[i]
                        this.selected_collector = this.nodes[i].collectors[j]
                        found = true
                        break;
                    }
                }

                if (found) {
                    break
                }
            }

            this.values = []
            for (let i = 0; i < this.selected_collector.parameters.length; i++) {
                for (let j = 0; j < this.source.parameter_values.length; j++) {
                    if (this.selected_collector.parameters[i].id === this.source.parameter_values[j].parameter.id) {
                        this.values.push(this.source.parameter_values[j].value)
                        break
                    }
                }
            }

            if (this.selected_osint_source_groups.length === 1) {
                for (let i = 0; i < this.osint_source_groups.length; i++) {
                    if (this.selected_osint_source_groups[0].id === this.osint_source_groups[i].id) {
                        this.osint_source_groups[i].isSelectable = false
                        break;
                    }
                }
            }
        });
    },
    beforeDestroy() {
        this.$root.$off('osint-source-group-added')
        this.$root.$off('show-edit')
    }
}
</script>