# Data Folder Management

This system facilitates the handling of presenter templates, including synchronization, addition, retrieval, and deletion of templates stored in a specific directory designated by the Config.DATA_FOLDER configuration.


## Presenter Templates Synchronization
The sync_presenter_templates_to_data method synchronizes presenter templates from a source directory (typically a folder inside your venv) to a destination directory within the Config.DATA_FOLDER. This synchronization process includes:

1. Source and Destination Paths: Identifies the source (static/presenter_templates) and destination (Config.DATA_FOLDER/presenter_templates) paths.
1. Hash File Management: Reads and updates a JSON file (template_hashes.json) that stores the hashes of the templates. This file is used to track changes to the templates.
1. File Copy and Hash Update: Copies each template from the source to the destination if it does not exist in the destination or if its content has changed (detected via hash comparison). Updates the hash file accordingly.
