#!/bin/bash
set -x

if [ $# -eq 0 ]; then
    echo "Usage: $0 [up|down]"
    exit 1
fi

case "$1" in
    up)
        TARANIS_GUI_PORT=8083
        TARANIS_CORE_API_PORT=5002
        export TARANIS_SSE_UPSTREAM=127.0.0.1
        if ! ss -tulwn | grep -q ":$TARANIS_GUI_PORT " && ! ss -tulwn | grep -q ":$TARANIS_CORE_API_PORT "; then
            echo "Ports ($PORT1 and $PORT2) for Taranis test setup are free."
        else
            echo "At least one of the ports $TARANIS_GUI_PORT or $TARANIS_CORE_API_PORT is in use.";
            echo "Please free up the ports and try again.";
            echo "You can check the service running using the following command:";
            echo "ss -tulpn | grep ':<PORT>'";
            exit 1;
        fi


        # ENVs for Core and GUI
        CORE_ENV_PATH="$(git rev-parse --show-toplevel)/src/core/"
        GUI_ENV_PATH="$(git rev-parse --show-toplevel)/src/gui/"


        echo -e "VITE_TARANIS_CONFIG_JSON=\"/config.e2e_test.json\"" | tee -a "$CORE_ENV_PATH/.env" "$GUI_ENV_PATH/.env"



        # GUI
        GUI_CORE_GUI_CONFIG="config.e2e_test.json"
        echo -e "{\n  \"TARANIS_CORE_API\": \"http://127.0.0.1:$TARANIS_CORE_API_PORT/api\"\n}" > "$GUI_CONFIG_PATH/public/$GUI_CORE_GUI_CONFIG"
        echo "File $GUI_CORE_GUI_CONFIG has been created with the required content."

        cd "$(git rev-parse --show-toplevel)/src/gui" || {
            echo "Error: Failed to navigate to the Docker directory."; exit 1;
        }
        npm run dev
        sleep 5
        unset VITE_TARANIS_CONFIG_JSON
        ;;
    down)
        CORE_ENV_PATH="$(git rev-parse --show-toplevel)/src/core/.env"
        LINE="TARANIS_CORE_URL=http://127.0.0.1:$TARANIS_CORE_API_PORT/api"
        tac "$CORE_ENV_PATH" | sed "0,/^${LINE}$/d" | tac > temp_file && mv temp_file "$CORE_ENV_PATH"
        ;;
    *)
        echo "Invalid argument: $1"
        echo "Usage: $0 [up|down]"
        exit 1
        ;;
esac

set +x
