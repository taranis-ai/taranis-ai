# API contract review

The 510 Core application operations below have executable request, path, query, application-header and response contracts. Both configuration aliases and public reports are included. Authentication executes before request validation; the response boundary also validates authentication failures. Framework HEAD uses GET contracts; generated OPTIONS and Flask static files are explicit framework exclusions. Downloads validate metadata without consuming file iterators. Historical revision snapshots and provider parameter maps remain intentional extension maps.

Regenerate this table and OpenAPI after route changes with `cd src/core && uv run python ../../dev/update_api_contracts.py`. The mandatory route test checks completeness, handler wiring and resolvable schemas under both application prefixes.

| Operation | Endpoint | Request body | Query | Path | Application headers | Explicit responses | OpenAPI | Boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `DELETE /admin/acls/{acl_id}` | `admin.admin_acl` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/acls` | `admin.admin_acls` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /admin/attributes/{attribute_id}` | `admin.admin_attribute` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/attributes` | `admin.admin_attributes` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /admin/bots/{bot_id}` | `admin.admin_bot_config` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/connectors/{connector_id}` | `admin.admin_connector` | none | ListQuery | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `DELETE /admin/organizations/{organization_id}` | `admin.admin_organization` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/organizations` | `admin.admin_organizations` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /admin/osint-source-groups/{group_id}` | `admin.admin_osint_source_group` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/osint-source-groups` | `admin.admin_osint_source_groups_config` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /admin/osint-sources/{source_id}` | `admin.admin_osint_source` | none | SourceDeleteQuery | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `DELETE /admin/osint-sources` | `admin.admin_osint_sources` | none | SourceDeleteQuery | EmptyParameters | EmptyParameters | 200: SourceDeleteResponse | yes | enforced |
| `DELETE /admin/product-types/{type_id}` | `admin.admin_product_type` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/publisher-presets/{preset_id}` | `admin.admin_publisher_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/publishers-presets/{preset_id}` | `admin.admin_publishers_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/report-item-types/{type_id}` | `admin.admin_report_item_type` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/report-item-types` | `admin.admin_report_item_types` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /admin/roles/{role_id}` | `admin.admin_role` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/roles` | `admin.admin_roles` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /admin/sources/{source_id}` | `admin.admin_source` | none | SourceDeleteQuery | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `DELETE /admin/templates/{template_path}` | `admin.admin_template` | none | EmptyParameters | PathParameters | EmptyParameters | 200: TemplateDeleteResponse | yes | enforced |
| `DELETE /admin/templates` | `admin.admin_templates` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: TemplateDeleteResponse | yes | enforced |
| `DELETE /admin/users/{user_id}` | `admin.admin_user` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/users` | `admin.admin_users` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /admin/word-lists/{word_list_id}` | `admin.admin_word_list` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /admin/word-lists` | `admin.admin_word_lists` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /analyze/report-items/{report_item_id}/lock` | `analyze.report_item_lock` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ReportLock | yes | enforced |
| `DELETE /analyze/report-items/{report_item_id}` | `analyze.report_item` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /analyze/report-items` | `analyze.report_items` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /analyze/report/{report_item_id}` | `analyze.report` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /analyze/reports` | `analyze.reports` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /assess/bookmarks/{bookmark_id}` | `assess.bookmark` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /assess/news-items/{item_id}` | `assess.news_item` | none | EmptyParameters | PathParameters | EmptyParameters | 200: NewsDeleted | yes | enforced |
| `DELETE /assess/stories/{story_id}` | `assess.story_` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /assess/story/{story_id}` | `assess.story` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /asset-groups/{group_id}` | `asset_group` | none | EmptyParameters | PathParameters | EmptyParameters | 200: union | yes | enforced |
| `DELETE /asset-groups` | `asset_groups` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /assets/{asset_id}` | `asset` | none | EmptyParameters | PathParameters | EmptyParameters | 200: union | yes | enforced |
| `DELETE /assets` | `assets` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /auth/logout` | `auth.logout` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /chat/conversations/{conversation_id}` | `chat.conversation` | none | EmptyParameters | ConversationPath | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/acls/{acl_id}` | `config.config_acl` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/acls` | `config.config_acls` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /config/attributes/{attribute_id}` | `config.config_attribute` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/attributes` | `config.config_attributes` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /config/bots/{bot_id}` | `config.config_bot_config` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/connectors/{connector_id}` | `config.config_connector` | none | ListQuery | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `DELETE /config/organizations/{organization_id}` | `config.config_organization` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/organizations` | `config.config_organizations` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /config/osint-source-groups/{group_id}` | `config.config_osint_source_group` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/osint-source-groups` | `config.config_osint_source_groups_config` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /config/osint-sources/{source_id}` | `config.config_osint_source` | none | SourceDeleteQuery | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `DELETE /config/osint-sources` | `config.config_osint_sources` | none | SourceDeleteQuery | EmptyParameters | EmptyParameters | 200: SourceDeleteResponse | yes | enforced |
| `DELETE /config/product-types/{type_id}` | `config.config_product_type` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/publisher-presets/{preset_id}` | `config.config_publisher_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/publishers-presets/{preset_id}` | `config.config_publishers_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/report-item-types/{type_id}` | `config.config_report_item_type` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/report-item-types` | `config.config_report_item_types` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /config/roles/{role_id}` | `config.config_role` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/roles` | `config.config_roles` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /config/sources/{source_id}` | `config.config_source` | none | SourceDeleteQuery | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `DELETE /config/templates/{template_path}` | `config.config_template` | none | EmptyParameters | PathParameters | EmptyParameters | 200: TemplateDeleteResponse | yes | enforced |
| `DELETE /config/templates` | `config.config_templates` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: TemplateDeleteResponse | yes | enforced |
| `DELETE /config/users/{user_id}` | `config.config_user` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/users` | `config.config_users` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /config/word-lists/{word_list_id}` | `config.config_word_list` | none | ListQuery | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /config/word-lists` | `config.config_word_lists` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `DELETE /dashboard/delete-tag/{tag_name}` | `dashboard.delete-tag` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /publish/products/{product_id}` | `publish.product` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /tasks/{task_id}` | `tasks.task` | none | EmptyParameters | TaskPath | EmptyParameters | 200: MessageResponse | yes | enforced |
| `DELETE /tasks` | `tasks.tasks` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `GET /` | `isalive_` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: IsAliveResponse | yes | enforced |
| `GET /admin/acls/{acl_id}` | `admin.admin_acl` | none | ListQuery | PathParameters | EmptyParameters | 200: ACLResourceResponse | yes | enforced |
| `GET /admin/acls` | `admin.admin_acls` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ACLResourceResponse_ | yes | enforced |
| `GET /admin/admin-menu-badges` | `admin.admin_admin_menu_badges` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: AdminMenuBadges | yes | enforced |
| `GET /admin/attributes/{attribute_id}` | `admin.admin_attribute` | none | ListQuery | PathParameters | EmptyParameters | 200: AttributeResourceResponse | yes | enforced |
| `GET /admin/attributes` | `admin.admin_attributes` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_AttributeResourceResponse_ | yes | enforced |
| `GET /admin/bots/{bot_id}` | `admin.admin_bot_config` | none | BotQuery | PathParameters | EmptyParameters | 200: BotResourceResponse | yes | enforced |
| `GET /admin/bots` | `admin.admin_bots_config` | none | BotQuery | EmptyParameters | EmptyParameters | 200: PageResponse_BotResourceResponse_ | yes | enforced |
| `GET /admin/connectors/{connector_id}` | `admin.admin_connector` | none | ListQuery | PathParameters | EmptyParameters | 200: ConnectorResourceResponse | yes | enforced |
| `GET /admin/connectors` | `admin.admin_connectors` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ConnectorResourceResponse_ | yes | enforced |
| `GET /admin/curated-osint-source-lists` | `admin.admin_curated_osint_source_lists` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_CuratedSummary_ | yes | enforced |
| `GET /admin/export-osint-sources` | `admin.admin_osint_sources_export` | none | SourceExportQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /admin/export-report-item-types` | `admin.admin_report_item_types_export` | none | IdsQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /admin/export-word-lists` | `admin.admin_word_list_export` | none | IdsQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /admin/organizations/{organization_id}` | `admin.admin_organization` | none | ListQuery | PathParameters | EmptyParameters | 200: OrganizationResourceResponse | yes | enforced |
| `GET /admin/organizations` | `admin.admin_organizations` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_OrganizationResourceResponse_ | yes | enforced |
| `GET /admin/osint-source-groups/options` | `admin.admin_osint_source_group_options` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: OSINTSourceGroupOptions | yes | enforced |
| `GET /admin/osint-source-groups/{group_id}` | `admin.admin_osint_source_group` | none | ListQuery | PathParameters | EmptyParameters | 200: OSINTSourceGroupResourceResponse | yes | enforced |
| `GET /admin/osint-source-groups` | `admin.admin_osint_source_groups_config` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_OSINTSourceGroupResourceResponse_ | yes | enforced |
| `GET /admin/osint-sources/{source_id}/preview` | `admin.admin_osint_source_preview` | none | EmptyParameters | PathParameters | EmptyParameters | 200: Task, 201: QueueNotice, 202: QueuedState | yes | enforced |
| `GET /admin/osint-sources/{source_id}` | `admin.admin_osint_source` | none | SourceQuery | PathParameters | EmptyParameters | 200: OSINTSourceResourceResponse | yes | enforced |
| `GET /admin/osint-sources` | `admin.admin_osint_sources` | none | SourceQuery | EmptyParameters | EmptyParameters | 200: PageResponse_OSINTSourceResourceResponse_ | yes | enforced |
| `GET /admin/permissions` | `admin.admin_permissions` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_Permission_ | yes | enforced |
| `GET /admin/product-types/{type_id}` | `admin.admin_product_type` | none | ListQuery | PathParameters | EmptyParameters | 200: ProductTypeResourceResponse | yes | enforced |
| `GET /admin/product-types` | `admin.admin_product_types_config` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ProductTypeResourceResponse_ | yes | enforced |
| `GET /admin/publisher-presets/{preset_id}` | `admin.admin_publisher_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: PublisherPresetResourceResponse | yes | enforced |
| `GET /admin/publisher-presets` | `admin.admin_publisher_presets` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_PublisherPresetResourceResponse_ | yes | enforced |
| `GET /admin/publishers-presets/{preset_id}` | `admin.admin_publishers_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: PublisherPresetResourceResponse | yes | enforced |
| `GET /admin/publishers-presets` | `admin.admin_publishers_presets` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_PublisherPresetResourceResponse_ | yes | enforced |
| `GET /admin/report-item-types/{type_id}` | `admin.admin_report_item_type` | none | ListQuery | PathParameters | EmptyParameters | 200: ReportItemTypeResourceResponse | yes | enforced |
| `GET /admin/report-item-types` | `admin.admin_report_item_types` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ReportItemTypeResourceResponse_ | yes | enforced |
| `GET /admin/roles/{role_id}` | `admin.admin_role` | none | ListQuery | PathParameters | EmptyParameters | 200: RoleResourceResponse | yes | enforced |
| `GET /admin/roles` | `admin.admin_roles` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_RoleResourceResponse_ | yes | enforced |
| `GET /admin/schedule/{task_id}` | `admin.admin_queue_schedule_task` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ScheduledJob | yes | enforced |
| `GET /admin/schedule` | `admin.admin_queue_schedule` | none | JobFilter | EmptyParameters | EmptyParameters | 200: PageResponse_ScheduledJob_ | yes | enforced |
| `GET /admin/sources/{source_id}` | `admin.admin_source` | none | SourceQuery | PathParameters | EmptyParameters | 200: OSINTSourceResourceResponse | yes | enforced |
| `GET /admin/sources` | `admin.admin_sources` | none | SourceQuery | EmptyParameters | EmptyParameters | 200: PageResponse_OSINTSourceResourceResponse_ | yes | enforced |
| `GET /admin/templates/{template_path}` | `admin.admin_template` | none | EmptyParameters | PathParameters | EmptyParameters | 200: TemplateResponse | yes | enforced |
| `GET /admin/templates` | `admin.admin_templates` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_TemplateResponse_ | yes | enforced |
| `GET /admin/users-export` | `admin.admin_users_export` | none | IdsQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /admin/users/{user_id}` | `admin.admin_user` | none | ListQuery | PathParameters | EmptyParameters | 200: UserProfileResponse | yes | enforced |
| `GET /admin/users` | `admin.admin_users` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_UserResponseResourceResponse_ | yes | enforced |
| `GET /admin/word-lists/{word_list_id}` | `admin.admin_word_list` | none | WordListQuery | PathParameters | EmptyParameters | 200: WordListResourceResponse | yes | enforced |
| `GET /admin/word-lists` | `admin.admin_word_lists` | none | WordListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_WordListResourceResponse_ | yes | enforced |
| `GET /admin/workers/active` | `admin.admin_active_jobs` | none | JobFilter | EmptyParameters | EmptyParameters | 200: PageResponse_ActiveJob_ | yes | enforced |
| `GET /admin/workers/cron-jobs` | `admin.admin_cron_jobs` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: CronJobsResponse | yes | enforced |
| `GET /admin/workers/failed` | `admin.admin_failed_jobs` | none | JobFilter | EmptyParameters | EmptyParameters | 200: PageResponse_FailedJob_ | yes | enforced |
| `GET /admin/workers/queue-status` | `admin.admin_queue_status` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueStatusResponse, 500: QueueStatusError | yes | enforced |
| `GET /admin/workers/schedule` | `admin.admin_queue_schedule_config` | none | JobFilter | EmptyParameters | EmptyParameters | 200: PageResponse_ScheduledJob_ | yes | enforced |
| `GET /admin/workers/stats` | `admin.admin_worker_stats` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: WorkerStatsResponse | yes | enforced |
| `GET /admin/workers/tasks` | `admin.admin_queue_tasks` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /admin/workers` | `admin.admin_workers` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /analyze/report-editors/{report_item_id}` | `analyze.report_editor` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ReportEditor | yes | enforced |
| `GET /analyze/report-items/{report_item_id}/cti` | `analyze.report_item_cti` | none | EmptyParameters | PathParameters | EmptyParameters | 200: CTIResponse | yes | enforced |
| `GET /analyze/report-items/{report_item_id}/locks` | `analyze.report_item_locks` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ReportLock | yes | enforced |
| `GET /analyze/report-items/{report_item_id}/revisions/{revision_number}` | `analyze.report_item_revision_data` | none | EmptyParameters | ReportRevisionPath | EmptyParameters | 200: RevisionData | yes | enforced |
| `GET /analyze/report-items/{report_item_id}/revisions` | `analyze.report_item_revisions` | none | EmptyParameters | PathParameters | EmptyParameters | 200: PageResponse_Revision_ | yes | enforced |
| `GET /analyze/report-items/{report_item_id}/stories` | `analyze.report_stories` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ReportStories | yes | enforced |
| `GET /analyze/report-items/{report_item_id}` | `analyze.report_item` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ReportResponse | yes | enforced |
| `GET /analyze/report-items` | `analyze.report_items` | none | ContentQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ReportResponse_ | yes | enforced |
| `GET /analyze/report-types` | `analyze.report_types` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_ReportTypes_ | yes | enforced |
| `GET /analyze/report/{report_item_id}` | `analyze.report` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ReportResponse | yes | enforced |
| `GET /analyze/reports` | `analyze.reports` | none | ContentQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ReportResponse_ | yes | enforced |
| `GET /assess/analyst-review/snapshot` | `assess.analyst_review_snapshot` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: StoryIds | yes | enforced |
| `GET /assess/bookmarks/{bookmark_id}` | `assess.bookmark` | none | EmptyParameters | PathParameters | EmptyParameters | 200: StoryBookmark | yes | enforced |
| `GET /assess/bookmarks` | `assess.bookmarks` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_StoryBookmark_ | yes | enforced |
| `GET /assess/connectors/proposals` | `assess.proposals` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: CountResponse | yes | enforced |
| `GET /assess/connectors` | `assess.connectors_list` | none | ListQuery | EmptyParameters | EmptyParameters | 200: ItemsResponse_ConnectorReference_ | yes | enforced |
| `GET /assess/filter-lists` | `assess.filter_lists` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: FilterLists | yes | enforced |
| `GET /assess/news-items/{item_id}/cti` | `assess.news_item_cti` | none | EmptyParameters | PathParameters | EmptyParameters | 200: CTIResponse | yes | enforced |
| `GET /assess/news-items/{item_id}` | `assess.news_item` | none | EmptyParameters | PathParameters | EmptyParameters | 200: NewsItemResponse | yes | enforced |
| `GET /assess/news-items` | `assess.news_items` | none | ContentQuery | EmptyParameters | EmptyParameters | 200: ItemsResponse_NewsItemResponse_ | yes | enforced |
| `GET /assess/osint-source-group-list` | `assess.osint_source_groups-list` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_Reference_ | yes | enforced |
| `GET /assess/osint-sources-list` | `assess.osint_sources_list` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_Reference_ | yes | enforced |
| `GET /assess/stories/bulk_action` | `assess.bulk_action` | none | StoryFilters | EmptyParameters | EmptyParameters | 200: StoryPage | yes | enforced |
| `GET /assess/stories/export` | `assess.story_export` | none | StoryIds | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /assess/stories/{story_id}/cti` | `assess.story_cti` | none | EmptyParameters | PathParameters | EmptyParameters | 200: CTIResponse | yes | enforced |
| `GET /assess/stories/{story_id}/revisions/{revision_number}` | `assess.story_revision_data` | none | EmptyParameters | StoryRevisionPath | EmptyParameters | 200: RevisionData | yes | enforced |
| `GET /assess/stories/{story_id}/revisions` | `assess.story_revisions` | none | EmptyParameters | PathParameters | EmptyParameters | 200: PageResponse_Revision_ | yes | enforced |
| `GET /assess/stories/{story_id}` | `assess.story_` | none | EmptyParameters | PathParameters | EmptyParameters | 200: StoryResponse | yes | enforced |
| `GET /assess/stories` | `assess.stories` | none | StoryFilters | EmptyParameters | EmptyParameters | 200: StoryPage | yes | enforced |
| `GET /assess/story/{connector_id}/share` | `assess.share_to_connector` | none | ListQuery | PathParameters | EmptyParameters | 200: ItemsResponse_ConnectorReference_ | yes | enforced |
| `GET /assess/story/{story_id}` | `assess.story` | none | EmptyParameters | PathParameters | EmptyParameters | 200: StoryResponse | yes | enforced |
| `GET /assess/taglist` | `assess.taglist` | none | ListQuery | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /asset-groups/{group_id}` | `asset_group` | none | AssetQuery | PathParameters | EmptyParameters | 200: AssetGroupResponse | yes | enforced |
| `GET /asset-groups` | `asset_groups` | none | AssetQuery | EmptyParameters | EmptyParameters | 200: PageResponse_AssetGroupResponse_ | yes | enforced |
| `GET /assets/cti` | `assets_cti` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: CTIResponse | yes | enforced |
| `GET /assets/{asset_id}/cti` | `asset_cti` | none | EmptyParameters | PathParameters | EmptyParameters | 200: CTIResponse | yes | enforced |
| `GET /assets/{asset_id}` | `asset` | none | AssetQuery | PathParameters | EmptyParameters | 200: AssetResponse | yes | enforced |
| `GET /assets` | `assets` | none | AssetQuery | EmptyParameters | EmptyParameters | 200: PageResponse_AssetResponse_ | yes | enforced |
| `GET /auth/method` | `auth.auth_method` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: AuthMethodResponse | yes | enforced |
| `GET /auth/refresh` | `auth.refresh` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: AccessTokenResponse | yes | enforced |
| `GET /bots/news-item/{news_item_id}` | `bots.update_news_item` | none | EmptyParameters | PathParameters | EmptyParameters | 200: NewsItemResponse | yes | enforced |
| `GET /bots/story/{story_id}/attributes` | `bots.story_attributes` | none | EmptyParameters | PathParameters | EmptyParameters | 200: union, 404: union | yes | enforced |
| `GET /bots/story/{story_id}` | `bots.update_story` | none | EmptyParameters | PathParameters | EmptyParameters | 200: StoryResponse | yes | enforced |
| `GET /bots/{bot_id}` | `bots.bot_info` | none | BotQuery | PathParameters | EmptyParameters | 200: Bot | yes | enforced |
| `GET /bots` | `bots.bots` | none | BotQuery | EmptyParameters | EmptyParameters | 200: ItemsResponse_Bot_ | yes | enforced |
| `GET /chat/conversations/{conversation_id}` | `chat.conversation` | none | EmptyParameters | ConversationPath | EmptyParameters | 200: ConversationResponse | yes | enforced |
| `GET /chat/conversations` | `chat.conversations` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ConversationListResponse | yes | enforced |
| `GET /config/acls/{acl_id}` | `config.config_acl` | none | ListQuery | PathParameters | EmptyParameters | 200: ACLResourceResponse | yes | enforced |
| `GET /config/acls` | `config.config_acls` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ACLResourceResponse_ | yes | enforced |
| `GET /config/admin-menu-badges` | `config.config_admin_menu_badges` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: AdminMenuBadges | yes | enforced |
| `GET /config/attributes/{attribute_id}` | `config.config_attribute` | none | ListQuery | PathParameters | EmptyParameters | 200: AttributeResourceResponse | yes | enforced |
| `GET /config/attributes` | `config.config_attributes` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_AttributeResourceResponse_ | yes | enforced |
| `GET /config/bots/{bot_id}` | `config.config_bot_config` | none | BotQuery | PathParameters | EmptyParameters | 200: BotResourceResponse | yes | enforced |
| `GET /config/bots` | `config.config_bots_config` | none | BotQuery | EmptyParameters | EmptyParameters | 200: PageResponse_BotResourceResponse_ | yes | enforced |
| `GET /config/connectors/{connector_id}` | `config.config_connector` | none | ListQuery | PathParameters | EmptyParameters | 200: ConnectorResourceResponse | yes | enforced |
| `GET /config/connectors` | `config.config_connectors` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ConnectorResourceResponse_ | yes | enforced |
| `GET /config/curated-osint-source-lists` | `config.config_curated_osint_source_lists` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_CuratedSummary_ | yes | enforced |
| `GET /config/export-osint-sources` | `config.config_osint_sources_export` | none | SourceExportQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /config/export-report-item-types` | `config.config_report_item_types_export` | none | IdsQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /config/export-word-lists` | `config.config_word_list_export` | none | IdsQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /config/organizations/{organization_id}` | `config.config_organization` | none | ListQuery | PathParameters | EmptyParameters | 200: OrganizationResourceResponse | yes | enforced |
| `GET /config/organizations` | `config.config_organizations` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_OrganizationResourceResponse_ | yes | enforced |
| `GET /config/osint-source-groups/options` | `config.config_osint_source_group_options` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: OSINTSourceGroupOptions | yes | enforced |
| `GET /config/osint-source-groups/{group_id}` | `config.config_osint_source_group` | none | ListQuery | PathParameters | EmptyParameters | 200: OSINTSourceGroupResourceResponse | yes | enforced |
| `GET /config/osint-source-groups` | `config.config_osint_source_groups_config` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_OSINTSourceGroupResourceResponse_ | yes | enforced |
| `GET /config/osint-sources/{source_id}/preview` | `config.config_osint_source_preview` | none | EmptyParameters | PathParameters | EmptyParameters | 200: Task, 201: QueueNotice, 202: QueuedState | yes | enforced |
| `GET /config/osint-sources/{source_id}` | `config.config_osint_source` | none | SourceQuery | PathParameters | EmptyParameters | 200: OSINTSourceResourceResponse | yes | enforced |
| `GET /config/osint-sources` | `config.config_osint_sources` | none | SourceQuery | EmptyParameters | EmptyParameters | 200: PageResponse_OSINTSourceResourceResponse_ | yes | enforced |
| `GET /config/permissions` | `config.config_permissions` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_Permission_ | yes | enforced |
| `GET /config/product-types/{type_id}` | `config.config_product_type` | none | ListQuery | PathParameters | EmptyParameters | 200: ProductTypeResourceResponse | yes | enforced |
| `GET /config/product-types` | `config.config_product_types_config` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ProductTypeResourceResponse_ | yes | enforced |
| `GET /config/publisher-presets/{preset_id}` | `config.config_publisher_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: PublisherPresetResourceResponse | yes | enforced |
| `GET /config/publisher-presets` | `config.config_publisher_presets` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_PublisherPresetResourceResponse_ | yes | enforced |
| `GET /config/publishers-presets/{preset_id}` | `config.config_publishers_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: PublisherPresetResourceResponse | yes | enforced |
| `GET /config/publishers-presets` | `config.config_publishers_presets` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_PublisherPresetResourceResponse_ | yes | enforced |
| `GET /config/report-item-types/{type_id}` | `config.config_report_item_type` | none | ListQuery | PathParameters | EmptyParameters | 200: ReportItemTypeResourceResponse | yes | enforced |
| `GET /config/report-item-types` | `config.config_report_item_types` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ReportItemTypeResourceResponse_ | yes | enforced |
| `GET /config/roles/{role_id}` | `config.config_role` | none | ListQuery | PathParameters | EmptyParameters | 200: RoleResourceResponse | yes | enforced |
| `GET /config/roles` | `config.config_roles` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_RoleResourceResponse_ | yes | enforced |
| `GET /config/schedule/{task_id}` | `config.config_queue_schedule_task` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ScheduledJob | yes | enforced |
| `GET /config/schedule` | `config.config_queue_schedule` | none | JobFilter | EmptyParameters | EmptyParameters | 200: PageResponse_ScheduledJob_ | yes | enforced |
| `GET /config/sources/{source_id}` | `config.config_source` | none | SourceQuery | PathParameters | EmptyParameters | 200: OSINTSourceResourceResponse | yes | enforced |
| `GET /config/sources` | `config.config_sources` | none | SourceQuery | EmptyParameters | EmptyParameters | 200: PageResponse_OSINTSourceResourceResponse_ | yes | enforced |
| `GET /config/templates/{template_path}` | `config.config_template` | none | EmptyParameters | PathParameters | EmptyParameters | 200: TemplateResponse | yes | enforced |
| `GET /config/templates` | `config.config_templates` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_TemplateResponse_ | yes | enforced |
| `GET /config/users-export` | `config.config_users_export` | none | IdsQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /config/users/{user_id}` | `config.config_user` | none | ListQuery | PathParameters | EmptyParameters | 200: UserProfileResponse | yes | enforced |
| `GET /config/users` | `config.config_users` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_UserResponseResourceResponse_ | yes | enforced |
| `GET /config/word-lists/{word_list_id}` | `config.config_word_list` | none | WordListQuery | PathParameters | EmptyParameters | 200: WordListResourceResponse | yes | enforced |
| `GET /config/word-lists` | `config.config_word_lists` | none | WordListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_WordListResourceResponse_ | yes | enforced |
| `GET /config/workers/active` | `config.config_active_jobs` | none | JobFilter | EmptyParameters | EmptyParameters | 200: PageResponse_ActiveJob_ | yes | enforced |
| `GET /config/workers/cron-jobs` | `config.config_cron_jobs` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: CronJobsResponse | yes | enforced |
| `GET /config/workers/failed` | `config.config_failed_jobs` | none | JobFilter | EmptyParameters | EmptyParameters | 200: PageResponse_FailedJob_ | yes | enforced |
| `GET /config/workers/queue-status` | `config.config_queue_status` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueStatusResponse, 500: QueueStatusError | yes | enforced |
| `GET /config/workers/schedule` | `config.config_queue_schedule_config` | none | JobFilter | EmptyParameters | EmptyParameters | 200: PageResponse_ScheduledJob_ | yes | enforced |
| `GET /config/workers/stats` | `config.config_worker_stats` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: WorkerStatsResponse | yes | enforced |
| `GET /config/workers/tasks` | `config.config_queue_tasks` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /config/workers` | `config.config_workers` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /connectors/conflicts/news-items` | `connectors.news_item_conflicts` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_NewsItemConflict_ | yes | enforced |
| `GET /connectors/conflicts/stories/{story_id}` | `connectors.story_conflict` | none | EmptyParameters | PathParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /connectors/conflicts/stories` | `connectors.story_conflicts` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /connectors/story-summary/{story_id}` | `connectors.story_summary` | none | EmptyParameters | PathParameters | EmptyParameters | 200: StorySummary | yes | enforced |
| `GET /dashboard/build-info` | `dashboard.build-info` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: BuildInfo | yes | enforced |
| `GET /dashboard/cluster-names` | `dashboard.cluster-names` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_str_ | yes | enforced |
| `GET /dashboard/cluster/{tag_type}` | `dashboard.cluster-by-type` | none | ClusterQuery | PathParameters | EmptyParameters | 200: PageResponse_Cluster_ | yes | enforced |
| `GET /dashboard/pizzint` | `dashboard.pizzint` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: PizzintStatus | yes | enforced |
| `GET /dashboard/story-clusters` | `dashboard.story-clusters` | none | ClusterQuery | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /dashboard/trending-clusters` | `dashboard.trending-clusters` | none | ClusterQuery | EmptyParameters | EmptyParameters | 200: ItemsResponse_TrendingCluster_ | yes | enforced |
| `GET /dashboard` | `dashboard.dashboard` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_Dashboard_ | yes | enforced |
| `GET /health` | `health` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: CoreHealth, 503: CoreHealth | yes | enforced |
| `GET /isalive` | `isalive` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: IsAliveResponse | yes | enforced |
| `GET /publish/product-choices` | `publish.product_choices` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_ProductChoice_ | yes | enforced |
| `GET /publish/product-metadata/{product_id}` | `publish.product_metadata` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ProductResponse | yes | enforced |
| `GET /publish/product-type-choices` | `publish.product_type_choices` | none | ProductTypeQuery | EmptyParameters | EmptyParameters | 200: ItemsResponse_ProductTypeChoice_ | yes | enforced |
| `GET /publish/product-types` | `publish.product_types` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_ProductType_ | yes | enforced |
| `GET /publish/products/auto-render/{report_item_id}` | `publish.auto_render_products` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ProductList | yes | enforced |
| `GET /publish/products/{product_id}/render` | `publish.render_product` | none | EmptyParameters | PathParameters | EmptyParameters | 200: DownloadHeaders, 206: DownloadHeaders, 304: none | yes | enforced |
| `GET /publish/products/{product_id}` | `publish.product` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ProductResponse | yes | enforced |
| `GET /publish/products` | `publish.products` | none | ProductQuery | EmptyParameters | EmptyParameters | 200: PageResponse_ProductResponse_ | yes | enforced |
| `GET /publish/publisher-presets/{preset_id}` | `publish.publisher_preset` | none | ListQuery | PathParameters | EmptyParameters | 200: models__product__PublisherPreset | yes | enforced |
| `GET /publish/publisher-presets` | `publish.publisher_presets` | none | ListQuery | EmptyParameters | EmptyParameters | 200: PageResponse_PublisherPreset_ | yes | enforced |
| `GET /realtime/clients` | `realtime.connected_clients` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: Clients | yes | enforced |
| `GET /reports/{product_id}` | `published_reports.published_report` | none | EmptyParameters | PathParameters | EmptyParameters | 200: DownloadHeaders, 206: DownloadHeaders, 304: none | yes | enforced |
| `GET /settings/export-stories` | `settings.export_stories` | none | ExportStoriesQuery | EmptyParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /settings/settings` | `settings.settings` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: SettingsResponse | yes | enforced |
| `GET /static/<path:filename>` | `static` | none | none | filename | none | file | n/a | framework static |
| `GET /static/default_word_lists.json` | `static.default_word_lists` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: DownloadHeaders, 206: DownloadHeaders, 304: none | yes | enforced |
| `GET /static/openapi3_1.yaml` | `static.openapi3` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: DownloadHeaders, 206: DownloadHeaders, 304: none | yes | enforced |
| `GET /tasks/runs` | `tasks.completed_runs` | none | TaskRunFilter | EmptyParameters | EmptyParameters | 200: UserTaskListResponse | yes | enforced |
| `GET /tasks/user` | `tasks.user_tasks` | none | UserTaskFilter | EmptyParameters | EmptyParameters | 200: UserTaskListResponse | yes | enforced |
| `GET /tasks/{task_id}` | `tasks.task` | none | EmptyParameters | TaskPath | EmptyParameters | 200: TaskResponse, 404: union | yes | enforced |
| `GET /tasks` | `tasks.tasks` | none | TaskQuery | EmptyParameters | EmptyParameters | 200: TaskListResponse | yes | enforced |
| `GET /users/` | `user.user_info` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: UserProfileResponse | yes | enforced |
| `GET /users/profile` | `user.user_profile` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: ProfileSettings | yes | enforced |
| `GET /worker/bots/{bot_id}` | `worker.bot_info_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: WorkerBotResponse | yes | enforced |
| `GET /worker/bots` | `worker.bots_worker` | none | BotQuery | EmptyParameters | EmptyParameters | 200: ItemsResponse_WorkerBotResponse_ | yes | enforced |
| `GET /worker/connectors/{connector_id}` | `worker.connectors_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: WorkerConnectorResponse | yes | enforced |
| `GET /worker/cron-jobs` | `worker.cron_jobs_worker` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: CronJobsResponse | yes | enforced |
| `GET /worker/endpoint-health/{kind}/{endpoint_id}` | `worker.endpoint_health_worker` | none | CheckQuery | PathParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /worker/osint-sources/{source_id}` | `worker.osint_sources_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: WorkerSourceResponse | yes | enforced |
| `GET /worker/osint-sources` | `worker.osint_sources_all_worker` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: SourcesResponse | yes | enforced |
| `GET /worker/presenters/{presenter}` | `worker.presenters_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /worker/products/{product_id}/render` | `worker.products_render_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: DownloadHeaders | yes | enforced |
| `GET /worker/products/{product_id}` | `worker.products_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: WorkerProduct | yes | enforced |
| `GET /worker/publishers/{publisher}` | `worker.publishers_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: WorkerPublisherResponse | yes | enforced |
| `GET /worker/report-items/{report_id}` | `worker.report_by_id_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: WorkerReportResponse | yes | enforced |
| `GET /worker/stories` | `worker.stories_worker` | none | ContentQuery | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /worker/tags` | `worker.tags_worker` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `GET /worker/word-list/{word_list_id}` | `worker.word_list_by_id_worker` | none | WordListQuery | PathParameters | EmptyParameters | 200: WorkerWordListResponse | yes | enforced |
| `GET /worker/word-lists` | `worker.word_lists_worker` | none | WordListQuery | EmptyParameters | EmptyParameters | 200: ItemsResponse_WorkerWordListResponse_ | yes | enforced |
| `PATCH /admin/bots/{bot_id}` | `admin.admin_bot_config` | BotUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /admin/connectors/{connector_id}` | `admin.admin_connector` | ConnectorUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /admin/osint-sources/{source_id}` | `admin.admin_osint_source` | SourceUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /admin/product-types/{type_id}` | `admin.admin_product_type` | ProductTypeUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /admin/publisher-presets/{preset_id}` | `admin.admin_publisher_preset` | PublisherPresetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /admin/publishers-presets/{preset_id}` | `admin.admin_publishers_preset` | PublisherPresetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /admin/sources/{source_id}` | `admin.admin_source` | SourceUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /assess/bookmarks/order` | `assess.bookmark_order` | StoryBookmarkOrderPayload | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PATCH /assess/bookmarks/{bookmark_id}` | `assess.bookmark` | StoryBookmarkUpdatePayload | EmptyParameters | PathParameters | EmptyParameters | 200: BookmarkWritten | yes | enforced |
| `PATCH /assess/news-items/{item_id}` | `assess.news_item` | NewsUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: NewsUpdated | yes | enforced |
| `PATCH /assess/stories/{story_id}` | `assess.story_` | StoryUpdatePayload | EmptyParameters | PathParameters | EmptyParameters | 200: StoryUpdated | yes | enforced |
| `PATCH /assess/story/{story_id}` | `assess.story` | StoryUpdatePayload | EmptyParameters | PathParameters | EmptyParameters | 200: StoryUpdated | yes | enforced |
| `PATCH /bots/story/{story_id}/attributes` | `bots.story_attributes` | union | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PATCH /config/bots/{bot_id}` | `config.config_bot_config` | BotUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /config/connectors/{connector_id}` | `config.config_connector` | ConnectorUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /config/osint-sources/{source_id}` | `config.config_osint_source` | SourceUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /config/product-types/{type_id}` | `config.config_product_type` | ProductTypeUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /config/publisher-presets/{preset_id}` | `config.config_publisher_preset` | PublisherPresetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /config/publishers-presets/{preset_id}` | `config.config_publishers_preset` | PublisherPresetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /config/sources/{source_id}` | `config.config_source` | SourceUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `PATCH /settings/settings` | `settings.settings` | SettingsInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: SettingsUpdated | yes | enforced |
| `POST /admin/acls` | `admin.admin_acls` | ACL | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/attributes` | `admin.admin_attributes` | models__admin__Attribute | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/bots/dag-preview` | `admin.admin_bot_dag_preview` | DagRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: DagResponse | yes | enforced |
| `POST /admin/bots/{bot_id}/execute` | `admin.admin_bot_execute` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /admin/bots` | `admin.admin_bots_config` | BotCreate | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/cache/invalidate` | `admin_cache_invalidate` | CacheRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: CacheResponse | yes | enforced |
| `POST /admin/connectors/{connector_id}/pull` | `admin.admin_connector_collect` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /admin/connectors` | `admin.admin_connectors` | Connector | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/curated-osint-source-lists` | `admin.admin_curated_osint_source_lists` | CuratedOSINTSourceSelection | EmptyParameters | EmptyParameters | EmptyParameters | 200: CuratedLoadResponse | yes | enforced |
| `POST /admin/dictionaries-reload/{dictionary_type}` | `admin.admin_dictionaries_reload` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /admin/import-osint-sources` | `admin.admin_osint_sources_import` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: SourcesImported | yes | enforced |
| `POST /admin/import-report-item-types` | `admin.admin_report_item_types_import` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `POST /admin/import-word-lists` | `admin.admin_word_list_import` | WordListImport | EmptyParameters | EmptyParameters | EmptyParameters | 200: WordListsImported | yes | enforced |
| `POST /admin/organizations` | `admin.admin_organizations` | Organization | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/osint-source-groups` | `admin.admin_osint_source_groups_config` | OSINTSourceGroup | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/osint-sources/collect` | `admin.admin_osint_sources_collect` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /admin/osint-sources/{source_id}/collect` | `admin.admin_osint_source_collect` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /admin/osint-sources/{source_id}/preview` | `admin.admin_osint_source_preview` | none | EmptyParameters | PathParameters | EmptyParameters | 201: QueueNotice | yes | enforced |
| `POST /admin/osint-sources` | `admin.admin_osint_sources` | OSINTSource | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/parameter-secrets/{resource}/{resource_id}/{parameter}/reveal` | `admin.admin_parameter_secret_reveal` | none | EmptyParameters | PathParameters | EmptyParameters | 200: SecretResponse | yes | enforced |
| `POST /admin/product-types` | `admin.admin_product_types_config` | ProductType | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/publisher-presets` | `admin.admin_publisher_presets` | models__admin__PublisherPreset | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/publishers-presets` | `admin.admin_publishers_presets` | models__admin__PublisherPreset | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/report-item-types` | `admin.admin_report_item_types` | ReportTypeInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/roles` | `admin.admin_roles` | Role | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/sources` | `admin.admin_sources` | OSINTSource | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/templates/validate` | `admin.admin_template_validation` | TemplateValidationRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: TemplateValidationResponse | yes | enforced |
| `POST /admin/templates/{template_path}` | `admin.admin_template` | TemplateWrite | EmptyParameters | PathParameters | EmptyParameters | 200: TemplateWriteResponse | yes | enforced |
| `POST /admin/templates` | `admin.admin_templates` | TemplateWrite | EmptyParameters | EmptyParameters | EmptyParameters | 200: TemplateWriteResponse | yes | enforced |
| `POST /admin/users-import` | `admin.admin_users_import` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: UsersImported | yes | enforced |
| `POST /admin/users` | `admin.admin_users` | UserInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /admin/word-lists/gather/{word_list_id}` | `admin.admin_word_list_gather` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /admin/word-lists/gather` | `admin.admin_word_list_gather_all` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /admin/word-lists` | `admin.admin_word_lists` | WordListInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /analyze/report-items/botactions` | `analyze.report_bot_actions` | BotAction | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice | yes | enforced |
| `POST /analyze/report-items/publish-product` | `analyze.report_items_publish_product` | WorkflowRequest | EmptyParameters | EmptyParameters | EmptyParameters | 201: WorkflowResponse, 400: ContentError, 500: union | yes | enforced |
| `POST /analyze/report-items/{report_item_id}/clone` | `analyze.clone_report_item` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ReportWritten | yes | enforced |
| `POST /analyze/report-items/{report_item_id}/stories` | `analyze.report_stories` | union | EmptyParameters | PathParameters | EmptyParameters | 200: union, 400: union, 403: union, 404: union, 409: union, 500: union | yes | enforced |
| `POST /analyze/report-items` | `analyze.report_items` | ReportCreate | EmptyParameters | EmptyParameters | EmptyParameters | 200: ReportWritten | yes | enforced |
| `POST /analyze/reports` | `analyze.reports` | ReportCreate | EmptyParameters | EmptyParameters | EmptyParameters | 200: ReportWritten | yes | enforced |
| `POST /assess/analyst-review/actions` | `assess.analyst_review_action` | AnalystReviewActionPayload | EmptyParameters | EmptyParameters | EmptyParameters | 200: ReviewActionResponse | yes | enforced |
| `POST /assess/bookmarks/memberships` | `assess.bookmark_memberships` | StoryBookmarkMembershipPayload | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /assess/bookmarks/quick-save` | `assess.bookmark_quick_save` | StoryBookmarkStoryPayload | EmptyParameters | EmptyParameters | EmptyParameters | 200: BookmarkSaved | yes | enforced |
| `POST /assess/bookmarks/{bookmark_id}/stories/remove` | `assess.bookmark_story_removal` | StoryBookmarkStoryPayload | EmptyParameters | PathParameters | EmptyParameters | 200: BookmarkRemoved | yes | enforced |
| `POST /assess/bookmarks/{bookmark_id}/stories` | `assess.bookmark_stories` | StoryBookmarkStoryPayload | EmptyParameters | PathParameters | EmptyParameters | 200: BookmarkAdded | yes | enforced |
| `POST /assess/bookmarks` | `assess.bookmarks` | StoryBookmarkCreatePayload | EmptyParameters | EmptyParameters | EmptyParameters | 201: BookmarkWritten | yes | enforced |
| `POST /assess/connectors` | `assess.connectors_list` | ShareInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice | yes | enforced |
| `POST /assess/import` | `assess.import` | JsonValue | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `POST /assess/news-items/fetch` | `assess.news_item_fetch` | FetchInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice | yes | enforced |
| `POST /assess/news-items` | `assess.news_items` | ManualNewsInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: StoryAdded, 400: ContentError, 404: ContentError, 409: ContentError, 500: ContentError | yes | enforced |
| `POST /assess/stories/botactions` | `assess.bot_actions` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice | yes | enforced |
| `POST /assess/stories/bulk_action` | `assess.bulk_action` | BulkWrite | EmptyParameters | EmptyParameters | EmptyParameters | 200: BulkResponse | yes | enforced |
| `POST /assess/stories/group` | `assess.group_action` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `POST /assess/stories` | `assess.stories` | BulkWrite | EmptyParameters | EmptyParameters | EmptyParameters | 200: BulkResponse | yes | enforced |
| `POST /assess/story/{connector_id}/share` | `assess.share_to_connector` | ShareInput | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice | yes | enforced |
| `POST /asset-groups` | `asset_groups` | AssetGroupInput | EmptyParameters | EmptyParameters | EmptyParameters | 201: IdMessageResponse | yes | enforced |
| `POST /assets` | `assets` | Asset | EmptyParameters | EmptyParameters | EmptyParameters | 201: IdMessageResponse | yes | enforced |
| `POST /auth/change_password` | `auth.change_password` | ChangePasswordRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /auth/login` | `auth.login` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: TokenResponse | yes | enforced |
| `POST /chat/conversations/{conversation_id}/messages` | `chat.messages` | ChatTurnRequest | EmptyParameters | ConversationPath | EmptyParameters | 201: TurnResponse | yes | enforced |
| `POST /chat/conversations` | `chat.conversations` | ChatTurnRequest | EmptyParameters | EmptyParameters | EmptyParameters | 201: TurnResponse | yes | enforced |
| `POST /config/acls` | `config.config_acls` | ACL | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/attributes` | `config.config_attributes` | models__admin__Attribute | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/bots/dag-preview` | `config.config_bot_dag_preview` | DagRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: DagResponse | yes | enforced |
| `POST /config/bots/{bot_id}/execute` | `config.config_bot_execute` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /config/bots` | `config.config_bots_config` | BotCreate | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/connectors/{connector_id}/pull` | `config.config_connector_collect` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /config/connectors` | `config.config_connectors` | Connector | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/curated-osint-source-lists` | `config.config_curated_osint_source_lists` | CuratedOSINTSourceSelection | EmptyParameters | EmptyParameters | EmptyParameters | 200: CuratedLoadResponse | yes | enforced |
| `POST /config/dictionaries-reload/{dictionary_type}` | `config.config_dictionaries_reload` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /config/import-osint-sources` | `config.config_osint_sources_import` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: SourcesImported | yes | enforced |
| `POST /config/import-report-item-types` | `config.config_report_item_types_import` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `POST /config/import-word-lists` | `config.config_word_list_import` | WordListImport | EmptyParameters | EmptyParameters | EmptyParameters | 200: WordListsImported | yes | enforced |
| `POST /config/organizations` | `config.config_organizations` | Organization | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/osint-source-groups` | `config.config_osint_source_groups_config` | OSINTSourceGroup | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/osint-sources/collect` | `config.config_osint_sources_collect` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /config/osint-sources/{source_id}/collect` | `config.config_osint_source_collect` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /config/osint-sources/{source_id}/preview` | `config.config_osint_source_preview` | none | EmptyParameters | PathParameters | EmptyParameters | 201: QueueNotice | yes | enforced |
| `POST /config/osint-sources` | `config.config_osint_sources` | OSINTSource | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/parameter-secrets/{resource}/{resource_id}/{parameter}/reveal` | `config.config_parameter_secret_reveal` | none | EmptyParameters | PathParameters | EmptyParameters | 200: SecretResponse | yes | enforced |
| `POST /config/product-types` | `config.config_product_types_config` | ProductType | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/publisher-presets` | `config.config_publisher_presets` | models__admin__PublisherPreset | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/publishers-presets` | `config.config_publishers_presets` | models__admin__PublisherPreset | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/report-item-types` | `config.config_report_item_types` | ReportTypeInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/roles` | `config.config_roles` | Role | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/sources` | `config.config_sources` | OSINTSource | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/templates/validate` | `config.config_template_validation` | TemplateValidationRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: TemplateValidationResponse | yes | enforced |
| `POST /config/templates/{template_path}` | `config.config_template` | TemplateWrite | EmptyParameters | PathParameters | EmptyParameters | 200: TemplateWriteResponse | yes | enforced |
| `POST /config/templates` | `config.config_templates` | TemplateWrite | EmptyParameters | EmptyParameters | EmptyParameters | 200: TemplateWriteResponse | yes | enforced |
| `POST /config/users-import` | `config.config_users_import` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: UsersImported | yes | enforced |
| `POST /config/users` | `config.config_users` | UserInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /config/word-lists/gather/{word_list_id}` | `config.config_word_list_gather` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /config/word-lists/gather` | `config.config_word_list_gather_all` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice, 201: QueueNotice, 202: QueueNotice | yes | enforced |
| `POST /config/word-lists` | `config.config_word_lists` | WordListInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `POST /connectors/conflicts/clear` | `connectors.clear_conflicts` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /connectors/conflicts/news-items` | `connectors.news_item_conflicts` | AddNews | EmptyParameters | EmptyParameters | EmptyParameters | 200: AddedNews, 207: AddedNews | yes | enforced |
| `POST /publish/products/{product_id}/publishers/{publisher_id}` | `publish.publish_product` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice | yes | enforced |
| `POST /publish/products/{product_id}/render` | `publish.render_product` | none | EmptyParameters | PathParameters | EmptyParameters | 200: QueueNotice | yes | enforced |
| `POST /publish/products` | `publish.products` | ProductInput | EmptyParameters | EmptyParameters | EmptyParameters | 201: ProductWritten | yes | enforced |
| `POST /realtime/broadcast` | `realtime.broadcast_notification` | Broadcast | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /realtime/connect` | `realtime.connect` | union | EmptyParameters | EmptyParameters | ProxyHeaders | 200: union | yes | enforced |
| `POST /settings/clear-queues` | `settings.clear_queue` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /settings/delete-stories` | `settings.delete_stories` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /settings/delete-tags` | `settings.delete_tags` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /settings/llm-endpoints/{endpoint_id}/delete` | `settings.delete_llm_endpoint` | none | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `POST /settings/llm-endpoints/{endpoint_id}` | `settings.llm_endpoint` | LLMWriteUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `POST /settings/llm-endpoints` | `settings.llm_endpoints` | LLMWriteUpdate | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse | yes | enforced |
| `POST /settings/rebuild-story-search-vectors` | `settings.rebuild_story_search_vectors` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: RebuildResponse | yes | enforced |
| `POST /settings/reset-database` | `settings.reset_database` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `POST /settings/settings` | `settings.settings` | SettingsInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: SettingsUpdated | yes | enforced |
| `POST /settings/ungroup-stories` | `settings.ungroup_all_stories` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `POST /tasks` | `tasks.tasks` | TaskSubmission | EmptyParameters | EmptyParameters | EmptyParameters | 200: TaskResponse | yes | enforced |
| `POST /users/profile` | `user.user_profile` | ProfileSettingsUpdate | EmptyParameters | EmptyParameters | EmptyParameters | 200: ProfileUpdated | yes | enforced |
| `POST /worker/bot-pipeline/stories` | `worker.bot_pipeline_stories_worker` | PipelineRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: PipelineResponse | yes | enforced |
| `POST /worker/cron-jobs` | `worker.cron_jobs_worker` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /worker/endpoint-health/{kind}/{endpoint_id}` | `worker.endpoint_health_worker` | EndpointResult | EmptyParameters | PathParameters | EmptyParameters | 200: EndpointAccepted | yes | enforced |
| `POST /worker/iocs` | `worker.iocs_worker` | IOCQuery | EmptyParameters | EmptyParameters | EmptyParameters | 200: ItemsResponse_CTIItem_ | yes | enforced |
| `POST /worker/misp/last-change` | `worker.last_change` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: union, 400: union, 409: union, 500: union | yes | enforced |
| `POST /worker/misp/stories` | `worker.misp_stories_worker` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: union, 400: union, 409: union, 500: union | yes | enforced |
| `POST /worker/news-items` | `worker.news_items_worker` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: CollectionResult, 400: union, 409: union, 500: union | yes | enforced |
| `POST /worker/products/{product_id}/publish` | `worker.products_publish_worker` | none | EmptyParameters | PathParameters | EmptyParameters | 200: TaranisPublished | yes | enforced |
| `POST /worker/stories` | `worker.stories_worker` | StoryInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: union, 400: union, 409: union, 500: union | yes | enforced |
| `POST /worker/tasks/changed` | `worker.task_changes_worker` | TaskChangeNotice | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `POST /worker/tasks/history/cleanup` | `worker.task_history_cleanup_worker` | none | EmptyParameters | EmptyParameters | EmptyParameters | 200: CleanupResult | yes | enforced |
| `PUT /admin/acls/{acl_id}` | `admin.admin_acl` | ACLUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/acls` | `admin.admin_acls` | ACLUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /admin/attributes/{attribute_id}` | `admin.admin_attribute` | AttributeUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/attributes` | `admin.admin_attributes` | AttributeUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /admin/bots/{bot_id}` | `admin.admin_bot_config` | BotUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/connectors/{connector_id}` | `admin.admin_connector` | ConnectorUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/organizations/{organization_id}` | `admin.admin_organization` | OrganizationUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/organizations` | `admin.admin_organizations` | OrganizationUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /admin/osint-source-groups/{group_id}` | `admin.admin_osint_source_group` | OSINTSourceGroupUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/osint-source-groups` | `admin.admin_osint_source_groups_config` | OSINTSourceGroupUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /admin/osint-sources/{source_id}` | `admin.admin_osint_source` | SourceUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/product-types/{type_id}` | `admin.admin_product_type` | ProductTypeUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/publisher-presets/{preset_id}` | `admin.admin_publisher_preset` | PublisherPresetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/publishers-presets/{preset_id}` | `admin.admin_publishers_preset` | PublisherPresetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/report-item-types/{type_id}` | `admin.admin_report_item_type` | ReportTypeInputUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/report-item-types` | `admin.admin_report_item_types` | ReportTypeInputUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /admin/roles/{role_id}` | `admin.admin_role` | RoleUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/roles` | `admin.admin_roles` | RoleUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /admin/sources/{source_id}` | `admin.admin_source` | SourceUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/templates/{template_path}` | `admin.admin_template` | TemplateWrite | EmptyParameters | PathParameters | EmptyParameters | 200: TemplateWriteResponse | yes | enforced |
| `PUT /admin/templates` | `admin.admin_templates` | TemplateWrite | EmptyParameters | EmptyParameters | EmptyParameters | 200: TemplateWriteResponse | yes | enforced |
| `PUT /admin/users/{user_id}` | `admin.admin_user` | UserInputUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/users` | `admin.admin_users` | UserInputUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /admin/word-lists/{word_list_id}` | `admin.admin_word_list` | WordListInputUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /admin/word-lists` | `admin.admin_word_lists` | WordListInputUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /analyze/report-items/{report_item_id}/lock` | `analyze.report_item_lock` | none | EmptyParameters | PathParameters | EmptyParameters | 200: ReportLock | yes | enforced |
| `PUT /analyze/report-items/{report_item_id}/stories` | `analyze.report_stories` | union | EmptyParameters | PathParameters | EmptyParameters | 200: union, 400: union, 403: union, 404: union, 409: union, 500: union | yes | enforced |
| `PUT /analyze/report-items/{report_item_id}` | `analyze.report_item` | ReportUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: ReportWritten, 400: union, 403: union, 404: union, 409: union, 500: union | yes | enforced |
| `PUT /analyze/report-items` | `analyze.report_items` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /analyze/report/{report_item_id}` | `analyze.report` | ReportUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: ReportWritten, 400: union, 403: union, 404: union, 409: union, 500: union | yes | enforced |
| `PUT /analyze/reports` | `analyze.reports` | none | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /assess/news-items/ungroup` | `assess.ungroup_news_items` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `PUT /assess/news-items/{item_id}` | `assess.news_item` | NewsUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: NewsUpdated | yes | enforced |
| `PUT /assess/news-items/{news_item_id}/attributes` | `assess.update_news_item_attributes` | union | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /assess/news-items/{news_item_id}/tags` | `assess.update_news_item_tags` | union | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /assess/stories/group` | `assess.group_action` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `PUT /assess/stories/ungroup` | `assess.ungroup_stories` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: union | yes | enforced |
| `PUT /assess/stories/{story_id}/news-item-order` | `assess.story_news_item_order` | StoryNewsItemOrderPayload | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /assess/stories/{story_id}` | `assess.story_` | StoryUpdatePayload | EmptyParameters | PathParameters | EmptyParameters | 200: StoryUpdated | yes | enforced |
| `PUT /assess/story/{story_id}` | `assess.story` | StoryUpdatePayload | EmptyParameters | PathParameters | EmptyParameters | 200: StoryUpdated | yes | enforced |
| `PUT /asset-groups/{group_id}` | `asset_group` | AssetGroupInputUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: union, 201: IdMessageResponse | yes | enforced |
| `PUT /asset-groups` | `asset_groups` | AssetGroupInputUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /assets/{asset_id}/vulnerabilities/{vulnerability_id}` | `asset_vulnerability` | SolvedRequest | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse, 400: union | yes | enforced |
| `PUT /assets/{asset_id}` | `asset` | AssetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: union, 201: IdMessageResponse | yes | enforced |
| `PUT /assets` | `assets` | AssetUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /bots/news-item/{news_item_id}/attributes` | `bots.update_news_item_attributes` | union | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /bots/news-item/{news_item_id}` | `bots.update_news_item` | LanguageUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: union | yes | enforced |
| `PUT /bots/stories/group-multiple` | `bots.group_multiple_stories` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /bots/stories/group` | `bots.group_stories` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /bots/stories/ungroup` | `bots.ungroup_stories_bot` | union | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /bots/story/{story_id}` | `bots.update_story` | StoryUpdatePayload | EmptyParameters | PathParameters | EmptyParameters | 200: StoryUpdated | yes | enforced |
| `PUT /bots/{bot_id}` | `bots.bot_info` | BotUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 404: union | yes | enforced |
| `PUT /bots` | `bots.bots` | BotUpdate | EmptyParameters | EmptyParameters | EmptyParameters | 200: IdMessageResponse, 404: union | yes | enforced |
| `PUT /config/acls/{acl_id}` | `config.config_acl` | ACLUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/acls` | `config.config_acls` | ACLUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /config/attributes/{attribute_id}` | `config.config_attribute` | AttributeUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/attributes` | `config.config_attributes` | AttributeUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /config/bots/{bot_id}` | `config.config_bot_config` | BotUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/connectors/{connector_id}` | `config.config_connector` | ConnectorUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/organizations/{organization_id}` | `config.config_organization` | OrganizationUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/organizations` | `config.config_organizations` | OrganizationUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /config/osint-source-groups/{group_id}` | `config.config_osint_source_group` | OSINTSourceGroupUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/osint-source-groups` | `config.config_osint_source_groups_config` | OSINTSourceGroupUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /config/osint-sources/{source_id}` | `config.config_osint_source` | SourceUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/product-types/{type_id}` | `config.config_product_type` | ProductTypeUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/publisher-presets/{preset_id}` | `config.config_publisher_preset` | PublisherPresetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/publishers-presets/{preset_id}` | `config.config_publishers_preset` | PublisherPresetUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/report-item-types/{type_id}` | `config.config_report_item_type` | ReportTypeInputUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/report-item-types` | `config.config_report_item_types` | ReportTypeInputUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /config/roles/{role_id}` | `config.config_role` | RoleUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/roles` | `config.config_roles` | RoleUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /config/sources/{source_id}` | `config.config_source` | SourceUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/templates/{template_path}` | `config.config_template` | TemplateWrite | EmptyParameters | PathParameters | EmptyParameters | 200: TemplateWriteResponse | yes | enforced |
| `PUT /config/templates` | `config.config_templates` | TemplateWrite | EmptyParameters | EmptyParameters | EmptyParameters | 200: TemplateWriteResponse | yes | enforced |
| `PUT /config/users/{user_id}` | `config.config_user` | UserInputUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/users` | `config.config_users` | UserInputUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /config/word-lists/{word_list_id}` | `config.config_word_list` | WordListInputUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: IdMessageResponse, 201: IdMessageResponse | yes | enforced |
| `PUT /config/word-lists` | `config.config_word_lists` | WordListInputUpdate | EmptyParameters | EmptyParameters | EmptyParameters | errors only | yes | enforced |
| `PUT /connectors/conflicts/news-items` | `connectors.news_item_conflicts` | UngroupIncoming | EmptyParameters | EmptyParameters | EmptyParameters | 200: StoryAdded, 400: ContentError, 409: ContentError, 500: ContentError | yes | enforced |
| `PUT /connectors/conflicts/stories/{story_id}` | `connectors.story_conflict` | Resolution | EmptyParameters | PathParameters | EmptyParameters | 200: union, 400: union, 404: union, 409: union, 500: union | yes | enforced |
| `PUT /connectors/conflicts/stories` | `connectors.story_conflicts` | Resolution | EmptyParameters | EmptyParameters | EmptyParameters | 200: union, 400: union, 404: union, 409: union, 500: union | yes | enforced |
| `PUT /publish/products/{product_id}` | `publish.product` | ProductInputUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: ProductWritten | yes | enforced |
| `PUT /settings/settings` | `settings.settings` | SettingsInput | EmptyParameters | EmptyParameters | EmptyParameters | 200: SettingsUpdated | yes | enforced |
| `PUT /users/profile` | `user.user_profile` | ProfileSettingsUpdate | EmptyParameters | EmptyParameters | EmptyParameters | 200: ProfileUpdated | yes | enforced |
| `PUT /worker/bots/{bot_id}` | `worker.bot_info_worker` | BotUpdate | EmptyParameters | PathParameters | EmptyParameters | 200: WorkerBotResponse | yes | enforced |
| `PUT /worker/bots` | `worker.bots_worker` | BotUpdate | EmptyParameters | EmptyParameters | EmptyParameters | 200: WorkerBotResponse | yes | enforced |
| `PUT /worker/misp/last-change` | `worker.last_change` | LastChangeRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /worker/misp/stories` | `worker.misp_stories_worker` | LastChangeRequest | EmptyParameters | EmptyParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /worker/osint-sources/{source_id}/icon` | `worker.osint_sources_worker_icon` | none | EmptyParameters | PathParameters | EmptyParameters | 200: MessageResponse | yes | enforced |
| `PUT /worker/post-collection-bots` | `worker.post_collection_bots_worker` | PostCollection | EmptyParameters | EmptyParameters | EmptyParameters | 200: QueueNotice | yes | enforced |
| `PUT /worker/tags` | `worker.tags_worker` | union | ReplaceQuery | EmptyParameters | EmptyParameters | 200: MessageResponse, 207: PartialTags | yes | enforced |
| `PUT /worker/word-list/{word_list_id}` | `worker.word_list_by_id_worker` | WordListImport | EmptyParameters | PathParameters | EmptyParameters | 200: WordListUpdated | yes | enforced |
| `PUT /worker/word-lists` | `worker.word_lists_worker` | WordListImport | EmptyParameters | EmptyParameters | EmptyParameters | 200: WordListUpdated | yes | enforced |

## Frontend and service clients

Four structured frontend operations are enforced through `models/frontend_api.py` and `frontend/api_contracts.py`: the cached-user JSON collection and the three JSON/form conflict actions. Their HTML success, error and authentication responses validate metadata while retaining server rendering. Ordinary pages and HTMX fragments are outside API conversion. The frontend route test checks their handler wiring under both application prefixes.

Frontend CoreApi and worker CoreApi require executable operations for every outgoing call, including external login, uncached readers, multipart icons, CSV updates and downloads. They validate remote responses before returning them for use or caching. Invalid remote data follows the existing static failure path; validation adds no retries. Streaming downloads retain their existing ownership and close behavior.

## Contract review decisions

| Family | Reviewed contract decisions |
| --- | --- |
| Tasks, chat and health | Require collection/message/result envelopes and service health fields; retain nullable legacy task values. |
| Authentication and profiles | Preserve cookies and header/form login, type nested organizations and roles, separate partial profile updates, and use static JWT error messages. |
| Assessment, analysis and publishing | Separate creation, partial updates and persisted responses; retain HTML summaries, repeated filters, conflict envelopes, historical revision maps and conditional files. |
| Admin/configuration | Bind both aliases, versioned imports, per-record skipped users, template results and queue state; retain provider parameter extension maps and domain checks in services. |
| Worker callbacks | Validate collection counts, pipeline selections/revisions, task notices, endpoint health and partial tag results before consumers act. |
| Intentional extension maps | Worker/provider parameters, attributes keyed by configured IDs, historical snapshots and external enrichment details retain their documented extension points. |

Response validation runs after handlers and may discover a failure after a mutation committed. A static 500 does not imply rollback; transports do not retry it automatically.
