<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="add_button && canCreate"
               @click="addReportItem">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('analyze.add_new') }}</span>
        </v-btn>

        <v-dialog v-bind="UI.DIALOG.FULLSCREEN"
                  v-model="visible" @keydown.esc="cancel" report-item>
            <v-overlay :value="overlay" z-index="50000">
                <v-progress-circular indeterminate size="64"></v-progress-circular>
            </v-overlay>

            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" data-dialog="report-item">
                    <v-btn icon dark @click="cancel" data-btn="cancel">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('report_item.add_new') }}</span>
                        <span v-else>{{ $t('report_item.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>

                    <!--DiALOG iMPORT CSV-->
                    <v-dialog v-model="dialog_csv" max-width="500px">
                        <template v-if="!edit" v-slot:activator="{ on }">
                            <v-btn v-on="on" text :disabled="!selected_type">
                                <v-icon left>mdi-upload</v-icon>
                                <span>{{$t('report_item.import_csv')}}</span>
                            </v-btn>
                        </template>
                        <v-card>
                            <v-card-title>
                                <span class="headline">{{$t('report_item.import_from_csv')}}</span>
                            </v-card-title>

                            <v-row class="ma-6">
                                <VueCsvImport v-model="csv" :map-fields="csv_struct" autoMatchFields autoMatchIgnoreCase>

                                    <template slot="hasHeaders" slot-scope="{headers, toggle}">
                                        <label style="display: none;">
                                            <input type="checkbox" id="hasHeaders" checked="checked" :value="headers" @change="toggle">
                                            Headers?
                                        </label>
                                    </template>

                                    <template slot="next" slot-scope="{load}">
                                        <button class="load" @click.prevent="load">{{$t('asset.load_csv_file')}}</button>
                                    </template>

                                </VueCsvImport>

                            </v-row>

                            <v-card-actions>
                                <v-spacer></v-spacer>
                                <v-checkbox style="display: none;" v-model="csv_delete_exist_list" :label="$t('report_item.delete_existing_codes')"></v-checkbox>
                                <v-spacer></v-spacer>
                                <v-btn color="primary" dark @click="importCSV">
                                    {{$t('asset.import')}}
                                </v-btn>
                                <v-btn color="primary" text @click="closeCSV">
                                    {{$t('asset.cancel')}}
                                </v-btn>
                            </v-card-actions>
                        </v-card>
                    </v-dialog>
                    <v-switch :disabled="!canModify"
                              style="padding-top:25px"
                              v-model="report_item.completed"
                              label="Completed"
                              @change="onEdit('completed')"
                    ></v-switch>
                    <v-btn v-if="!edit" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('report_item.save') }}</span>
                    </v-btn>

                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12" v-if="edit">
                            <span class="caption grey--text">ID: {{ report_item.uuid }}</span>
                        </v-col>
                        <v-col cols="4" class="pr-3">
                            <v-combobox v-on:change="reportSelected" :disabled="edit"
                                        v-model="selected_type"
                                        :items="report_types"
                                        item-text="title"
                                        :label="$t('report_item.report_type')"
                            />
                        </v-col>
                        <v-col cols="4" class="pr-3">
                            <v-text-field @focus="onFocus('title_prefix')"
                                          @blur="onBlur('title_prefix')"
                                          @keyup="onKeyUp('title_prefix')"
                                          :class="getLockedStyle('title_prefix')"
                                          :disabled="field_locks.title_prefix || !canModify"
                                          :label="$t('report_item.title_prefix')"
                                          name="title_prefix"
                                          v-model="report_item.title_prefix"
                                          :spellcheck="$store.state.settings.spellcheck"
                            ></v-text-field>
                        </v-col>
                        <v-col cols="4" class="pr-3">
                            <v-text-field @focus="onFocus('title')" @blur="onBlur('title')"
                                          @keyup="onKeyUp('title')"
                                          :class="getLockedStyle('title')"
                                          :disabled="field_locks.title || !canModify"
                                          :label="$t('report_item.title')"
                                          name="title"
                                          type="text"
                                          v-model="report_item.title"
                                          v-validate="'required'"
                                          data-vv-name="title"
                                          :error-messages="errors.collect('title')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            ></v-text-field>
                        </v-col>
                    </v-row>
                    <v-row no-gutters class="pb-4">
                        <v-col cols="12">
                            <v-btn v-bind="UI.BUTTON.ADD_NEW_IN" v-if="canModify"
                                   @click="$refs.new_item_selector.openSelector()">
                                <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
                                <span>{{$t('assess.add_news_item')}}</span>
                            </v-btn>
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <NewsItemSelector ref="new_item_selector" analyze_selector
                                              :values="news_item_aggregates"
                                              :modify="modify"
                                              :collections="collections"
                                              :report_item_id="this.report_item.id"
                                              :edit="edit"/>
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <RemoteReportItemSelector :values="remote_report_items" :modify="modify" :edit="edit"
                                                      :report_item_id="this.report_item.id"
                                                      @remote-report-items-changed="updateRemoteAttributes"/>
                        </v-col>
                    </v-row>
                    <v-row>
                        <v-col cols="12" class="pa-0 ma-0">
                            <v-expansion-panels class="mb-1"
                                                v-for="(attribute_group, i) in attribute_groups"
                                                :key="attribute_group.id"
                                                v-model="expandPanelGroups"
                                                multiple
                            >
                                <v-expansion-panel>
                                    <v-expansion-panel-header color="primary--text" class="body-1 text-uppercase pa-3">
                                        {{ attribute_group.title }}
                                    </v-expansion-panel-header>
                                    <v-expansion-panel-content>
                                        <!--TYPES-->
                                        <v-expansion-panels multiple focusable class="items" v-model="expand_group_items[i].values">
                                            <v-expansion-panel v-for="attribute_item in attribute_group.attribute_group_items"
                                                               :key="attribute_item.id"
                                                               class="item-panel"
                                            >
                                                <v-expansion-panel-header class="pa-2 font-weight-bold primary--text rounded-0">
                                                    <v-row>
                                                        <!--<v-icon small left>mdi-account</v-icon>-->
                                                        <span>{{attribute_item.attribute_group_item.title}}</span>
                                                    </v-row>
                                                </v-expansion-panel-header>
                                                <v-expansion-panel-content class="pt-0">
                                                    <AttributeContainer
                                                        :attribute_item="attribute_item" :edit="edit" :modify="modify"
                                                        :report_item_id="report_item.id"
                                                    />
                                                </v-expansion-panel-content>
                                            </v-expansion-panel>
                                        </v-expansion-panels>
                                    </v-expansion-panel-content>
                                </v-expansion-panel>
                            </v-expansion-panels>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{ $t('report_item.validation_error') }}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{ $t('report_item.error') }}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>


            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";
