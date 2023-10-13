# Taranis GUI

The GUI is written in [Vue.js](https://vuejs.org/) with [Vuetify](https://vuetifyjs.com/en/).

Currently, the best way to build and deploy is via Docker. For more information, see [docker/README.md](../../docker/README.md) and the [toplevel README.md file](../../README.md).

If you wish to develop and build the GUI separately, read on.

### Project setup

Install the dependencies

```
npm install
```

### Developing

You can run the GUI on the local machine, and edit it with your favorite IDE or text editor. The application will react to your changes in real time. Depending on whether you expose your API directly on `http://localhost:5000` (see `docker-compose.yml`), via Traefik on `https://localhost:4443`, or on a public IP and host name, you may need to change the following environment variables.

```
# env variables
env variables can be adapted in .env file


to run the applicaiton locally add `VITE_TARANIS_CONFIG_JSON = "/config.local.json"`  to .env file and add a `/config.local.json` file in the public folder. This can look like:

```

{
"TARANIS_CORE_API": "http://localhost:5000/api"
}

```
npm run dev
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
