<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilterAnalyze title='nav_menu.report_items' total_count_title="analyze.total_count"
                                  @update-report-items-filter="updateFilter"
                                  ref="toolbarFilter">
                <template v-slot:addbutton>
                    <NewReportItem add_button ref="reportItemDialog"/>
                </template>

            </ToolbarFilterAnalyze>
        </template>
        <template v-slot:content>
            <ContentDataAnalyze card-item="CardAnalyze" ref="contentData"
                                @show-report-item-detail="showReportItemDetail"
                                @show-remote-report-item-detail="showRemoteReportItemDetail"
                                @new-data-loaded="newDataLoaded"/>
            <NewProduct class="np" add_button/>
            <RemoteReportItem ref="remoteReportItemDialog"/>
        </template>
    </ViewLayout>

</template>

<script>
    import ViewLayout from "../../components/layouts/ViewLayout";
    import ToolbarFilterAnalyze from "@/components/analyze/ToolbarFilterAnalyze";
    import NewReportItem from "@/components/analyze/NewReportItem";
    import NewProduct from "@/components/publish/NewProduct";
    import ContentDataAnalyze from "../../components/analyze/ContentDataAnalyze";
    import {deleteReportItem} from "@/api/analyze";
    import RemoteReportItem from "@/components/analyze/RemoteReportItem";

    export default {
        name: "Analyze",
        components: {
            ViewLayout,
            ToolbarFilterAnalyze,
            ContentDataAnalyze,
            NewProduct,
            NewReportItem,
            RemoteReportItem
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
            showRemoteReportItemDetail(report_item) {
                this.$refs.remoteReportItemDialog.showDetail(report_item)
            },
        },
        computed: {},
        watch: {
            $route() {
                this.$refs.contentData.updateData(false, false);
            }
        },
        beforeCreate() {
            this.$root.$on('delete-report-item', (item) => {
                deleteReportItem(item).then(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'success',
                            loc: 'report_item.removed'
                        }
                    )
                }).catch(() => {
                    this.$root.$emit('notification',
                        {
                            type: 'error',
                            loc: 'report_item.removed_error'
                        }
                    )
                })
            });
        },
        mounted() {
            this.analyze_selector = true
        },
        beforeDestroy() {
            this.$root.$off('delete-report-item');
        }
    };
</script>