<template>
    <div>
        <v-btn v-if="canModify" depressed small @click="openSelector">
            <v-icon left>mdi-plus</v-icon>
            <span>{{$t('report_item.select')}}</span>
        </v-btn>

        <v-row>
            <div class="pt-2"></div>
        </v-row>

        <v-row justify="center">
            <v-dialog v-model="dialog" fullscreen hide-overlay transition="dialog-bottom-transition">

                <v-card fixed>
                    <v-toolbar dark color="primary" style="z-index: 10000">
                        <v-btn icon dark @click="close">
                            <v-icon>mdi-close-circle</v-icon>
                        </v-btn>
                        <v-toolbar-title>{{$t('report_item.select')}}</v-toolbar-title>
                        <v-spacer></v-spacer>
                        <v-btn text dark @click="add">
                            <v-icon left>mdi-plus-box</v-icon>
                            <span>{{$t('report_item.add')}}</span>
                        </v-btn>
                    </v-toolbar>

                    <v-row class="cs-inside">
                        <v-col class="cs-content-full">
                            <ToolbarFilterAnalyze publish_selector
                                                  total_count_title="analyze.total_count"
                                                  @update-report-items-filter="updateFilter"
                                                  ref="toolbarFilter"></ToolbarFilterAnalyze>
                            <ContentDataAnalyze publish_selector :selection="values"
                                                class="item-selector" card-item="CardAnalyze"
                                                ref="contentData"
                                                @show-report-item-detail="showReportItemDetail"
                                                @new-data-loaded="newDataLoaded"/>

                        </v-col>
                    </v-row>

                </v-card>
            </v-dialog>
        </v-row>

        <v-spacer style="height:8px"></v-spacer>

        <NewReportItem ref="reportItemDialog"/>

        <component publish_selector class="item-selector ml-4" v-bind:is="cardLayout()" v-for="value in values" :card="value"
                   :key="value.id"
                   @show-report-item-detail="showReportItemDetail"
                   @remove-report-item-from-selector="removeReportItemFromSelector"></component>

    </div>
</template>

<script>
    import ContentDataAnalyze from "@/components/analyze/ContentDataAnalyze";
    import ToolbarFilter from "@/components/common/ToolbarFilter";
    import CardAnalyze from "../analyze/CardAnalyze";
    import ToolbarFilterAnalyze from "@/components/analyze/ToolbarFilterAnalyze";
    import NewReportItem from "@/components/analyze/NewReportItem";
    import Permissions from "@/services/auth/permissions";
    import AuthMixin from "@/services/auth/auth_mixin";

    export default {
        name: "ReportItemSelector",
        components: {
            ToolbarFilterAnalyze,
            ContentDataAnalyze,
            ToolbarFilter,
            CardAnalyze,
            NewReportItem
        },
        mixins: [AuthMixin],
        props: {
            values: Array,
            modify: Boolean,
            edit: Boolean
        },
        data: () => ({
            dialog: false,
            value: ""
        }),
        computed: {
            canModify() {
                return this.edit === false || (this.checkPermission(Permissions.PUBLISH_UPDATE) && this.modify === true)
            }
        },
        methods: {
            newDataLoaded(count) {
                this.$refs.toolbarFilter.updateDataCount(count)
            },

            updateFilter(filter) {
                this.$refs.contentData.updateFilter(filter)
            },

            showReportItemDetail(report_item) {
                this.$refs.reportItemDialog.showDetail(report_item)
            },

            removeReportItemFromSelector(report_item) {
                const i = this.values.indexOf(report_item)
                this.values.splice(i, 1)
            },

            cardLayout: function () {
                return "CardAnalyze";
            },

            openSelector() {
                this.$store.dispatch("multiSelectReport", true)
                this.dialog = true;
            },

            add() {
                let selection = this.$store.getters.getSelectionReport
                for (let i = 0; i < selection.length; i++) {
                    let found = false
                    for (let j = 0; j < this.values.length; j++) {
                        if (this.values[j].id === selection[i].item.id) {
                            found = true
                            break
                        }
                    }

                    if (found === false)
                        selection[i].item.tag = 'mdi-file-table-outline'
                        this.values.push(selection[i].item)
                }

                this.close()
            },

            close() {
                this.$store.dispatch("multiSelectReport", false)
                this.dialog = false;
            }
        }
    }
</script>

<style>
    .container.item-selector,
    .item-selector .row {
        margin-right: 0;
        margin-left: 0;
    }

    .toolbar-filter .row1 .view-heading {
        height: 40px;
    }

    .cs-inside .cs-content-full {
        position: relative;
        padding: 0;
    }

    .cs-inside .cs-content-full {
        width: 100%;
        margin-left: 0px;
    }
</style>