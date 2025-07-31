taranis.ai - an OSINT application

See [README.md](../README.md) for more information.

- this project uses uv for managing python and packages
- the core (the backend, API) is a flask application located in `src/core`, it uses sqlalchemy
- the gui is a vue application located in `src/gui`
- the frontend is a flask application, built with htmx, daisyui. it is located in `/src/frontend`. currently, it only serves the admin section of the web interface, but the gui will be replaced by the frontend, piece by piece
- there are workers in 'src/workers'
- see .github/workflows, how tests are run
- run `uv run pytest` with various options like 'e2e-user' to run tests
- never use `git add -A` or in general do not add "all" files lying around

