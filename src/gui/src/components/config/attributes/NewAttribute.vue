<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addAttribute">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{$t('attribute.add_btn')}}</span>
        </v-btn>
        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('attribute.add_new') }}</span>
                        <span v-else>{{ $t('attribute.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canUpdate" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{$t('attribute.save')}}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('attribute.name')"
                                          name="name"
                                          type="text"
                                          v-model="attribute.name"
                                          v-validate="'required'"
                                          data-vv-name="name"
                                          :error-messages="errors.collect('name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12">
                            <v-textarea :disabled="!canUpdate"
                                        :label="$t('attribute.description')"
                                        name="description"
                                        v-model="attribute.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="6" class="pa-1">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('attribute.default_value')"
                                          name="default_value"
                                          type="text"
                                          v-model="attribute.default_value"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="6" class="pa-1">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('attribute.default_value')"
                                          name="default_value"
                                          type="text"
                                          v-model="attribute.default_value"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="6" class="pa-1">
                            <v-combobox :disabled="!canUpdate"
                                        v-model="selected_validator"
                                        :items="validators"
                                        item-text="title"
                                        :label="$t('attribute.validator')"
                            />
                        </v-col>
                        <v-col cols="6" class="pa-1">
                            <v-text-field :disabled="!canUpdate"
                                          :label="$t('attribute.validator_parameter')"
                                          type="text"
                                          v-model="attribute.validator_parameter"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>

                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-data-table :disabled="!canUpdate"
                                          :headers="headers"
                                          :items="attribute.attribute_enums"
                                          :server-items-length="attribute.attribute_enums_total_count"
                                          @update:options="updateOptions"
                                          :items-per-page="25"
                                          class="elevation-1"
                                          :page.sync="current_page"
                                          :footer-props="{
                                                      showFirstLastPage: true,
                                                      itemsPerPageOptions: [25, 50, 100],
                                                      showCurrentPage: true
                                                    }"

                            >
                                <template v-slot:top>
                                    <v-toolbar flat color="white">
                                        <v-toolbar-title>{{$t('attribute.attribute_constants')}}</v-toolbar-title>
                                        <v-divider
                                            class="mx-4"
                                            inset
                                            vertical
                                        ></v-divider>
                                        <v-spacer></v-spacer>
                                        <v-text-field
                                            v-model="search"
                                            append-icon="mdi-magnify"
                                            :label="$t('attribute.search')"
                                            v-on:keyup="filterSearch"
                                            single-line
                                            hide-details
                                        ></v-text-field>
                                        <v-spacer></v-spacer>
                                        <v-btn v-if="edit && selected_type !== null && selected_type.id === 'CVE'"
                                               color="primary" dark class="mb-2 mr-3"
                                               @click="reloadDictionary('cve')">
                                            <v-icon left>mdi-refresh</v-icon>
                                            <span>{{$t('attribute.reload_cve')}}</span>
                                        </v-btn>
                                        <v-btn v-if="edit && selected_type !== null && selected_type.id === 'CPE'"
                                               color="primary" dark class="mb-2 mr-3"
                                               @click="reloadDictionary('cpe')">
                                            <v-icon left>mdi-refresh</v-icon>
                                            <span>{{$t('attribute.reload_cpe')}}</span>
                                        </v-btn>

                                        <v-dialog v-if="canUpdate" v-model="dialog" max-width="500px">
                                            <template v-slot:activator="{ on }">
                                                <span style="width: 10px"></span>
                                                <v-btn color="primary" dark class="mb-2" v-on="on">
                                                    <v-icon left>mdi-plus</v-icon>
                                                    <span>{{$t('attribute.new_constant')}}</span>
                                                </v-btn>

                                            </template>
                                            <v-card>
                                                <v-card-title>
                                                    <span class="headline">{{ formTitle }}</span>
                                                </v-card-title>

                                                <v-card-text>

                                                    <v-text-field v-model="edited_constant.value"
                                                                  :label="$t('attribute.value')"
                                                                  :spellcheck="$store.state.settings.spellcheck"></v-text-field>

                                                    <v-text-field v-model="edited_constant.description"
                                                                  :label="$t('attribute.description')"
                                                                  :spellcheck="$store.state.settings.spellcheck"></v-text-field>

                                                </v-card-text>

                                                <v-card-actions>
                                                    <v-spacer></v-spacer>
                                                    <v-btn color="primary" dark @click="save">
                                                        {{$t('attribute.save')}}
                                                    </v-btn>
                                                    <v-btn color="primary" text @click="close">
                                                        {{$t('attribute.cancel')}}
                                                    </v-btn>
                                                </v-card-actions>
                                            </v-card>
                                        </v-dialog>

                                        <v-dialog v-model="importDialog" persistent max-width="290">
                                            <v-card>
                                                <v-card-title class="headline">{{$t('attribute.reloading')}}</v-card-title>
                                                <v-progress-linear indeterminate color="primary" />
                                            </v-card>
                                        </v-dialog>

                                        <v-dialog v-if="canUpdate" v-model="dialog_csv" max-width="700px">
                                            <template v-slot:activator="{ on }">
                                                <v-btn color="primary" dark class="mb-2" v-on="on">
                                                    <v-icon left>mdi-upload</v-icon>
                                                    <span>{{$t('attribute.import_from_csv')}}</span>
                                                </v-btn>
                                            </template>
                                            <v-card>
                                                <v-card-title>
                                                    <span class="headline">{{$t('attribute.import_from_csv')}}</span>
                                                </v-card-title>

                                                <v-row class="ma-6">
                                                    <VueCsvImport
                                                        v-model="csv"
                                                        :map-fields="['value', 'description']"
                                                    >

                                                        <template slot="hasHeaders" slot-scope="{headers, toggle}">
                                                            <label>
                                                                <input type="checkbox" id="hasHeaders"
                                                                       :value="headers" @change="toggle">
                                                                {{$t('attribute.file_has_header')}}
                                                            </label>
                                                        </template>

                                                        <template slot="next" slot-scope="{load}">
                                                            <button class="load" @click.prevent="load">
                                                                {{$t('attribute.load_csv_file')}}
                                                            </button>
                                                        </template>

                                                    </VueCsvImport>
                                                </v-row>

                                                <div v-if="csv_preview" class="mt-2 px-4">
                                                    <v-row class="pa-0 ma-0 grey white--text">
                                                        <v-col class="pa-0 ma-0">
                                                            <span class="heading">{{$t('attribute.value')}}</span>
                                                        </v-col>
                                                        <v-col class="pa-0 ma-0">
                                                            <span class="heading">{{$t('attribute.description')}}</span>
                                                        </v-col>
                                                    </v-row>

                                                    <v-card-text class="ma-0 pa-0" v-for="parse in csv"
                                                                 :key="parse.value">

                                                        <v-row class="pa-0 ma-0">
                                                            <v-col class="pa-0 ma-0">
                                                                {{parse.value}}
                                                            </v-col>
                                                            <v-col class="pa-0 ma-0">
                                                                {{parse.description}}
                                                            </v-col>
                                                        </v-row>

                                                    </v-card-text>
                                                </div>

                                                <v-card-actions>
                                                    <v-spacer></v-spacer>
                                                    <v-checkbox v-model="csv_delete_exist_list"
                                                                :label="$t('attribute.delete_existing')"></v-checkbox>
                                                    <v-spacer></v-spacer>
                                                    <v-btn color="primary" dark @click="importCSV">
                                                        {{$t('attribute.import')}}
                                                    </v-btn>
                                                    <v-btn color="primary" text @click="closeCSV">
                                                        {{$t('attribute.cancel')}}
                                                    </v-btn>
                                                </v-card-actions>
                                            </v-card>
                                        </v-dialog>

                                    </v-toolbar>
                                </template>
                                <template v-slot:item.action="{ item }">
                                    <v-icon v-if="canUpdate"
                                            small
                                            class="mr-2"
                                            @click="editItem(item)"
                                    >
                                        edit
                                    </v-icon>
                                    <v-icon v-if="canUpdate"
                                            small
                                            @click="deleteItem(item)"
                                    >
                                        delete
                                    </v-icon>
                                </template>
                            </v-data-table>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{$t('attribute.validation_error')}}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{$t('attribute.error')}}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
    import {createNewAttribute} from "@/api/config";
    import {updateAttribute} from "@/api/config";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";
    import {getAttributeEnums} from "@/api/config";
    import {deleteAttributeEnum} from "@/api/config";
    import {addAttributeEnum} from "@/api/config";
    import {updateAttributeEnum} from "@/api/config";
    import {reloadDictionaries} from "@/api/config";

    import VueCsvImport from '@/components/common/ImportCSV';

    export default {
        name: "NewAttribute",
        components: {
            VueCsvImport
        },
        data: () => ({
            csv: null,
            csv_delete_exist_list: false,
            csv_preview: false,
            visible: false,
            edit: false,
            show_validation_error: false,
            show_error: false,
            search: "",
            importDialog: false,
            headers: [
                {
                    text: 'Value',
                    align: 'left',
                    sortable: false,
                    value: 'value'
                },
                {text: 'Description', value: 'description', sortable: false},
                {text: 'Actions', value: 'action', align: 'right', sortable: false},
            ],
            current_page: 1,
            current_page_size: 25,
            dialog: false,
            dialog_csv: false,
            edited_index: -1,
            edited_constant: {id: -1, index: 0, value: "", description: ""},
            default_constant: {id: -1, index: 0, value: "", description: ""},
            types: [
                {id: "STRING", title: "Text"},
                {id: "NUMBER", title: "Number"},
                {id: "BOOLEAN", title: "Boolean"},
                {id: "RADIO", title: "Radio"},
                {id: "ENUM", title: "Enumeration"},
                {id: "TEXT", title: "Text"},
                {id: "RICH_TEXT", title: "Rich Text"},
                {id: "DATE", title: "Date"},
                {id: "TIME", title: "Time"},
                {id: "DATE_TIME", title: "Date Time"},
                {id: "LINK", title: "Link"},
                {id: "ATTACHMENT", title: "Attachment"},
                {id: "TLP", title: "TLP"},
                {id: "CVE", title: "CVE"},
                {id: "CPE", title: "CPE"},
                {id: "CVSS", title: "CVSS"},
            ],
            selected_type: null,
            validators: [
                {id: "EMAIL", title: "Email"},
                {id: "NUMBER", title: "Number"},
                {id: "RANGE", title: "Range"},
                {id: "REGEXP", title: "Regular Expression"},
            ],
            selected_validator: null,
            attribute: {
                id: -1,
                name: "",
                description: "",
                type: null,
                default_value: "",
                validator: "NONE",
                validator_parameter: "",
                attribute_enums: [],
                attribute_enums_total_count: 0
            }
        }),
        mixins: [AuthMixin],
        computed: {
            canCreate() {
                return this.checkPermission(Permissions.CONFIG_ATTRIBUTE_CREATE)
            },
            canUpdate() {
                return this.checkPermission(Permissions.CONFIG_ATTRIBUTE_UPDATE) || !this.edit
            },

            formTitle() {
                return this.edited_index === -1 ? 'Add Constant' : 'Edit Constant'
            }
        },
        watch: {
            dialog(val) {
                val || this.close()
            },
        },
        methods: {
            addAttribute() {
                this.visible = true;
                this.edit = false
                this.show_error = false;
                this.selected_validator = null;
                this.selected_type = null;
                this.attribute.id = -1;
                this.attribute.name = "";
                this.attribute.description = "";
                this.attribute.type = null;
                this.attribute.default_value = "";
                this.attribute.validator = "NONE";
                this.attribute.validator_parameter = "";
                this.attribute.attribute_enums = []
                this.attribute.attribute_enums_total_count = 0
                this.$validator.reset();
            },

            close() {
                this.dialog = false;
                setTimeout(() => {
                    this.edited_constant = Object.assign({}, this.default_constant);
                    this.edited_index = -1
                }, 300)
            },

            save() {
                if (this.edited_index > -1) {
                    if (this.edit === true) {
                        updateAttributeEnum(this.attribute.id, [this.edited_constant]).then(() => {
                            this.updateAttributeEnums()
                        })
                    } else {
                        Object.assign(this.attribute.attribute_enums[this.edited_index], this.edited_constant)
                    }
                } else {
                    if (this.edit === true) {
                        addAttributeEnum(this.attribute.id, {
                            items: [this.edited_constant],
                            delete_existing: false
                        }).then(() => {
                            this.updateAttributeEnums()
                        })
                    } else {
                        this.attribute.attribute_enums.push(this.edited_constant);
                        this.attribute.attribute_enums_total_count++
                    }
                }
                this.close()
            },

            importCSV() {

                if (this.edit === true) {

                    addAttributeEnum(this.attribute.id, {
                        items: this.csv,
                        delete_existing: this.csv_delete_exist_list
                    }).then(() => {
                        this.updateAttributeEnums()
                    })

                } else {
                    if (this.csv_delete_exist_list) {
                        this.attribute.attribute_enums = null;
                        this.attribute.attribute_enums = this.csv;

                        for (let i = 0; i < this.csv.length; i++) {
                            this.attribute.attribute_enums[i].index = i;
                        }
                    } else {

                        let arrayWithDuplicates = this.attribute.attribute_enums.concat(this.csv);

                        let removeDuplicates = function (originalArray, prop) {
                            let newArray = [];
                            let lookupObject = {};

                            for (var i in originalArray) {
                                lookupObject[originalArray[i][prop]] = originalArray[i];
                            }

                            for (i in lookupObject) {
                                newArray.push(lookupObject[i]);
                            }

                            return newArray;
                        }

                        let uniqueArray = removeDuplicates(arrayWithDuplicates, "value");
                        this.attribute.attribute_enums = uniqueArray;

                        for (let i = 0; i < uniqueArray.length; i++) {
                            this.attribute.attribute_enums[i].index = i;
                        }
                    }

                    this.attribute.attribute_enums_total_count = this.attribute.attribute_enums.length
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

            editItem(item) {
                this.edited_index = this.attribute.attribute_enums.indexOf(item);
                this.edited_constant = Object.assign({}, item);
                this.dialog = true
            },

            deleteItem(item) {
                if (this.edit === true) {
                    deleteAttributeEnum(this.attribute.id, item.id).then(() => {
                        this.updateAttributeEnums()
                    })
                } else {
                    const index = this.attribute.attribute_enums.indexOf(item);
                    this.attribute.attribute_enums.splice(index, 1)
                }
            },

            cancel() {
                this.$validator.reset();
                this.visible = false
            },

            reloadDictionary(type) {
                this.importDialog = true
                reloadDictionaries(type).then(() => {
                    this.importDialog = false
                    this.current_page = 1
                    this.updateAttributeEnums()
                })
            },

            add() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.show_validation_error = false;
                        this.show_error = false;

                        this.attribute.type = this.selected_type.id;

                        if (this.selected_validator !== null) {
                            this.attribute.validator = this.selected_validator.id;
                        }

                        if (this.edit) {
                            updateAttribute(this.attribute).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'attribute.successful_edit'
                                    }
                                )
                            }).catch(() => {

                                this.show_error = true;
                            })
                        } else {
                            createNewAttribute(this.attribute).then(() => {

                                this.$validator.reset();
                                this.visible = false;
                                this.$root.$emit('notification',
                                    {
                                        type: 'success',
                                        loc: 'attribute.successful'
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

            filterSearch() {
                clearTimeout(this.timeout);

                let self = this
                this.timeout = setTimeout(function () {
                    self.current_page = 1
                    self.updateAttributeEnums()
                }, 300);
            },

            updateAttributeEnums() {
                getAttributeEnums({
                    attribute_id: this.attribute.id,
                    search: this.search,
                    offset: (this.current_page - 1) * this.current_page_size,
                    limit: this.current_page_size
                }).then((response) => {
                    this.attribute.attribute_enums = []
                    this.attribute.attribute_enums_total_count = response.data.total_count
                    for (let i = 0; i < response.data.items.length; i++) {
                        this.attribute.attribute_enums.push(response.data.items[i])
                    }
                })
            },

            updateOptions(options) {
                if (this.edit === true) {
                    this.current_page = options.page
                    this.current_page_size = options.itemsPerPage
                    this.updateAttributeEnums()
                }
            }
        },
        mounted() {
            this.$root.$on('show-edit', (data) => {
                this.visible = true;
                this.edit = true;
                this.show_error = false;
                this.attribute.id = data.id
                this.attribute.name = data.name
                this.attribute.description = data.description
                this.attribute.default_value = data.default_value
                this.attribute.validator = data.validator
                this.attribute.type = data.type
                this.attribute.validator_parameter = data.validator_parameter
                this.attribute.attribute_enums_total_count = data.attribute_enums_total_count

                for (let i = 0; i < this.types.length; i++) {
                    if (this.types[i].id === data.type) {
                        this.selected_type = this.types[i]
                    }
                }

                for (let i = 0; i < this.validators.length; i++) {
                    if (this.validators[i].id === data.validator) {
                        this.selected_validator = this.validators[i]
                    }
                }

                this.updateAttributeEnums()
            });
        },
        beforeDestroy() {
            this.$root.$off('show-edit')
        }
    }
</script>