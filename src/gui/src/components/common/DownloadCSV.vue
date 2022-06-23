<template>
    <v-container>
        <v-row class="mt-0">
            <v-col>
                <v-checkbox v-model="hasHeaders" :label="$t('word_list.file_has_header')" hide-details class="mt-0" />
            </v-col>
        </v-row>
        <v-row class="mt-1">
            <v-col>
                <v-text-field :disabled="true" :label="$t('word_list.link')" name="category_link" v-model="link"
                    hide-details></v-text-field>
            </v-col>
        </v-row>
        <v-row class="mt-1" v-if="error">
            <v-col>
                <span style="color:red">{{ error }}</span>
            </v-col>
        </v-row>
        <v-row class="mt-1">
            <v-col>
                <v-btn color="primary" @click="downloadCSV" :disabled="disableDownloadButton">
                    {{ $t('word_list.download_from_link') }}</v-btn>
            </v-col>
        </v-row>
        <v-row v-if="sample" class="mt-1">
            <v-col>
                <v-simple-table>
                    <slot name="thead">
                        <thead>
                            <tr>
                                <th>Field</th>
                                <th>CSV Column</th>
                            </tr>
                        </thead>
                    </slot>
                    <tbody>
                        <tr v-for="(field, key) in fieldsToMap" :key="key">
                            <td>{{ field.label }}</td>
                            <td>
                                <v-select :name="`csv_uploader_map_${key}`" v-model="map[field.key]"
                                    :items="selectItems" item-text="text" item-value="value" />
                            </td>
                        </tr>
                    </tbody>
                </v-simple-table>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
import { drop, every, forEach, get, isArray, map, set } from 'lodash';
import axios from 'axios';
import Papa from 'papaparse';

export default {
    props: {
        value: Array,
        link: {
            type: String
        },
        mapFields: {
            required: true
        },
        callback: {
            type: Function,
            default: () => ({})
        },
        catch: {
            type: Function,
            default: () => ({})
        },
        finally: {
            type: Function,
            default: () => ({})
        },
        parseConfig: {
            type: Object,
            default() {
                return {};
            }
        },
        headers: {
            default: null
        },
        autoMatchFields: {
            type: Boolean,
            default: false
        },
        autoMatchIgnoreCase: {
            type: Boolean,
            default: false
        },
        validation: {
            type: Boolean,
            default: true,
        },
    },

    data: () => ({
        form: {
            csv: null,
        },
        fieldsToMap: [],
        map: {},
        hasHeaders: true,
        csv: null,
        sample: null,
        error: null,
    }),

    created() {
        this.hasHeaders = this.headers;

        if (isArray(this.mapFields)) {
            this.fieldsToMap = map(this.mapFields, (item) => {
                return {
                    key: item,
                    label: item
                };
            });
        } else {
            this.fieldsToMap = map(this.mapFields, (label, key) => {
                return {
                    key: key,
                    label: label
                };
            });
        }

        this.$root.$on('reset-csv-dialog', () => {
            this.reset();
        });

    },

    methods: {
        submit() {
            const _this = this;
            this.form.csv = this.buildMappedCsv();
            this.$emit('input', this.form.csv);
            _this.callback(this.form.csv);
        },
        buildMappedCsv() {
            const _this = this;

            let csv = this.hasHeaders ? drop(this.csv) : this.csv;

            const out = map(csv, (row) => {
                let newRow = {};

                forEach(_this.map, (column, field) => {
                    set(newRow, field, get(row, column));
                });

                return newRow;
            });

            return out;
        },
        downloadCSV() {
            const _this = this;
            this.downloadUrl((output) => {
                _this.sample = get(Papa.parse(output, { preview: 2, skipEmptyLines: true }), "data");
                _this.csv = get(Papa.parse(output, { skipEmptyLines: true }), "data");
            });
        },
        downloadUrl(callback) {
            if (this.link) {
                this.error = null;
                const _this = this;
                const _auth = axios.defaults.headers.common["Authorization"];
                delete axios.defaults.headers.common["Authorization"];
                axios.get(this.link).then(response => {
                    callback(response.data);
                }).catch((response) => {
                    _this.showError(response)
                    _this.catch(response);
                }).finally((response) => {
                    axios.defaults.headers.common["Authorization"] = _auth;
                    _this.finally(response);
                });
            }
        },
        reset() {
            this.form.csv = null;
            this.map = {};
            this.hasHeaders = false;
            this.csv = null;
            this.sample = null;
        },
        showError(error) {
            if (![200, 202, 203, 204].includes(error.response.status)) {
                this.error = 'Cannot download list from the provided URL.'
            }
        }
    },
    watch: {
        map: {
            deep: true,
            handler: function (newVal) {
                let hasAllKeys = Array.isArray(this.mapFields) ? every(this.mapFields, function (item) {
                    return newVal.hasOwnProperty(item);
                }) : every(this.mapFields, function (item, key) {
                    return newVal.hasOwnProperty(key);
                });

                if (hasAllKeys) {
                    this.submit();
                }
            }
        },
        sample(newVal) {
            if (this.autoMatchFields) {
                if (newVal !== null) {
                    this.fieldsToMap.forEach(field => {
                        newVal[0].forEach((columnName, index) => {
                            if (this.autoMatchIgnoreCase === true) {
                                if (field.label.toLowerCase().trim() === columnName.toLowerCase().trim()) {
                                    this.$set(this.map, field.key, index);
                                }
                            } else {
                                if (field.label.trim() === columnName.trim()) {
                                    this.$set(this.map, field.key, index);
                                }
                            }
                        });
                    });
                }
            }
        },
    },
    computed: {
        firstRow() {
            return get(this, "sample.0");
        },
        showErrorMessage() {
            return this.fileSelected && !this.isValidFileMimeType;
        },
        disableDownloadButton() {
            return false;
        },
        selectItems() {
            let out = [];
            for (const key in this.firstRow) {
                out.push({
                    'text': this.firstRow[key],
                    'value': key
                })
            }
            return out;
        }
    },
    mounted() {
    }
};
</script>
