<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.asset_groups' total_count_title="asset_group.total_count"
                           total_count_getter="getAssetGroups">
                <template v-slot:addbutton>
                    <NewAssetGroup/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="AssetGroups"
                    cardItem="CardPreset"
                    action="getAllAssetGroups"
                    getter="getAssetGroups"
                    deletePermission="MY_ASSETS_CONFIG"
            />
        </template>
    </ViewLayout>
</template>

<script>
    import ViewLayout from "../../components/layouts/ViewLayout";
    import NewAssetGroup from "@/components/config/assets/NewAssetGroup";
    import ToolbarFilter from "../../components/common/ToolbarFilter";
    import ContentData from "../../components/common/content/ContentData"
    import {deleteAssetGroup} from "@/api/assets";

    export default {
        name: "AssetGroups",
        components: {
            ViewLayout,
            ToolbarFilter,
            ContentData,
            NewAssetGroup
        },
        data: () => ({}),
        mounted() {
            this.$root.$on('delete-item', (item) => {
                deleteAssetGroup(item).then(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'success',
                            loc: 'asset_group.removed'
                        }
                    )
                }).catch(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'error',
                            loc: 'asset_group.removed_error'
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