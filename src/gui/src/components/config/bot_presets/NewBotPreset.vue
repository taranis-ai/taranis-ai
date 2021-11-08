<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addPreset">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('bot_preset.add_btn')}}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('bot_preset.add_new') }}</span>
                        <span v-else>{{ $t('bot_preset.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('bot_preset.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-combobox :disabled="edit"
                                        v-model="selected_node"
                                        :items="nodes"
                                        item-text="name"
                                        :label="$t('bot_preset.node')"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-combobox v-if="selected_node" :disabled="edit"
                                        v-model="selected_bot"
                                        :items="selected_node.bots"
                                        item-text="name"
                                        :label="$t('bot_preset.bot')"
                            />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-text-field v-if="selected_bot" :disabled="!canUpdate"
                                          :label="$t('bot_preset.name')"
                                          name="name"
                                          type="text"
                                          v-model="preset.name"
                                          v-validate="'required'"
                                          data-vv-name="name"
                                          :error-messages="errors.collect('name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-textarea v-if="selected_bot" :disabled="!canUpdate"
                                        :label="$t('bot_preset.description')"
                                        name="description"
                                        v-model="preset.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <FormParameters v-if="selected_bot"
                                            ui="text"
                                            :sources="selected_bot.parameters"
                                            :values="values"
                                            :disabled="!canUpdate"
                            />
                        </v-col>
                    </v-row>
                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{$t('bot_preset.validation_error')}}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{$t('bot_preset.error')}}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    import {createNewBotPreset} from "@/api/config";
    import {updateBotPreset} from "@/api/config";
    import FormParameters from "../../common/FormParameters";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "NewBotPreset",
        components: {
            FormParameters
        },
        data: () => ({
            visible: false,
            edit: false,
            show_validation_error: false,
            show_error: false,
            selected_node: null,
            selected_bot: null,
            nodes: [],
            values: [],
            preset: {
                id: "",
                name: "",
                description: "",
                bot_id: "",
                parameter_values: []
            }
        }),
        mixins: [AuthMixin],
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_BOT_PRESET_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_BOT_PRESET_UPDATE) || !this.edit
            },
        },
        methods: {
            addPreset() {
                this.visible = true
                this.edit = false
                this.show_error = false;
                this.selected_node = null
                this.selected_bot = null
                this.preset.id = ""
                this.preset.name = ""
                this.preset.description = ""
                this.preset.bot_id = ""
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

                        this.preset.bot_id = this.selected_bot.id;

                        for (let i = 0; i < this.selected_bot.parameters.length; i++) {
                            this.preset.parameter_values[i] = {
                                value: this.values[i],
                                parameter: this.selected_bot.parameters[i]
                            }
                        }

                        if (this.edit) {
                            updateBotPreset(this.preset).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'bot_preset.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {

                            createNewBotPreset(this.preset).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'bot_preset.successful'
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
            this.$store.dispatch('getAllBotsNodes', {search: ''})
                .then(() => {
                    this.nodes = this.$store.getters.getBotsNodes.items
                });

            this.$root.$on('show-edit', (data) => {

                this.visible = true;
                this.edit = true
                this.show_error = false;

                this.preset.id = data.id
                this.preset.name = data.name
                this.preset.description = data.description
                this.preset.bot_id = data.bot_id

                this.preset.parameter_values = []
                for (let i = 0; i < data.parameter_values.length; i++) {
                    this.preset.parameter_values.push({
                        value: data.parameter_values[i].value,
                        parameter: data.parameter_values[i].parameter
                    })
                }

                let found = false
                for (let i = 0; i < this.nodes.length; i++) {
                    for (let j = 0; j < this.nodes[i].bots.length; j++) {
                        if (this.nodes[i].bots[j].id === this.preset.bot_id) {
                            this.selected_node = this.nodes[i]
                            this.selected_bot = this.nodes[i].bots[j]
                            found = true
                            break;
                        }
                    }

                    if (found) {
                        break
                    }
                }

                this.values = []
                for (let i = 0; i < this.selected_bot.parameters.length; i++) {
                    for (let j = 0; j < this.preset.parameter_values.length; j++) {
                        if (this.selected_bot.parameters[i].id === this.preset.parameter_values[j].parameter.id) {
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