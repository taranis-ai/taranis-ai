# Taranis NG GUI

The GUI is written in [Vue.js](https://vuejs.org/) with [Vuetify](https://vuetifyjs.com/en/).

Currently, the best way to build and deploy is via Docker. For more information, see [docker/README.md](../../docker/README.md) and the [toplevel README.md file](../../README.md).

If you wish to develop and build the GUI separately, read on.

### Project setup

Install the dependencies

```
npm install
```

### Developing

You can run the GUI on the local machine, and edit it with your favorite IDE or text editor. The application will react to your changes in real time.

```
# set the environment variables needed by GUI
export VUE_APP_TARANIS_NG_CORE_API="http://localhost:5000/api/v1"
export VUE_APP_TARANIS_NG_CORE_SSE="http://localhost:5000/sse"
export VUE_APP_TARANIS_NG_URL="http://localhost:8080"
export VUE_APP_TARANIS_NG_LOCALE="en"

# run the development server
npm run serve
```

### Building the static version

When you are ready to generate the final static version of the GUI, run

```
npm run build
```

The static html/js/css files will be stored under the `dist/` subdirectory.

### Testing and linting

```
npm run test
npm run lint
```

### Customize the configuration

See [Configuration Reference](https://cli.vuejs.org/config/).
