<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.osint_source_groups' total_count_title="osint_source_group.total_count"
                           total_count_getter="getOSINTSourceGroups">
                <template v-slot:addbutton>
                    <NewOSINTSourceGroup/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="OSINTSourceGroups"
                    cardItem="CardGroup"
                    action="getAllOSINTSourceGroups"
                    getter="getOSINTSourceGroups"
                    deletePermission="CONFIG_OSINT_SOURCE_GROUP_DELETE"
            />
        </template>
    </ViewLayout>
</template>

<script>
    import ViewLayout from "../../components/layouts/ViewLayout";
    import NewOSINTSourceGroup from "../../components/config/osint_sources/NewOSINTSourceGroup";
    import ToolbarFilter from "../../components/common/ToolbarFilter";
    import ContentData from "../../components/common/content/ContentData"
    import {deleteOSINTSourceGroup} from "@/api/config";

    export default {
        name: "OSINTSourceGroups",
        components: {
            ViewLayout,
            ToolbarFilter,
            ContentData,
            NewOSINTSourceGroup
        },
        data: () => ({}),
        mounted() {
            this.$root.$on('delete-item', (item) => {
                deleteOSINTSourceGroup(item).then(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'success',
                            loc: 'osint_source_group.removed'
                        }
                    )
                }).catch(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'error',
                            loc: 'osint_source_group.removed_error'
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