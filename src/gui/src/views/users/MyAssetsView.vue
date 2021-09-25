<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilterAssets title='main_menu.my_assets' total_count_title="asset.total_count">
                <template v-slot:addbutton>
                    <NewAsset/>
                </template>
            </ToolbarFilterAssets>
        </template>
        <template v-slot:content>
            <ContentDataAssets cardItem="CardAsset"/>
            <VulnerabilityDetail/>
        </template>
    </ViewLayout>

</template>

<style>
    .np {
        display: none;
    }
</style>

<script>
    import ViewLayout from "../../components/layouts/ViewLayout";
    import {deleteAsset} from "@/api/assets";
    import ToolbarFilterAssets from "@/components/assets/ToolbarFilterAssets";
    import ContentDataAssets from "@/components/assets/ContentDataAssets";
    import NewAsset from "@/components/assets/NewAsset";
    import VulnerabilityDetail from "@/components/assets/VulnerabilityDetail";

    export default {
        name: "MyAssets",
        components: {
            ViewLayout,
            ToolbarFilterAssets,
            ContentDataAssets,
            NewAsset,
            VulnerabilityDetail
        },
        mounted() {
            this.$root.$on('delete-asset', (item) => {
                deleteAsset(item).then(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'success',
                            loc: 'asset.removed'
                        }
                    )
                }).catch(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'error',
                            loc: 'asset.removed_error'
                        }
                    )
                })
            });
        }
    };
</script>