<template>
    <ViewLayout>
        <template v-slot:panel>
            <ToolbarFilter title='nav_menu.notification_templates' total_count_title="notification_template.total_count"
                           total_count_getter="getNotificationTemplates">
                <template v-slot:addbutton>
                    <NewNotificationTemplate/>
                </template>
            </ToolbarFilter>

        </template>
        <template v-slot:content>
            <ContentData
                    name="NotificationTemplates"
                    cardItem="CardPreset"
                    action="getAllNotificationTemplates"
                    getter="getNotificationTemplates"
                    deletePermission="MY_ASSETS_CONFIG"
            />
        </template>
    </ViewLayout>
</template>

<script>
    import ViewLayout from "../../components/layouts/ViewLayout";
    import NewNotificationTemplate from "@/components/config/assets/NewNotificationTemplate";
    import ToolbarFilter from "../../components/common/ToolbarFilter";
    import ContentData from "../../components/common/content/ContentData"
    import {deleteNotificationTemplate} from "@/api/assets";

    export default {
        name: "NotificationTemplates",
        components: {
            ViewLayout,
            ToolbarFilter,
            ContentData,
            NewNotificationTemplate
        },
        data: () => ({}),
        mounted() {
            this.$root.$on('delete-item', (item) => {
                deleteNotificationTemplate(item).then(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'success',
                            loc: 'notification_template.removed'
                        }
                    )
                }).catch(() => {

                    this.$root.$emit('notification',
                        {
                            type: 'error',
                            loc: 'notification_template.removed_error'
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