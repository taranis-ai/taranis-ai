<template>
    <div>
        <v-btn  v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addSource">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('osint_source.add_btn')}}</span>
        </v-btn>
        <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
            <v-card>

                <v-toolbar dark color="primary">
                    <v-btn icon dark @click="cancel">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title v-if="!edit">{{$t('osint_source.add_new')}}</v-toolbar-title>
                    <v-toolbar-title v-if="edit">{{$t('osint_source.edit')}}</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('osint_source.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form">
                    <v-card>
                        <v-card-text>
                            <span v-if="edit">ID: {{source.id}}</span>

                            <v-combobox :disabled="edit"
                                        v-model="selected_node"
                                        :items="nodes"
                                        item-text="name"
                                        :label="$t('osint_source.node')"
                            ></v-combobox>
                            <v-combobox v-if="selected_node" :disabled="edit"
                                        v-model="selected_collector"
                                        :items="selected_node.collectors"
                                        item-text="name_with_id"
                                        :label="$t('osint_source.collector')"
                            ></v-combobox>

                            <v-text-field v-if="selected_collector" :disabled="!canUpdate"
                                          :label="$t('osint_source.name')"
                                          name="name"
                                          type="text"
                                          v-model="source.name"
                                          v-validate="'required'"
                                          data-vv-name="name"
                                          :error-messages="errors.collect('name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            ></v-text-field>
                            <v-textarea v-if="selected_collector" :disabled="!canUpdate"
                                        :label="$t('osint_source.description')"
                                        name="description"
                                        v-model="source.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            ></v-textarea>

                            <FormParameters v-if="selected_collector" :disabled="!canUpdate"
                                            ui="text"
                                            :sources="selected_collector.parameters"
                                            :values="values"
                            />

                            <v-spacer class="mt-8"/>

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
                                        <v-toolbar-title>{{$t('osint_source.word_lists')}}</v-toolbar-title>
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-card-text>
                    </v-card>
                </v-form>
                <v-alert v-if="show_validation_error" dense type="error" text>
                    {{$t('osint_source.validation_error')}}
                </v-alert>
                <v-alert v-if="show_error" dense type="error" text>
                    {{$t('osint_source.error')}}
                </v-alert>

            </v-card>
        </v-dialog>
    </div>
</template>

<script>
    import {createNewOSINTSource} from "@/api/config";
    import {updateOSINTSource} from "@/api/config";
    import FormParameters from "../../common/FormParameters";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewOSINTSource",
        components: {
            FormParameters
        },
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

                        this.source.collector_id = this.selected_collector.id;

                        this.source.parameter_values = [];
                        for (let i = 0; i < this.selected_collector.parameters.length; i++) {
                            this.source.parameter_values[i] = {
                                value: this.values[i],
                                parameter: this.selected_collector.parameters[i]
                            }
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

            this.$root.$on('show-edit', (data) => {

                this.visible = true;
                this.edit = true
                this.show_error = false;

                this.source.id = data.id
                this.source.name = data.name
                this.source.description = data.description
                this.selected_word_lists = data.word_lists
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
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>
