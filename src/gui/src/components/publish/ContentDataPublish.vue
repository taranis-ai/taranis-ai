<template>

    <v-container id="selector_publish">
        <CardProduct v-for="collection in collections" :card="collection" :key="collection.id"></CardProduct>
        <v-card v-intersect.quiet="infiniteScrolling"></v-card>
    </v-container>

</template>

<style>
    html {
        scroll-behavior: smooth;
    }
    #selector_publish .card-assess {
        transition: background-color 1s;
    }
    #selector_publish .focus.in_progress {
        box-shadow: inset 0 0 0 3px #ffd556;
        background-color: rgba(255, 213, 86, 0.3);
    }
    #selector_publish .focus.read {
        box-shadow: inset 0 0 0 3px #33DD40;
        background-color: rgba(0, 128, 0, 0.3);
    }
    #selector_publish .focus.important {
        box-shadow: inset 0 0 0 3px red;
        background-color: rgba(255, 0, 0, 0.3);
    }
</style>

<script>
    import CardProduct from "./CardProduct";

    export default {
        name: "ContentDataPublish",
        components: {
            CardProduct,
        },
        data: () => ({
            collections: [],
            data_loaded: false,
            filter: {
                search: "",
                range: "ALL",
                sort: "DATE_DESC"
            }
        }),
        methods: {
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
                this.$store.dispatch("getAllProducts", {filter: this.filter, offset:offset, limit:limit})
                    .then(() => {
                        this.collections = this.collections.concat(this.$store.getters.getProducts.items);
                        setTimeout(() => {
                            this.data_loaded = true
                        }, 1000);
                    });
            }
        },
        watch: {
            $route() {
                this.updateData(false, false);
            }
        },
        mounted() {
            this.updateData();
            this.$root.$on('notification', () => {
                this.updateData(true, true)
            });
            this.$root.$on('update-products-filter', (filter) => {
                this.filter = filter;
                this.updateData(false, false)
            });
        },
        created() {
        },
        beforeDestroy() {
        }
    }
</script>
