<template>
    <div>
        <v-btn text small @click="show" :title="$t('report_item.tooltip.enum_selector')">
            <v-icon>mdi-feature-search-outline</v-icon>
        </v-btn>
        <v-row justify="center">
            <v-dialog v-model="visible" fullscreen hide-overlay transition="dialog-bottom-transition">
                <v-card>
                    <v-toolbar dark color="primary">

                        <v-btn icon dark @click="cancel">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title>{{$t('attribute.select_enum')}}</v-toolbar-title>
                    </v-toolbar>

                    <v-card>
                        <v-card-text>
                            <v-data-table
                                    :headers="headers"
                                    :items="attribute_enums"
                                    :server-items-length="attribute_enums_total_count"
                                    @update:options="updateOptions"
                                    :items-per-page="25"
                                    class="elevation-1 enum_selector"
                                    :page.sync="current_page"
                                    @click:row="clickRow"
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
                                    </v-toolbar>
                                </template>

                            </v-data-table>
                        </v-card-text>
                    </v-card>
                </v-card>
            </v-dialog>
        </v-row>
    </div>

</template>

<style>
    tbody tr {
        user-select: none !important;
        cursor: pointer;
    }
</style>

<script>
    import {getAttributeEnums} from "@/api/analyze";
    import {getCPEAttributeEnums} from "@/api/assets";

    export default {
        name: "EnumSelector",
        props: {
            attribute_id: Number,
            value_index: Number,
            cpe_only: Boolean
        },
        data: () => ({
            visible: false,
            search: "",
            headers: [
                {
                    text: 'Value',
                    align: 'left',
                    sortable: false,
                    value: 'value',
                },
                {text: 'Description', value: 'description', sortable: false},
            ],
            current_page: 1,
            current_page_size: 25,
            attribute_enums: [],
            attribute_enums_total_count: 0
        }),
        methods: {
            show() {
                this.updateAttributeEnums()
                this.visible = true;
            },

            cancel() {
                this.visible = false
            },

            filterSearch() {
                clearTimeout(this.timeout);

                let self = this
                this.timeout = setTimeout(function () {
                    self.current_page = 1
                    self.updateAttributeEnums()
                }, 300);
            },

            clickRow(event, row) {
                this.$emit('enum-selected', {index: this.value_index, value: row.item.value})
                this.visible = false
            },

            updateAttributeEnums() {
                if (this.cpe_only === true) {
                    getCPEAttributeEnums({
                        search: this.search,
                        offset: (this.current_page - 1) * this.current_page_size,
                        limit: this.current_page_size
                    }).then((response) => {
                        this.processResponse(response)
                    })
                } else {
                    getAttributeEnums({
                        attribute_id: this.attribute_id,
                        search: this.search,
                        offset: (this.current_page - 1) * this.current_page_size,
                        limit: this.current_page_size
                    }).then((response) => {
                        this.processResponse(response)
                    })
                }
            },

            processResponse(response) {
                this.attribute_enums = []
                this.attribute_enums_total_count = response.data.total_count
                for (let i = 0; i < response.data.items.length; i++) {
                    this.attribute_enums.push(response.data.items[i])
                }
            },

            updateOptions(options) {
                this.current_page = options.page
                this.current_page_size = options.itemsPerPage
                this.updateAttributeEnums()
            }
        }
    }
</script>
