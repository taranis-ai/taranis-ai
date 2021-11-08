<template>

    <v-container id="selector_analyze">
        <component v-bind:is="cardLayout()" v-for="collection in collections" :card="collection" :key="collection.id"
                   :publish_selector="publish_selector" :preselected="preselected(collection.id)"
                   @show-report-item-detail="showReportItemDetail"
                   @show-remote-report-item-detail="showRemoteReportItemDetail"
                   @remove-report-item-from-selector="removeReportItemFromSelector"></component>
        <v-card v-intersect.quiet="infiniteScrolling"></v-card>
    </v-container>

</template>

<script>
    import CardAnalyze from "./CardAnalyze";

    export default {
        name: "ContentDataAnalyze",
        components: {
            CardAnalyze,
        },
        props: {
            publish_selector: Boolean,
            selection: Array,
            cardItem: String
        },
        data: () => ({
            collections: [],
            data_loaded: false,
            filter: {
                search: "",
                range: "ALL",
                completed: false,
                incompleted: false,
                sort: "DATE_DESC"
            }
        }),
        methods: {
            showReportItemDetail(report_item){
                this.$emit('show-report-item-detail', report_item)
            },
            showRemoteReportItemDetail(report_item){
                this.$emit('show-remote-report-item-detail', report_item)
            },
            removeReportItemFromSelector(report_item){
                this.$emit('remove-report-item-from-selector', report_item)
            },
            preselected(item_id) {
                if (this.selection != null) {

                    for (let i = 0; i < this.selection.length; i++) {
                        if (this.selection[i].id === item_id) {
                            return true
                        }
                    }
                }
                return false
            },

            cardLayout: function () {

                return this.cardItem;
            },

            infiniteScrolling(entries, observer, isIntersecting) {

                if (this.data_loaded && isIntersecting) {
                    this.updateData(true, false)
                }
            },

            updateData(append, reload_all) {

                this.data_loaded = false;

                if (append === false) {
                    this.collections = []
                }

                let offset = this.collections.length;
                let limit = 20;
                if (reload_all) {
                    offset = 0;
                    if (this.collections.length > limit) {
                        limit = this.collections.length;
                    }
                    this.collections = []
                }

                let group = ''
                if (this.publish_selector) {

                    group = this.$store.getters.getCurrentReportItemGroup

                } else if (window.location.pathname.includes("/group/")) {

                    let i = window.location.pathname.indexOf("/group/");
                    let len = window.location.pathname.length;
                    group = window.location.pathname.substring(i + 7, len).replaceAll("-", " ");
                }

                this.$store.dispatch("getAllReportItems", {group: group, filter: this.filter, offset: offset, limit: limit})
                    .then(() => {
                        this.collections = this.collections.concat(this.$store.getters.getReportItems.items);
                        this.$emit('new-data-loaded', this.collections.length);
                        setTimeout(() => {
                            this.data_loaded = true
                        }, 1000);
                    });
            },

            report_item_updated() {
                this.updateData(false, true)
            },

            updateFilter(filter) {
                this.filter = filter;
                this.updateData(false, false);
            },
        },
        computed: {
            multiSelectActive() {
                return this.$store.getters.getMultiSelect;
            }
        },

        mounted() {
            this.updateData(false, false);

            this.$root.$on('report-item-updated', this.report_item_updated);
            this.$root.$on('report-items-updated', this.report_item_updated);
        },
        created() {},
        beforeDestroy() {
            this.$root.$off('report-item-updated', this.report_item_updated);
            this.$root.$off('report-items-updated', this.report_item_updated);
        }
    }
</script>