import {createNewReportItem} from "@/api/analyze";
import {updateReportItem} from "@/api/analyze";
import {lockReportItem} from "@/api/analyze";
import {unlockReportItem} from "@/api/analyze";
import {holdLockReportItem} from "@/api/analyze";
import {getReportItem} from "@/api/analyze";
import {getReportItemData} from "@/api/analyze";
import {getReportItemLocks} from "@/api/analyze";
import AttributeContainer from "@/components/common/attribute/AttributeContainer";
import NewsItemSelector from "@/components/analyze/NewsItemSelector";
import RemoteReportItemSelector from "@/components/analyze/RemoteReportItemSelector";

import VueCsvImport from '@/components/common/ImportCSV'

export default {
    name: "NewReportItem",
    props: {
        add_button: Boolean,
        analyze_selector: Boolean,
        collections: Array,
        csv_codes: Array
    },
    components: {NewsItemSelector, AttributeContainer, RemoteReportItemSelector, VueCsvImport},
    data: () => ({
        csv: null,
        csv_delete_exist_list: false,
        csv_preview: true,
        csv_data: null,
        csv_struct: null,
        headers: [
            {text: 'Value', value: 'value', align: 'left', sortable: true},
            {text: 'Actions', value: 'action', align: 'right', sortable: false},
        ],
        dialog: false,
        dialog_csv: false,
        expand_panel_groups: [],
        expand_group_items: [],
        visible: false,
        edit: false,
        modify: true,
        overlay: false,
        local_reports: true,
        key_timeout: null,
        show_validation_error: false,
        show_error: false,
        report_types: [],
        selected_type: null,
        attribute_groups: [],
        news_item_aggregates: [],
        remote_report_items: [],
        field_locks: {
            title_prefix: false,
            title: false
        },
        report_item: {
            id: null,
            uuid: null,
            title: "",
            title_prefix: "",
            completed: false,
            report_item_type_id: null,
            news_item_aggregates: [],
            remote_report_items: [],
            attributes: []
        }
    }),
    computed: {
        canCreate() {
            return this.checkPermission(Permissions.ANALYZE_CREATE) && this.local_reports === true
        },

        canModify() {
            return this.edit === false || (this.checkPermission(Permissions.ANALYZE_UPDATE) && this.modify === true)
        },
        expandPanelGroups() {
            return this.expand_groups();
        }
    },
    methods: {
        addReportItem() {
            this.visible = true;
            this.modify = true;
            this.edit = false
            this.overlay = false
            this.show_error = false;
            this.field_locks.title = false;
            this.field_locks.title_prefix = false;
            this.attachmets_attributes_count = 0;
            this.selected_type = null;
            this.attribute_groups = [];
            this.news_item_aggregates = [];
            this.remote_report_items = []
            this.report_item.id = null;
            this.report_item.uuid = null;
            this.report_item.title = "";
            this.report_item.title_prefix = "";
            this.report_item.completed = false;
            this.$validator.reset();
        },

        reportSelected() {

            this.attribute_groups = [];
            this.expand_group_items = [];

            for (let i = 0; i < this.selected_type.attribute_groups.length; i++) {
                let group = {
                    id: this.selected_type.attribute_groups[i].id,
                    title: this.selected_type.attribute_groups[i].title,
                    attribute_group_items: []
                };

                for (let j = 0; j < this.selected_type.attribute_groups[i].attribute_group_items.length; j++) {
                    group.attribute_group_items.push({
                        attribute_group_item: this.selected_type.attribute_groups[i].attribute_group_items[j],
                        values: []
                    })
                }

                this.attribute_groups.push(group)
                this.expand_group_items.push({values: Array.from(Array(group.attribute_group_items.length).keys())});
            }

            this.csv_struct = this.findAttributeType();
        },

        cancel() {
            setTimeout(() => {
                //this.$root.$emit('mouse-click-close');
                this.$root.$emit('change-state', 'DEFAULT');
                this.$validator.reset();
                this.visible = false;
                this.$root.$emit('first-dialog', '');
            }, 150);

        },

        add() {
            this.$validator.validateAll().then(() => {

                if (!this.$validator.errors.any()) {

                    this.overlay = true

                    this.show_validation_error = false;
                    this.show_error = false;

                    this.report_item.report_item_type_id = this.selected_type.id;

                    this.report_item.news_item_aggregates = [];
                    for (let i = 0; i < this.news_item_aggregates.length; i++) {
                        this.report_item.news_item_aggregates.push(
                                {
                                    id: this.news_item_aggregates[i].id
                                }
                        )
                    }

                    this.report_item.remote_report_items = [];
                    for (let i = 0; i < this.remote_report_items.length; i++) {
                        this.report_item.remote_report_items.push(
                                {
                                    id: this.remote_report_items[i].id
                                }
                        )
                    }

                    this.report_item.attributes = [];
                    for (let i = 0; i < this.attribute_groups.length; i++) {

                        for (let j = 0; j < this.attribute_groups[i].attribute_group_items.length; j++) {

                            for (let k = 0; k < this.attribute_groups[i].attribute_group_items[j].values.length; k++) {

                                let value = this.attribute_groups[i].attribute_group_items[j].values[k].value
                                if (this.attribute_groups[i].attribute_group_items[j].attribute_group_item.attribute.type === 'CPE') {
                                    value = value.replace("*", "%")
                                } else if (this.attribute_groups[i].attribute_group_items[j].attribute_group_item.attribute.type === 'BOOLEAN') {
                                    if (value === true) {
                                        value = "true"
                                    } else {
                                        value = "false"
                                    }
                                }

                                if (this.attribute_groups[i].attribute_group_items[j].attribute_group_item.attribute.type !== 'ATTACHMENT') {
                                    this.report_item.attributes.push({
                                        id: -1,
                                        value: value,
                                        attribute_group_item_id: this.attribute_groups[i].attribute_group_items[j].attribute_group_item.id
                                    })
                                }
                            }
                        }
                    }

                    createNewReportItem(this.report_item).then((response) => {

                        this.attachmets_attributes_count = 0
                        for (let i = 0; i < this.attribute_groups.length; i++) {
                            for (let j = 0; j < this.attribute_groups[i].attribute_group_items.length; j++) {
                                if (this.attribute_groups[i].attribute_group_items[j].attribute_group_item.attribute.type === 'ATTACHMENT') {
                                    this.attachmets_attributes_count++
                                }
                            }
                        }

                        if (this.attachmets_attributes_count > 0) {
                            this.$root.$emit('dropzone-new-process', {report_item_id: response.data});
                        } else {
                            this.$root.$emit('attachments-uploaded', {});
                        }

                    }).catch(() => {

                        this.show_error = true;
                        this.overlay = false
                    })

                } else {

                    this.show_validation_error = true;
                }
            })
        },

        getLockedStyle(field_id) {
            return this.field_locks[field_id] === true ? 'locked-style' : ''
        },

        onFocus(field_id) {
            if (this.edit === true) {
                lockReportItem(this.report_item.id, {'field_id': field_id}).then(() => {
                })
            }
        },

        onBlur(field_id) {
            if (this.edit === true) {

                this.onEdit(field_id)
                unlockReportItem(this.report_item.id, {'field_id': field_id}).then(() => {
                })
            }
        },

        onKeyUp(field_id) {
            if (this.edit === true) {

                clearTimeout(this.key_timeout);
                let self = this;
                this.key_timeout = setTimeout(function () {
                    holdLockReportItem(self.report_item.id, {'field_id': field_id}).then(() => {
                    })
                }, 1000);
            }
        },

        onEdit(field_id) {
            if (this.edit === true) {

                let data = {}
                data.update = true
                if (field_id === 'title') {
                    data.title = this.report_item.title
                } else if (field_id === 'title_prefix') {
                    data.title_prefix = this.report_item.title_prefix
                } else if (field_id === 'completed') {
                    data.completed = this.report_item.completed
                }

                updateReportItem(this.report_item.id, data).then(() => {
                })
            }
        },

        report_item_locked(data) {
            if (this.edit === true && this.report_item.id === data.report_item_id) {
                if (data.user_id !== this.$store.getters.getUserId) {
                    this.field_locks[data.field_id] = true
                }
            }
        },
        report_item_unlocked(data) {
            if (this.edit === true && this.report_item.id === data.report_item_id) {
                if (data.user_id !== this.$store.getters.getUserId) {
                    this.field_locks[data.field_id] = false
                }
            }
        },
        report_item_updated(data_info) {
            if (this.edit === true && this.report_item.id === data_info.report_item_id) {
                if (data_info.user_id !== this.$store.getters.getUserId) {
                    getReportItemData(this.report_item.id, data_info).then((response) => {
                        let data = response.data
                        if (data.title !== undefined) {
                            this.report_item.title = data.title
                        } else if (data.title_prefix !== undefined) {
                            this.report_item.title_prefix = data.title_prefix
                        } else if (data.completed !== undefined) {
                            this.report_item.completed = data.completed
                        }
                    })
                }
            }
        },
        showDetail(report_item) {
            getReportItem(report_item.id).then((response) => {

                let data = response.data;

                this.visible = true;
                this.edit = true;
                this.overlay = false
                this.show_error = false;
                this.modify = report_item.modify;

                this.field_locks.title = false;
                this.field_locks.title_prefix = false;

                this.selected_type = null;
                this.attribute_groups = [];
                this.news_item_aggregates = data.news_item_aggregates;
                this.remote_report_items = data.remote_report_items;

                this.report_item.id = data.id;
                this.report_item.uuid = data.uuid;
                this.report_item.title = data.title;
                this.report_item.title_prefix = data.title_prefix;
                this.report_item.report_item_type_id = data.report_item_type_id;
                this.report_item.completed = data.completed;

                for (let i = 0; i < this.report_types.length; i++) {
                    if (this.report_types[i].id === this.report_item.report_item_type_id) {
                        this.selected_type = this.report_types[i];

                        this.expand_panel_groups = Array.from(Array(this.selected_type.attribute_groups.length).keys());
                        this.expand_group_items = [];

                        for( let j=0; j<this.expand_panel_groups.length; j++) {
                            this.expand_group_items.push({values: Array.from(Array(this.selected_type.attribute_groups[j].attribute_group_items.length).keys())});
                        }
                        break;
                    }
                }

                getReportItemLocks(this.report_item.id).then((response) => {
                    let locks_data = response.data

                    if (locks_data.title !== undefined && locks_data.title !== null) {
                        this.field_locks['title'] = true
                    } else if (locks_data.title_prefix !== undefined && locks_data.title_prefix !== null) {
                        this.field_locks['title_prefix'] = true
                    }

                    for (let i = 0; i < this.selected_type.attribute_groups.length; i++) {
                        let group = {
                            id: this.selected_type.attribute_groups[i].id,
                            title: this.selected_type.attribute_groups[i].title,
                            attribute_group_items: []
                        };

                        for (let j = 0; j < this.selected_type.attribute_groups[i].attribute_group_items.length; j++) {

                            let values = [];
                            for (let k = 0; k < data.attributes.length; k++) {
                                if (data.attributes[k].attribute_group_item_id === this.selected_type.attribute_groups[i].attribute_group_items[j].id) {

                                    let value = data.attributes[k].value
                                    if (this.selected_type.attribute_groups[i].attribute_group_items[j].attribute.type === 'CPE') {
                                        value = value.replace("%", "*")
                                    } else if (this.selected_type.attribute_groups[i].attribute_group_items[j].attribute.type === 'BOOLEAN') {
                                        value = value === "true";
                                    }

                                    let locked = false
                                    if (locks_data["'" + data.attributes[k].id + "'"] !== undefined && locks_data["'" + data.attributes[k].id + "'"] !== null) {
                                        locked = true
                                    }

                                    values.push({
                                        id: data.attributes[k].id,
                                        index: values.length,
                                        value: value,
                                        binary_mime_type: data.attributes[k].binary_mime_type,
                                        binary_size: data.attributes[k].binary_size,
                                        binary_description: data.attributes[k].binary_description,
                                        last_updated: data.attributes[k].last_updated,
                                        user: data.attributes[k].user,
                                        locked: locked,
                                        remote: false
                                    });
                                }
                            }

                            for (let l = 0; l < data.remote_report_items.length; l++) {
                                for (let k = 0; k < data.remote_report_items[l].attributes.length; k++) {
                                    if (data.remote_report_items[l].attributes[k].attribute_group_item_title === this.selected_type.attribute_groups[i].attribute_group_items[j].title) {

                                        let value = data.remote_report_items[l].attributes[k].value
                                        if (this.selected_type.attribute_groups[i].attribute_group_items[j].attribute.type === 'CPE') {
                                            value = value.replace("%", "*")
                                        } else if (this.selected_type.attribute_groups[i].attribute_group_items[j].attribute.type === 'BOOLEAN') {
                                            value = value === "true";
                                        }

                                        values.push({
                                            id: data.remote_report_items[l].attributes[k].id,
                                            index: values.length,
                                            value: value,
                                            last_updated: data.remote_report_items[l].attributes[k].last_updated,
                                            binary_mime_type: data.remote_report_items[l].attributes[k].binary_mime_type,
                                            binary_size: data.remote_report_items[l].attributes[k].binary_size,
                                            binary_description: data.remote_report_items[l].attributes[k].binary_description,
                                            user: {name: data.remote_report_items[l].remote_user},
                                            locked: false,
                                            remote: true
                                        });
                                    }
                                }
                            }

                            group.attribute_group_items.push({
                                attribute_group_item: this.selected_type.attribute_groups[i].attribute_group_items[j],
                                values: values
                            })
                        }

                        this.attribute_groups.push(group)
                    }
                })
            })
        },

        updateRemoteAttributes() {
            for (let i = 0; i < this.attribute_groups.length; i++) {
                for (let j = 0; j < this.attribute_groups[i].attribute_group_items.length; j++) {
                    for (let k = 0; k < this.attribute_groups[i].attribute_group_items[j].values.length; k++) {
                        if (this.attribute_groups[i].attribute_group_items[j].values[k].remote === true) {
                            this.attribute_groups[i].attribute_group_items[j].values.splice(k, 1)
                            k--
                        }
                    }

                    for (let l = 0; l < this.remote_report_items.length; l++) {
                        for (let k = 0; k < this.remote_report_items[l].attributes.length; k++) {
                            if (this.remote_report_items[l].attributes[k].attribute_group_item_title === this.attribute_groups[i].attribute_group_items[j].title) {

                                let value = this.remote_report_items[l].attributes[k].value
                                if (this.attribute_groups[i].attribute_group_items[j].attribute.type === 'CPE') {
                                    value = value.replace("%", "*")
                                } else if (this.attribute_groups[i].attribute_group_items[j].attribute.type === 'BOOLEAN') {
                                    value = value === "true";
                                }

                                this.attribute_groups[i].attribute_group_items[j].values.push({
                                    id: this.remote_report_items[l].attributes[k].id,
                                    index: this.attribute_groups[i].attribute_group_items[j].values.length,
                                    value: value,
                                    last_updated: this.remote_report_items[l].attributes[k].last_updated,
                                    binary_mime_type: this.remote_report_items[l].attributes[k].binary_mime_type,
                                    binary_size: this.remote_report_items[l].attributes[k].binary_size,
                                    binary_description: this.remote_report_items[l].attributes[k].binary_description,
                                    user: {name: this.remote_report_items[l].remote_user},
                                    locked: false,
                                    remote: true
                                });
                            }
                        }
                    }
                }
            }
        },

        expand_groups() {
            return this.expand_panel_groups = Array.from(Array(this.attribute_groups.length).keys());
        },

        findAttributeType() {
            let groups = this.selected_type.attribute_groups;
            let available = [];

            for( let i=0; i<groups.length; i++) {
                let group = groups[i];

                for( let j=0; j<group.attribute_group_items.length; j++) {
                    available.push(group.attribute_group_items[j].title.replace(" ", "_"));
                }
            }
            return available;
        },
        importCSV() {
            let csv_lines = this.csv.length;
            let sorted_csv = new Array();

            for( let c=0; c<this.csv_struct.length; c++) {
                sorted_csv.push([]);
                for( let d=1; d<csv_lines; d++) {
                    sorted_csv[c].push( this.csv[d][this.csv_struct[c]] );
                }
            }

            let count = 0;
            for( let i=0; i<this.attribute_groups.length; i++) {
                for (let j=0; j<this.attribute_groups[i].attribute_group_items.length; j++) {

                    this.attribute_groups[i].attribute_group_items[j].values = [];
                    for( let k=0; k<csv_lines-1; k++) {
                        if(sorted_csv[count][k] !== "") {
                            this.attribute_groups[i].attribute_group_items[j].values.push({ "id": -1, "index": k, "value": sorted_csv[count][k], "user": null });
                        }
                    }
                    count++;
                }
            }

            this.dialog_csv = false;
            this.csv = null;
            this.csv_delete_exist_list = false;
            this.$root.$emit('reset-csv-dialog');

        },

        closeCSV() {
            this.dialog_csv = false;
            this.csv = null;
            this.csv_delete_exist_list = false;
            this.$root.$emit('reset-csv-dialog');
        },
    },
    mixins: [AuthMixin],
    mounted() {
        this.$root.$on('attachments-uploaded', () => {
            this.attachmets_attributes_count--
            if (this.attachmets_attributes_count <= 0) {
                this.$validator.reset();
                this.visible = false;
                this.overlay = false
                this.$root.$emit('notification',
                        {
                            type: 'success',
                            loc: 'report_item.successful'
                        }
                );
            }
        });

        this.local_reports = !window.location.pathname.includes('/group/');

        this.$store.dispatch('getAllReportItemTypes', {search: ''})
                .then(() => {
                    this.report_types = this.$store.getters.getReportItemTypes.items;
                });

        this.$root.$on('new-report', (data) => {
            this.visible = true;
            this.selected_type = null;
            this.attribute_groups = [];
            this.news_item_aggregates = data;

            this.$root.$emit('first-dialog', 'push');
        });

        this.$root.$on('report-item-locked', this.report_item_locked);
        this.$root.$on('report-item-unlocked', this.report_item_unlocked);
        this.$root.$on('report-item-updated', this.report_item_updated);
    },
    watch: {
        $route() {
            this.local_reports = !window.location.pathname.includes('/group/');
        }
    },
    beforeDestroy() {
        this.$root.$off('attachments-uploaded')
        this.$root.$off('new-report')
        this.$root.$off('show-edit')

        this.$root.$off('report-item-locked', this.report_item_locked);
        this.$root.$off('report-item-unlocked', this.report_item_unlocked);
        this.$root.$off('report-item-updated', this.report_item_updated);
    }
}
</script>