<template>

    <v-container id="selector">
        <component v-bind:is="cardLayout()" v-for="collection in collections" :card="collection" :key="collection.id"
                   :deletePermission="deletePermission"></component>
    </v-container>

</template>

<script>
    import CardNode from "../card/CardNode";
    import CardAssess from "../../assess/CardAssess";
    import CardCompact from "../card/CardCompact";
    import CardAnalyze from "@/components/analyze/CardAnalyze";
    import CardProduct from "@/components/publish/CardProduct";
    import CardPreset from "@/components/common/card/CardPreset";
    import CardProductType from "@/components/config/product_types/CardProductType";
    import CardUser from "@/components/config/user/CardUser";
    import CardSource from "@/components/config/osint_sources/CardSource";
    import CardGroup from "@/components/config/osint_sources/CardGroup";

    export default {
        name: "ContentData",
        components: {
            CardNode,
            CardAssess,
            CardCompact,
            CardAnalyze,
            CardProduct,
            CardPreset,
            CardProductType,
            CardUser,
            CardSource,
            CardGroup
        },
        props: {
            name: String,
            action: String,
            getter: String,
            cardItem: String,
            deletePermission: String
        },
        data: () => ({
            collections: [],
            filter: {
                search: "",
            },
        }),
        methods: {
            updateData() {
                this.$store.dispatch(this.action, this.filter)
                    .then(() => {
                        this.collections = this.$store.getters[this.getter].items
                    });
            },
            cardLayout: function () {

                return this.cardItem;
            }
        },
        mounted() {
            this.updateData();
            this.$root.$on('notification', () => {
                this.updateData()
            });
            this.$root.$on('update-data', () => {
                this.updateData()
            });
            this.$root.$on('update-items-filter', (filter) => {
                this.filter = filter;
                this.updateData()
            });
        },
        beforeDestroy() {
            this.$root.$off('notification')
            this.$root.$off('update-data')
            this.$root.$off('update-items-filter')
        }
    }
</script>
