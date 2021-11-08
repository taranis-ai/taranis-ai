<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.osint_sources' total_count_title="osint_source.total_count"
                           total_count_getter="getOSINTSources">
                <template v-slot:addbutton>
                    <NewOSINTSource/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "OSINTSources"
                    cardItem="CardSource"
                    action="getAllOSINTSources"
                    getter="getOSINTSources"
                    deletePermission="CONFIG_OSINT_SOURCE_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
    import ViewLayout from "../../components/layouts/ViewLayout";
    import NewOSINTSource from "../../components/config/osint_sources/NewOSINTSource";
    import ToolbarFilter from "../../components/common/ToolbarFilterOSINTSource";
    import ContentData from "../../components/common/content/ContentData"
    import {deleteOSINTSource} from "@/api/config";

    export default {
        name: "OSINTSources",
        components: {
            ViewLayout,
            ToolbarFilter,
            ContentData,
            NewOSINTSource
        },
        data: () => ({
        }),
        mounted() {
            this.$root.$on('delete-item', (item) => {
                deleteOSINTSource(item).then(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'success',
                            loc: 'osint_source.removed'
                        }
                    )
                }).catch(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'error',
                            loc: 'osint_source.removed_error'
                        }
                    )
                })
            });
        },
        beforeDestroy() {
            this.$root.$off('delete-item')
        }
    };

</script>