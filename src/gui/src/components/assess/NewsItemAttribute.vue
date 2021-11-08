<template>
    <v-row>
        <v-col>
            <span style="margin-right:20px; font-size:12px">{{attribute.key}}</span>
            <br/>
            <span v-if="attribute.binary_mime_type === ''" style="font-size:16px">{{attribute.value}}</span>
            <v-row v-if="attribute.binary_mime_type !== ''">
                <v-col style="flex-grow: 0">
                    <v-icon>mdi-file-document</v-icon>
                </v-col>
                <v-col>
                    <div>{{attribute.value}}</div>
                </v-col>
                <v-col>
                    <v-btn small :href="getDownloadLink">{{$t('assess.download')}}
                        <v-icon right dark>mdi-cloud-download</v-icon>
                    </v-btn>
                </v-col>
            </v-row>
        </v-col>

    </v-row>
</template>

<script>
    export default {
        name: "NewsItemAttribute",
        props: {
            attribute: Object,
            news_item_data: Object
        },
        data: () => ({}),
        methods: {
            getDownloadLink() {
                return ((typeof(process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API)
                    + '/assess/news-item-data/' + this.news_item_data.id + '/attributes/' + this.attribute.id + '/file?jwt=' + this.$store.getters.getJWT
            }
        }
    }
</script>