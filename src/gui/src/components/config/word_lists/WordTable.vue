<template>
    <v-data-table
            :headers="headers"
            :items="words"
            sort-by="value"
            class="elevation-1"
    >
        <template v-slot:top>
            <v-toolbar flat color="white">
                <v-toolbar-title>{{$t('word_list.words')}}</v-toolbar-title>
                <v-divider
                        class="mx-4"
                        inset
                        vertical
                ></v-divider>
                <v-spacer></v-spacer>
                <v-dialog v-if="!disabled" v-model="dialog" max-width="500px">
                    <template v-slot:activator="{ on }">
                        <v-btn color="primary" dark class="mb-2" v-on="on">
                            <v-icon left>mdi-plus</v-icon>
                            <span>{{$t('word_list.new_word')}}</span>
                        </v-btn>
                    </template>
                    <v-card>
                        <v-card-title>
                            <span class="headline">{{ formTitle }}</span>
                        </v-card-title>

                        <v-card-text>

                            <v-text-field v-model="edited_word.value"
                                          :label="$t('word_list.value')"
                                          :spellcheck="$store.state.settings.spellcheck"></v-text-field>

                            <v-text-field v-model="edited_word.description"
                                          :label="$t('word_list.description')"
                                          :spellcheck="$store.state.settings.spellcheck"></v-text-field>

                        </v-card-text>

                        <v-card-actions>
                            <v-spacer></v-spacer>
                            <v-btn color="primary" dark @click="save">{{$t('word_list.save')}}</v-btn>
                            <v-btn color="primary" text @click="close">{{$t('word_list.cancel')}}</v-btn>
                        </v-card-actions>
                    </v-card>
                </v-dialog>

                <v-dialog v-if="!disabled" v-model="dialog_csv" max-width="700px">
                    <template v-slot:activator="{ on }">
                        <v-btn color="primary" dark class="mb-2 ml-2" v-on="on">
                            <v-icon left>mdi-upload</v-icon>
                            <span>{{$t('word_list.import_from_csv')}}</span>
                        </v-btn>
                    </template>
                    <v-card>
                        <v-card-title>
                            <span class="headline">{{$t('word_list.import_from_csv')}}</span>
                        </v-card-title>

                        <v-row class="ma-6">
                            <VueCsvImport v-model="csv" :map-fields="['value', 'description']">

                                <template slot="hasHeaders" slot-scope="{headers, toggle}">
                                    <label>
                                        <input type="checkbox" id="hasHeaders" :value="headers" @change="toggle">
                                        {{$t('word_list.file_has_header')}}
                                    </label>
                                </template>

                                <template slot="next" slot-scope="{load}">
                                    <button class="load" @click.prevent="load">{{$t('word_list.load_csv_file')}}</button>
                                </template>

                            </VueCsvImport>
                        </v-row>

                        <div v-if="csv_preview" class="mt-2 px-4">
                            <v-row class="pa-0 ma-0 grey white--text">
                                <v-col class="pa-0 ma-0">
                                    <span class="heading">Value</span>
                                </v-col>
                                <v-col class="pa-0 ma-0">
                                    <span class="heading">Description</span>
                                </v-col>
                            </v-row>

                            <v-card-text class="ma-0 pa-0" v-for="parse in csv" :key="parse.value">

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
                            <v-checkbox v-model="csv_delete_exist_list" label="Delete existing Attribute values"></v-checkbox>
                            <v-spacer></v-spacer>
                            <v-btn color="primary" dark @click="importCSV">
                                {{$t('word_list.import')}}
                            </v-btn>
                            <v-btn color="primary" text @click="closeCSV">
                                {{$t('word_list.cancel')}}
                            </v-btn>
                        </v-card-actions>
                    </v-card>
                </v-dialog>
            </v-toolbar>
        </template>
        <template v-slot:item.action="{ item }">
            <v-icon v-if="!disabled"
                    small
                    class="mr-2"
                    @click="editItem(item)"
            >
                edit
            </v-icon>
            <v-icon v-if="!disabled"
                    small
                    @click="deleteItem(item)"
            >
                delete
            </v-icon>
        </template>
    </v-data-table>
</template>

<script>
    import VueCsvImport from '@/components/common/ImportCSV';

    export default {

        name: "WordTable",
        components: {
            VueCsvImport
        },
        props: {
            words: Array,
            id: null,
            word_templates: Array,
            disabled: Boolean
        },
        data: () => ({
            csv: null,
            csv_delete_exist_list: false,
            csv_preview: false,
            headers: [
                {text: 'Value', value: 'value', align: 'left', sortable: true},
                {text: 'Description', value: 'description', sortable: false},
                {text: 'Actions', value: 'action', align: 'right', sortable: false},
            ],
            dialog: false,
            dialog_csv: false,
            selected_word: null,
            edited_index: -1,
            edited_word: {
                value: "",
                description: "",
            },
            default_word: {
                value: "",
                description: "",
            },
        }),
        computed: {
            formTitle() {
                return this.edited_index === -1 ? 'Add Word' : 'Edit Word'
            }
        },
        watch: {
            dialog(val) {
                val || this.close()
            },
        },
        methods: {
            close() {
                this.dialog = false;
                setTimeout(() => {
                    this.edited_word = Object.assign({}, this.default_word);
                    this.edited_index = -1
                }, 300)
            },

            save() {
                if (this.edited_index > -1) {
                    Object.assign(this.words[this.edited_index], this.edited_word)
                } else {
                    this.words.push(this.edited_word)
                }
                this.selected_word = null;
                this.close()
            },

            importCSV() {

                if(this.csv_delete_exist_list) {
                    this.$emit('update-categories', {'entries':this.csv, 'index':this.id} );
                } else {

                    let arrayWithDuplicates = this.words.concat(this.csv);

                    let removeDuplicates = function(originalArray, prop) {
                        let newArray = [];
                        let lookupObject  = {};

                        for(var i in originalArray) {
                            lookupObject[originalArray[i][prop]] = originalArray[i];
                        }

                        for(i in lookupObject) {
                            newArray.push(lookupObject[i]);
                        }

                        return newArray;
                    }

                    let uniqueArray = removeDuplicates(arrayWithDuplicates, "value");
                    this.$emit('update-categories', {'entries':uniqueArray, 'index':this.id} );
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
                this.edited_index = this.words.indexOf(item);
                this.edited_word = Object.assign({}, item);
                this.dialog = true;
            },

            moveItemUp(item) {
                const index = this.words.indexOf(item);
                if (index > 0) {
                    this.words.splice(index-1, 0, this.words.splice(index, 1)[0]);
                }
            },

            moveItemDown(item) {
                const index = this.words.indexOf(item);
                if (index < this.words.length-1) {
                    this.words.splice(index+1, 0, this.words.splice(index, 1)[0]);
                }
            },

            deleteItem(item) {
                const index = this.words.indexOf(item);
                this.words.splice(index, 1)
            },
        }
    }
</script>