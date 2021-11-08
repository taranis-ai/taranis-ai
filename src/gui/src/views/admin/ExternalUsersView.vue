<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.users' total_count_title="user.total_count"
                           total_count_getter="getUsers">
                <template v-slot:addbutton>
                    <NewExternalUser/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name = "ExternalUsers"
                    cardItem="CardUser"
                    action="getAllExternalUsers"
                    getter="getUsers"
                    deletePermission="MY_ASSETS_CONFIG"
            />
        </template>
    </ViewLayout>
</template>

<script>
    import ViewLayout from "../../components/layouts/ViewLayout";
    import NewExternalUser from "@/components/config/user/NewExternalUser";
    import ToolbarFilter from "../../components/common/ToolbarFilter";
    import ContentData from "../../components/common/content/ContentData"
    import {deleteExternalUser} from "@/api/config";

    export default {
        name: "ExternalUsersView",
        components: {
            ViewLayout,
            ToolbarFilter,
            ContentData,
            NewExternalUser
        },
        data: () => ({
        }),
        mounted() {
            this.$root.$on('delete-item', (item) => {
                deleteExternalUser(item).then(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'success',
                            loc: 'user.removed'
                        }
                    )
                }).catch(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'error',
                            loc: 'user.removed_error'
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