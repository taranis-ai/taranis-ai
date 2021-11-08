<template>
    <v-container v-bind="UI.TOOLBAR.CONTAINER" :style="UI.STYLE.shadow">
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                <div :class="UI.CLASS.toolbar_filter_title">{{ $t(title) }}</div>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.MIDDLE">
                <v-text-field v-bind="UI.ELEMENT.SEARCH" v-model="filter.search"
                              :placeholder="$t('toolbar_filter.search')"
                              v-on:keyup="filterSearch"/>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                <slot name="addbutton"></slot>
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col cols="6" v-bind="UI.TOOLBAR.COL.SELECTOR">
                <ToolbarGroupOSINTSource ref="toolbarGroupOSINTSource"/>
            </v-col>
            <v-col cols="6" align="right">
                <v-btn v-bind="UI.BUTTON.ADD_NEW" color="success" @click="openImportDialog">
                    <v-icon left>{{ UI.ICON.IMPORT }}</v-icon>
                    <span>{{ $t('osint_source.import') }}</span>
                </v-btn>
                <v-btn v-bind="UI.BUTTON.ADD_NEW" class="ml-1" color="success" @click="exportSources">
                    <v-icon left>{{ UI.ICON.EXPORT }}</v-icon>
                    <span>{{ $t('osint_source.export') }}</span>
                </v-btn>

                <v-dialog v-model="dialog_import" max-width="600" persistent>
                    <v-overlay v-model="overlay" z-index="50000">
                        <v-progress-circular indeterminate size="64"></v-progress-circular>
                    </v-overlay>
                    <v-card v-bind="UI.DIALOG.BASEMENT">
                        <v-toolbar v-bind="UI.DIALOG.TOOLBAR">
                            <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                                <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                            </v-btn>
                            <v-toolbar-title>{{ $t('osint_source.dialog_import') }}</v-toolbar-title>
                        </v-toolbar>

                        <v-form @submit.prevent="importSources" id="form" ref="form">
                            <v-card-text>
                                <v-combobox v-model="selected_node"
                                            :items="nodes"
                                            item-text="name"
                                            :label="$t('osint_source.node')"
                                            required
                                            v-validate="'required'"
                                            data-vv-name="collector_node"
                                            :error-messages="errors.collect('collector_node')"
                                />
                            </v-card-text>

                            <v-card-text v-if="selected_node" class="pt-4">
                                <v-file-input
                                    v-model="import_file"
                                    accept="application/json"
                                    label="File input"
                                    outlined
                                    dense
                                    :error="file_needed"
                                ></v-file-input>
                            </v-card-text>

                            <v-card-text class="py-0">
                                <v-alert v-if="file_needed" dense type="error" text>
                                    File is required
                                </v-alert>
                                <v-alert v-if="show_validation_error" dense type="error" text>
                                    {{$t('collectors_node.validation_error')}}
                                </v-alert>
                                <v-alert v-if="show_error" dense type="error" text>{{$t('collectors_node.error')}}
                                </v-alert>
                            </v-card-text>
                            <v-card-actions>
                                <v-spacer></v-spacer>
                                <v-btn dense depressed color="primary" dark class="px-3" type="submit" form="form">
                                    <v-icon left>{{ UI.ICON.IMPORT }}</v-icon>
                                    <span>{{ $t('osint_source.import') }}</span>
                                </v-btn>
                            </v-card-actions>
                        </v-form>
                    </v-card>
                </v-dialog>
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.INFO">
                <span>{{ $t(total_count_title) }}<strong>{{ totalCount }}</strong></span>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT"></v-col>
        </v-row>
    </v-container>
</template>

<script>
import AuthMixin from "../../services/auth/auth_mixin";
import ToolbarGroupOSINTSource from "./ToolbarGroupOSINTSource";
import {exportOSINTSources, importOSINTSources} from "@/api/config";

export default {
    name: "ToolbarFilterOSINTSource",
    components: {
        ToolbarGroupOSINTSource
    },
    props: {
        title: String,
        dialog: String,
        total_count_title: String,
        total_count_getter: String
    },
    data: () => ({
        filter: {
            search: "",
        },
        selected_node: null,
        timeout: null,
        dialog_import: false,
        import_file: null,
        nodes: [],
        show_validation_error: false,
        show_error: false,
        overlay: false,
        is_file: false,
        file_needed: false,
        rules: [
            v => !!v || 'File is required'
        ]
    }),
    computed: {
        totalCount() {
            return this.$store.getters[this.total_count_getter].total_count
        },
        multiSelectActive() {
            return this.$store.getters.getOSINTSourcesMultiSelect;
        },
        selected() {
            if( !this.$store.getters.getOSINTSourcesSelection.length ) {
                return {};
            } else {
                return { selection: this.$store.getters.getOSINTSourcesSelection };
            }
        },
        isFile() {
            return Object.entries(this.import_file).length !== 0;
        }
    },
    watch: {
        import_file(val) {
            if( val ) {
                this.is_file = true;
                this.file_needed = false;
            } else {
                this.is_file = false;
            }
        }
    },
    mixins: [AuthMixin],
    methods: {
        importSources() {
            this.$validator.validateAll().then(() => {

                if (!this.$validator.errors.any() && this.is_file) {

                    //this.show_validation_error = false;
                    //this.show_error = false;

                    let formData = new FormData();
                    formData.append("file", this.import_file)
                    formData.append("collectors_node_id", this.selected_node.id)
                    this.overlay = true;
                    importOSINTSources(formData).then(() => {

                        this.overlay = false;
                        this.dialog_import = false;
                        this.$root.$emit('notification',
                            {
                                type: 'success',
                                loc: 'osint_source.notification.success'
                            });

                    }).catch(() => {
                        //this.show_error = true;
                        this.overlay = false;
                        this.$root.$emit('notification',
                            {
                                type: 'error',
                                loc: 'error.server_error'
                            });
                    })
                } else {
                    //this.show_validation_error = true;
                    this.file_needed = true;
                    this.$root.$emit('notification',
                        {
                            type: 'error',
                            loc: 'validations.messages._default'
                        });
                }
            })
        },
        cancel() {
            this.$validator.reset();
            this.dialog_import = false;
        },

        exportSources() {
            exportOSINTSources( this.selected );
        },
        filterSearch: function () {
            clearTimeout(this.timeout);

            let self = this;
            this.timeout = setTimeout(function () {
                self.$root.$emit('update-items-filter', self.filter)
            }, 800);
        },
        changeTheme() {
            this.$vuetify.theme.themes.light.primary = "#f0f";
            this.$vuetify.theme.themes.light.secondary = '#f00';
            this.$vuetify.theme.themes.light.bg = '#0f0';
            this.$vuetify.theme.themes.light.base = '#00f';
        },
        remove(item) {
            this.chips.splice(this.chips.indexOf(item), 1);
            this.chips = [...this.chips]
        },
        openImportDialog() {
            this.dialog_import = true;
            this.$refs.form.reset();
            //this.$refs.form.resetValidation();
            this.$validator.reset();
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

    },
    beforeDestroy() {
        this.$store.commit("setMultiSelect", false);
    }
}
</script>