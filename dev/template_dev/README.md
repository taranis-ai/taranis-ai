# Template Development Helper

The script in this folder helps developing Taranis AI Templates.

## Getting Started

```
uv run --with Flask --with jinja2 python template_dev.py
```
Running the Application
Start the Flask Application: Navigate to the folder containing the script and run the command above.


Accessing Default Template: To render the default template (template.html), simply visit:

[http://localhost:5000/](http://localhost:5000/)


### Using Dynamic Templates

To render a specific template file, first place the file into this folder and then append the file name to the URL.
Only plain file names in this folder are accepted. Absolute paths, path separators, and traversal segments are rejected.

For example, to render templatex.txt, visit:

[http://localhost:5000/templatex.txt](http://localhost:5000/templatex.txt)
