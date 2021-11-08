<template>

    <v-container class="selector_assess" :id="selfID">
        <component v-bind:is="cardLayout()" v-for="(news_item,i) in news_items_data" :card="news_item"
                   :key="i" :analyze_selector="analyze_selector"
                   :preselected="preselected(news_item.id)"
                   :word_list_regex="regexWordList" :data_set="data_set"
                   @show-single-aggregate-detail="showSingleAggregateDetail(news_item)"
                   @show-aggregate-detail="showAggregateDetail(news_item)"
                   @show-item-detail="showItemDetail"
                   @aggregate-open="setAggregateOpen"
                   ref="card"
                   :aggregate_opened="aggregateOpen(news_item)"
                   @check-focus="checkFocus"
        >
        </component>
        <v-card v-intersect.quiet="infiniteScrolling"></v-card>
        <NewsItemSingleDetail ref="newsItemSingleDetail"/>
        <NewsItemDetail ref="newsItemDetail"/>
        <NewsItemAggregateDetail ref="newsItemAggregateDetail"/>
    </v-container>

</template>

<script>
    import CardAssess from "./CardAssess";
    import NewsItemSingleDetail from "@/components/assess/NewsItemSingleDetail";
    import NewsItemDetail from "@/components/assess/NewsItemDetail";
    import NewsItemAggregateDetail from "@/components/assess/NewsItemAggregateDetail";

    export default {
        name: "ContentDataAssess",
        components: {
            CardAssess,
            NewsItemSingleDetail,
            NewsItemDetail,
            NewsItemAggregateDetail,
        },
        props: {
            analyze_selector: Boolean,
            selection: Array,
            cardItem: String,
            selfID: String,
            data_set: String
        },
        data: () => ({
            news_items_data: [],
            news_items_data_loaded: false,
            news_items_filter: {
                search: "",
                range: "ALL",
                read: false,
                important: false,
                relevant: false,
                in_analyze: false,
                sort: "DATE_DESC"
            },
            aggregate_open: []
        }),
        methods: {
            cardLayout: function () {
                return this.cardItem;
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

            infiniteScrolling(entries, observer, isIntersecting) {

                if (this.news_items_data_loaded && isIntersecting) {
                    this.updateData(true, false)
                }
            },

            showSingleAggregateDetail(news_item) {
                this.$root.$emit('change-state','SHOW_ITEM');
                this.$refs.newsItemSingleDetail.open(news_item)
            },

            showAggregateDetail(news_item) {
                this.$root.$emit('change-state','SHOW_ITEM');
                this.$refs.newsItemAggregateDetail.open(news_item)
            },

            showItemDetail(news_item) {
                this.$root.$emit('change-state','SHOW_ITEM');
                this.$refs.newsItemDetail.open(news_item)
            },

            updateData(append, reload_all) {

                this.news_items_data_loaded = false;

                if (append === false) {
                    this.news_items_data = []
                }

                let offset = this.news_items_data.length;
                let limit = 20;
                if (reload_all) {
                    offset = 0;
                    if (this.news_items_data.length > limit) {
                        limit = this.news_items_data.length;
                    }
                    this.news_items_data = []
                }

                let group = '';

                if (this.analyze_selector) {
                    group = this.$store.getters.getCurrentGroup
                } else {
                    if (window.location.pathname.includes("/group/")) {

                        let i = window.location.pathname.indexOf("/group/");
                        let len = window.location.pathname.length;
                        group = window.location.pathname.substring(i + 7, len);
                        this.$store.dispatch("changeCurrentGroup", group);
                    }
                }

                this.$store.dispatch("getNewsItemsByGroup", {
                    group_id: group,
                    data: {
                        filter: this.news_items_filter,
                        offset: offset,
                        limit: limit
                    }
                }).then(() => {
                    this.news_items_data = this.news_items_data.concat(this.$store.getters.getNewsItems.items);
                    this.$emit('new-data-loaded', this.$store.getters.getNewsItems.total_count);
                    setTimeout( () => {
                        this.$emit('card-items-reindex');
                    },200);
                    setTimeout(() => {
                        this.news_items_data_loaded = true;
                    }, 1000);
                });
            },

            updateFilter(filter) {
                this.news_items_filter = filter;
                this.updateData(false, false);
            },

            setAggregateOpen(folder) {

                if( !this.aggregate_open.length ) {
                    this.aggregate_open.push(folder.id);
                } else if( folder.opened === false ) {
                    let close = this.aggregate_open.indexOf(folder.id);
                    this.aggregate_open.splice(close, 1);
                } else {
                    this.aggregate_open.push(folder.id);
                }
            },

            checkFocus(pos) {
                this.$root.$emit('check-focus', pos);
            },

            news_items_updated() {
                // only update items when not in selection mode
                if (! this.multiSelectActive) {
                    this.updateData(false, true);
                }
            },

            aggregateOpen(folder) {

                for( let i=0; i<this.aggregate_open.length; i++) {
                    if( this.aggregate_open[i] == folder.id && folder.news_items.length !== 1) {
                        return true;
                    }
                }
                return false;
            },

            forceReindex() {
                this.$emit('card-items-reindex');
            }
        },

        computed: {
            multiSelectActive() {
                return this.$store.getters.getMultiSelect;
            },

            regexWordList() {

                let wordsData = this.$store.getters.getProfileWordLists;
                let wordListRegex = [];
                let chop;

                if ( wordsData.length ) {
                    for (let i = 0; i < wordsData.length; i++) {
                        for (let j = 0; j < wordsData[i].categories.length; j++) {
                            wordsData[i].categories[j].entries.forEach(t => {
                                wordListRegex.push(t.value + "|");
                            });
                        }
                    }

                    chop = wordListRegex.join('');
                    wordListRegex = chop.substring(0, chop.length - 1);
                } else {
                    wordListRegex = null;
                }

                return wordListRegex;
            }
        },

        mounted() {
            this.$root.$on('news-items-updated', this.news_items_updated);
            this.$root.$on('force-reindex', this.forceReindex);
        },

        beforeDestroy() {
            this.$root.$off('news-items-updated', this.news_items_updated);
        }
    }
</script>