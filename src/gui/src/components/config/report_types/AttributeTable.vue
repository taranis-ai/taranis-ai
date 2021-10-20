<template>
    <v-data-table
            :headers="headers"
            :items="attributes"
            sort-by="value"
            class="elevation-1"
    >
        <template v-slot:top>
            <v-toolbar flat color="white">
                <v-toolbar-title>{{$t('attribute.attributes')}}</v-toolbar-title>
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
                            <span>{{$t('attribute.new_attribute')}}</span>
                        </v-btn>
                    </template>
                    <v-card>
                        <v-card-title>
                            <span class="headline">{{ formTitle }}</span>
                        </v-card-title>

                        <v-card-text>

                            <v-combobox
                                    v-model="selected_attribute"
                                    :items="attribute_templates"
                                    item-text="name"
                                    :label="$t('attribute.attribute')"
                            ></v-combobox>

                            <v-text-field v-model="edited_attribute.title"
                                          :label="$t('attribute.name')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            ></v-text-field>

                            <v-text-field v-model="edited_attribute.description"
                                          :label="$t('attribute.description')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            ></v-text-field>

                            <v-row>
                                <v-col>
                                    <v-text-field v-model="edited_attribute.min_occurrence"
                                                  :label="$t('attribute.min_occurrence')"
                                                  :spellcheck="$store.state.settings.spellcheck"
                                    ></v-text-field>
                                </v-col>
                                <v-col>
                                    <v-text-field v-model="edited_attribute.max_occurrence"
                                                  :label="$t('attribute.max_occurrence')"
                                                  :spellcheck="$store.state.settings.spellcheck"
                                    ></v-text-field>
                                </v-col>
                            </v-row>

                        </v-card-text>

                        <v-card-actions>
                            <v-spacer></v-spacer>
                            <v-btn color="primary" dark @click="save">{{$t('attribute.save')}}</v-btn>
                            <v-btn color="primary" text @click="close">{{$t('attribute.cancel')}}</v-btn>
                        </v-card-actions>
                    </v-card>
                </v-dialog>
            </v-toolbar>
        </template>
        <template v-slot:item.action="{ item }">
            <v-icon v-if="!disabled"
                    small
                    class="mr-2"
                    @click="moveItemUp(item)"
            >
                mdi-arrow-up-bold
            </v-icon>
            <v-icon v-if="!disabled"
                    small
                    class="mr-2"
                    @click="moveItemDown(item)"
            >
                mdi-arrow-down-bold
            </v-icon>
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
    export default {
        name: "AttributeTable",
        props: {
            attributes: Array,
            attribute_templates: Array,
            disabled: Boolean
        },
        data: () => ({
            headers: [
                {text: 'Type', value: 'attribute_name', align: 'left', sortable: false},
                {text: 'Name', value: 'title', sortable: false},
                {text: 'Description', value: 'description', sortable: false},
                {text: 'Min Occurence', value: 'min_occurrence', sortable: false},
                {text: 'Max Occurence', value: 'max_occurrence', sortable: false},
                {text: 'Actions', value: 'action', align: 'right', sortable: false},
            ],
            dialog: false,
            selected_attribute: null,
            edited_index: -1,
            edited_attribute: {
                index: 0,
                id: -1,
                attribute_id: -1,
                attribute_name: "",
                title: "",
                description: "",
                min_occurrence: 0,
                max_occurrence: 1
            },
            default_attribute: {
                index: 0,
                id: -1,
                attribute_id: -1,
                attribute_name: "",
                title: "",
                description: "",
                min_occurrence: 0,
                max_occurrence: 1
            },
        }),
        computed: {
            formTitle() {
                return this.edited_index === -1 ? 'Add Attribute' : 'Edit Attribute'
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
                    this.edited_attribute = Object.assign({}, this.default_attribute);
                    this.edited_index = -1
                }, 300)
            },

            save() {
                this.edited_attribute.attribute_id = this.selected_attribute.id;
                this.edited_attribute.attribute_name = this.selected_attribute.name;
                if (this.edited_index > -1) {
                    Object.assign(this.attributes[this.edited_index], this.edited_attribute)
                } else {
                    this.attributes.push(this.edited_attribute)
                }
                this.selected_attribute = null;
                this.close()
            },

            editItem(item) {
                this.edited_index = this.attributes.indexOf(item);
                this.edited_attribute = Object.assign({}, item);
                this.dialog = true;
                for (const attribute_template of this.attribute_templates) {
                    if (attribute_template.id === this.edited_attribute.attribute_id) {
                        this.selected_attribute = attribute_template;
                        break;
                    }
                }
            },

            moveItemUp(item) {
                const index = this.attributes.indexOf(item);
                if (index > 0) {
                    this.attributes.splice(index-1, 0, this.attributes.splice(index, 1)[0]);
                }
            },

            moveItemDown(item) {
                const index = this.attributes.indexOf(item);
                if (index < this.attributes.length-1) {
                    this.attributes.splice(index+1, 0, this.attributes.splice(index, 1)[0]);
                }
            },

            deleteItem(item) {
                const index = this.attributes.indexOf(item);
                this.attributes.splice(index, 1)
            },
        }
    }
</script>
