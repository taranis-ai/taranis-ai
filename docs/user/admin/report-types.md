---
title: "Report Types"
description: >
    Admin users can manage report types (in the Administration tab). Each report type can have different attribute groups. To those groups various attributes (Text Area, Date, TLP, CPE, etc.) can be added. Attributes can be managed in Administration/Attributes.
weight: 4
---

> [!NOTE]
> When creating new Reports, one of the created report types have to be selected (see [Analyze](../analyze/_index.md)).


### Attributes
Desired attributes need to be created first. Then they can be managed by the admin user. Besides name, description and default value also type, validator and validator parameter can be set.

### Report Types - CRUD
* Create: Report types can be created ("New item"). After adding a new attribute group, different attributes can be added to this group.
* Read & Update: Report types (including their attribute groups) can be updated by clicking on them in the list. Their update will not affect Reports, which already use the Report Type
* Delete: One or multiple reports can be deleted at once.

## Screenshots
Add new Attribute

![report_type_add_attribute](../images/add_attribute.png)

Report Types -  Create new Report Type

![report_type_create](../images/report_type_add_new_attribute.png)

Report Types - Add new Attribute Group

![report_type_group](../images/report_type_group.png)

Report Types - Select new Attribute from list

![report_type_select_attribute](../images/report_type_select_attribute.png)
