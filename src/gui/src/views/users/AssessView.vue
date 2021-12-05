<template>
    <div>
        <ViewLayout>
            <template v-slot:panel>
                <ToolbarFilterAssess title='nav_menu.newsitems' total_count_title="assess.total_count"
                                     @update-news-items-filter="updateFilter"
                                     ref="toolbarFilter">
                    <template v-slot:addbutton>

                    </template>
                </ToolbarFilterAssess>
            </template>
            <template v-slot:content>
                <ContentDataAssess
                        card-item="CardAssess"
                        selfID="selector_assess"
                        data_set="assess"
                        ref="contentData"
                        @new-data-loaded="newDataLoaded"
                        @card-items-reindex="cardReindex"
                />
                <NewReportItem class="nri"/>
            </template>

        </ViewLayout>
    </div>

</template>

<script>
    import ViewLayout from "@/components/layouts/ViewLayout";
    import NewReportItem from "@/components/analyze/NewReportItem";
    import ToolbarFilterAssess from "@/components/assess/ToolbarFilterAssess";
    import ContentDataAssess from "@/components/assess/ContentDataAssess";

    import KeyboardMixin from "../../assets/keyboard_mixin";

    export default {
        name: "Assess",
        components: {
            ViewLayout,
            ToolbarFilterAssess,
            ContentDataAssess,
            NewReportItem
        },
        props: {
            analyze_selector: Boolean
        },
        data: () => ({
            dialog_stack: 0
        }),
        mixins: [KeyboardMixin('assess')],
        computed: {
            multiSelectActive() {
                return this.$store.getters.getMultiSelect;
            }
        },
        methods: {
            newDataLoaded(count) {
                this.$refs.toolbarFilter.updateDataCount(count)
            },

            updateFilter(filter) {
                this.$refs.contentData.updateFilter(filter)
                this.$store.dispatch("filter", filter)
            },

            cardReindex() {
                this.keyRemaper();

                // this scrolls the page all the way up... it should only scroll to the top of the newly-loaded items
                // setTimeout( ()=>{
                //     this.scrollPos();
                // },1 )

                if(this.focus) {
                    this.$refs.contentData.checkFocus(this.pos);
                }
            },

            firstDialog(action) {
                if(action == 'push') {
                    this.dialog_stack++;
                } else {
                    this.dialog_stack--;
                }
                if(this.dialog_stack <= 0) {
                    this.isItemOpen = false;
                    this.dialog_stack = 0;
                } else {
                    this.isItemOpen = true;
                }
            }
        },
        watch: {
            $route() {
                this.$refs.contentData.updateData(false, false);
            }
        },
        mounted() {
            if (window.location.pathname.includes("/group/")) {
                this.$refs.contentData.updateData(false, false);
            }

            this.$root.$on('first-dialog', (action) => {
                this.firstDialog(action);
            });

            this.$root.$on('clear-cards', () => {
                const cards = document.querySelectorAll('.card-item');
                cards.forEach(card => card.remove());
            });

        },
        created() {
            document.addEventListener("keydown", this.keyAction, false);
            const element = document.querySelector("card-item");
            element.addEventListener('click', this.targetClick, false);
        },
        beforeDestroy() {
            document.removeEventListener("keydown", this.keyAction);
            const element = document.querySelector("card-item");
            element.removeEventListener('click');
            this.$root.$off('first-dialog');
            this.$root.$off('clear-cards');
        }
    };
</script>