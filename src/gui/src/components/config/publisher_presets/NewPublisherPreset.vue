<template>
    <div>
        <v-btn v-if="canCreate" depressed small color="white--text ma-2 mt-3 mr-5" @click="addPreset">
            <v-icon left>mdi-plus-circle-outline</v-icon>
            <span class="subtitle-2">{{$t('publisher_preset.add_btn')}}</span>
        </v-btn>
        <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
            <v-card>

                <v-toolbar dark color="primary">
                    <v-btn icon dark @click="cancel">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>
                    <v-toolbar-title v-if="!edit">{{$t('publisher_preset.add_new')}}</v-toolbar-title>
                    <v-toolbar-title v-if="edit">{{$t('publisher_preset.edit')}}</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('publisher_preset.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-card-text>
                    <v-form @submit.prevent="add" id="form" ref="form">
                        <v-combobox :disabled="edit"
                                v-model="selected_node"
                                :items="nodes"
                                item-text="name"
                                :label="$t('publisher_preset.node')"
                        ></v-combobox>
                        <v-combobox v-if="selected_node" :disabled="edit"
                                    v-model="selected_publisher"
                                    :items="selected_node.publishers"
                                    item-text="name"
                                    :label="$t('publisher_preset.publisher')"
                        ></v-combobox>


                        <v-text-field v-if="selected_publisher" :disabled="!canUpdate"
                                      :label="$t('publisher_preset.name')"
                                      name="name"
                                      type="text"
                                      v-model="preset.name"
                                      v-validate="'required'"
                                      data-vv-name="name"
                                      :error-messages="errors.collect('name')"
                                      :spellcheck="$store.state.settings.spellcheck"
                        ></v-text-field>
                        <v-textarea v-if="selected_publisher" :disabled="!canUpdate"
                                    :label="$t('publisher_preset.description')"
                                    name="description"
                                    v-model="preset.description"
                                    :spellcheck="$store.state.settings.spellcheck"
                        ></v-textarea>

                        <v-checkbox v-if="selected_publisher" :disabled="!canUpdate"
                                    :label="$t('publisher_preset.use_for_notifications')"
                                    name="use_for_notifications"
                                    v-model="preset.use_for_notifications"
                                    :spellcheck="$store.state.settings.spellcheck"
                        ></v-checkbox>

                        <FormParameters v-if="selected_publisher" :disabled="!canUpdate"
                                        ui="text"
                                        :sources="selected_publisher.parameters"
                                        :values="values"
                        />

                    </v-form>
                    <v-alert v-if="show_validation_error" dense type="error" text>
                        {{$t('publisher_preset.validation_error')}}
                    </v-alert>
                    <v-alert v-if="show_error" dense type="error" text>
                        {{$t('publisher_preset.error')}}
                    </v-alert>
                </v-card-text>
            </v-card>
        </v-dialog>
    </div>
</template>

<script>
    import {createNewPublisherPreset} from "@/api/config";
    import {updatePublisherPreset} from "@/api/config";
    import FormParameters from "../../common/FormParameters";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewPublisherPreset",
        components: {
            FormParameters
        },
        data: () => ({
            visible: false,
            edit: false,
            show_validation_error: false,
            show_error: false,
            selected_node: null,
            selected_publisher: null,
            nodes: [],
            values: [],
            preset: {
                id: "",
                name: "",
                description: "",
                use_for_notifications: false,
                publisher_id: "",
                parameter_values: []
            }
        }),
        mixins: [AuthMixin],
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_PUBLISHER_PRESET_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_PUBLISHER_PRESET_UPDATE) || !this.edit
            },
        },

        methods: {
            addPreset() {
                this.visible = true
                this.edit = false
                this.show_error = false;
                this.selected_node = null
                this.selected_publisher = null
                this.preset.id = ""
                this.preset.name = ""
                this.preset.use_for_notifications = false
                this.preset.description = ""
                this.preset.publisher_id = ""
                this.values = []
                this.preset.parameter_values = []
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

                        this.preset.publisher_id = this.selected_publisher.id;

                        for (let i = 0; i < this.selected_publisher.parameters.length; i++) {
                            this.preset.parameter_values[i] = {
                                value: this.values[i],
                                parameter: this.selected_publisher.parameters[i]
                            }
                        }

                        if (this.edit) {
                            updatePublisherPreset(this.preset).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'publisher_preset.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {

                            createNewPublisherPreset(this.preset).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'publisher_preset.successful'
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
            this.$store.dispatch('getAllPublishersNodes', {search: ''})
                .then(() => {
                    this.nodes = this.$store.getters.getPublishersNodes.items
                });

            this.$root.$on('show-edit', (data) => {

                this.visible = true;
                this.edit = true
                this.show_error = false;

                this.preset.id = data.id
                this.preset.name = data.name
                this.preset.description = data.description
                this.preset.use_for_notifications = data.use_for_notifications
                this.preset.publisher_id = data.publisher_id

                this.preset.parameter_values = []
                for (let i = 0; i < data.parameter_values.length; i++) {
                    this.preset.parameter_values.push({
                        value: data.parameter_values[i].value,
                        parameter: data.parameter_values[i].parameter
                    })
                }

                let found = false
                for (let i = 0; i < this.nodes.length; i++) {
                    for (let j = 0; j < this.nodes[i].publishers.length; j++) {
                        if (this.nodes[i].publishers[j].id === this.preset.publisher_id) {
                            this.selected_node = this.nodes[i]
                            this.selected_publisher = this.nodes[i].publishers[j]
                            found = true
                            break;
                        }
                    }

                    if (found) {
                        break
                    }
                }

                this.values = []
                for (let i = 0; i < this.selected_publisher.parameters.length; i++) {
                    for (let j = 0; j < this.preset.parameter_values.length; j++) {
                        if (this.selected_publisher.parameters[i].id === this.preset.parameter_values[j].parameter.id) {
                            this.values.push(this.preset.parameter_values[j].value)
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
