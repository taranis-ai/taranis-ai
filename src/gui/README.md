# Taranis GUI

The GUI is written in [Vue.js](https://vuejs.org/) with [Vuetify](https://vuetifyjs.com/en/).

Currently, the best way to build and deploy is via Docker. For more information, see [docker/README.md](../../docker/README.md) and the [toplevel README.md file](../../README.md).

* Vue.js: As the primary frontend framework.
* Vuetify: As a UI library for Vue.js.
* Vite: For the frontend build tool and development server.

If you wish to develop and build the GUI separately, read on.

### Project setup

Install the dependencies

```bash
pnpm install
```

### Developing

You can run the GUI on the local machine, and edit it with your favorite IDE or text editor. The application will react to your changes in real time.
Depending on whether you expose your API directly on `http://localhost:5000` see [compose.yml](../../docker/compose.yml)

```
# env variables
env variables can be adapted in .env file


to run the applicaiton locally add `VITE_TARANIS_CONFIG_JSON = "/config.local.json"`  to .env file and add a `/config.local.json` file in the public folder. This can look like:

```

{
"TARANIS_CORE_API": "<http://localhost:5000/api>"
}

```bash
pnpm run dev
```

### Building the static version

When you are ready to generate the final static version of the GUI, run

```bash
pnpm run build
```

The static html/js/css files will be stored under the `dist/` subdirectory.

### Testing and linting

```bash
pnpm run test
pnpm run lint
```

### Customize the configuration

See [Configuration Reference](https://vite.dev/config/).
