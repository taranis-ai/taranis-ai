function llmEndpointState(config) {
  const formats = config.formats || {};
  const state = {
    provider: config.provider || "openai_compatible",
    endpointId: config.provider === "orcarouter" ? config.endpointId || "" : "",
    baseUrl: config.baseUrl || "",
    catalogUrl: config.catalogUrl,
    defaultModel: config.defaultModel || "",
    orcaBaseUrl: config.orcaBaseUrl || "",
    providerDefaults: config.providerDefaults || {},
    formats: {},
  };
  Object.keys(formats).forEach((apiFormat) => {
    state.formats[apiFormat] = {
      value: formats[apiFormat].model || "",
      items: [],
      filter: "",
      open: false,
      loading: false,
      loaded: false,
      source: "",
      degraded: false,
      cached: false,
      error: "",
      hint: "",
    };
  });
  return state;
}

function llmEndpoint(config) {
  const state = llmEndpointState(config);

  Object.defineProperty(state, "isOrca", {
    get() {
      return this.provider === "orcarouter";
    },
  });

  state.modelsFor = function (apiFormat) {
    const format = this.formats[apiFormat];
    if (!format) {
      return [];
    }
    const term = format.filter.trim().toLowerCase();
    if (!term) {
      return format.items;
    }
    return format.items.filter((item) => {
      return `${item.id} ${item.name || ""}`.toLowerCase().includes(term);
    });
  };

  state.selectedLabel = function (apiFormat) {
    const format = this.formats[apiFormat];
    if (!format || !format.value) {
      return "Provider default";
    }
    const match = format.items.find((item) => item.id === format.value);
    return match ? `${match.name || match.id} (${match.id})` : format.value;
  };

  state.isSelected = function (apiFormat, modelId) {
    const format = this.formats[apiFormat];
    return Boolean(format && format.value === modelId);
  };

  state.selectModel = function (apiFormat, modelId) {
    const format = this.formats[apiFormat];
    if (!format) {
      return;
    }
    format.value = modelId;
    format.open = false;
    format.hint = "";
  };

  state.togglePanel = function (apiFormat) {
    const format = this.formats[apiFormat];
    if (!format) {
      return;
    }
    format.open = !format.open;
    if (format.open && !format.loaded && this.isOrca) {
      this.loadModels(apiFormat);
    }
  };

  state.catalogPayload = function (apiFormat, refresh) {
    const payload = {
      provider: this.provider,
      api_format: apiFormat,
      base_url: this.baseUrl,
      refresh: Boolean(refresh),
    };
    if (this.endpointId) {
      payload.endpoint_id = this.endpointId;
    }
    const keyInput = this.$el.querySelector('input[name="api_key"]');
    if (keyInput && keyInput.value) {
      payload.api_key = keyInput.value;
    }
    return payload;
  };

  state.loadModels = function (apiFormat, refresh) {
    const format = this.formats[apiFormat];
    if (!format || !this.isOrca) {
      return;
    }
    if (!this.endpointId) {
      const baseInput = this.$el.querySelector('input[name="base_url"]');
      this.baseUrl = baseInput ? baseInput.value : this.baseUrl;
      const keyInput = this.$el.querySelector('input[name="api_key"]');
      if (!keyInput || !keyInput.value.trim()) {
        format.error = "Enter an API key to load the live OrcaRouter model catalogue.";
        format.loaded = true;
        format.loading = false;
        return;
      }
    }
    format.loading = true;
    format.error = "";
    fetch(this.catalogUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-TOKEN": getCSRFToken() || "",
      },
      body: JSON.stringify(this.catalogPayload(apiFormat, refresh)),
    })
      .then((response) => response.json().then((payload) => ({ payload, ok: response.ok })))
      .then(({ payload }) => {
        const previous = format.value;
        const items = Array.isArray(payload.models) ? payload.models : [];
        format.items = items;
        format.source = payload.source || "";
        format.degraded = Boolean(payload.degraded);
        format.cached = Boolean(payload.cached);
        format.error = payload.error || "";
        format.loaded = true;
        if (previous && !items.some((item) => item.id === previous)) {
          format.value = "";
          format.hint =
            "The previously selected model is not available for this format. Choose a compatible model.";
        }
        if (!format.value) {
          const preferred = payload.default_model || this.defaultModel;
          if (preferred && items.some((item) => item.id === preferred)) {
            format.value = preferred;
          }
        }
        if (!items.length && !format.error) {
          format.error = "No compatible models were returned for this format.";
        }
      })
      .catch(() => {
        format.error = "The OrcaRouter model catalogue could not be reached. Retry or keep the current model.";
        format.degraded = true;
        format.loaded = true;
      })
      .finally(() => {
        format.loading = false;
      });
  };

  state.loadAll = function (refresh) {
    if (!this.isOrca) {
      return;
    }
    Object.keys(this.formats).forEach((apiFormat) => this.loadModels(apiFormat, refresh));
  };

  state.onProviderChange = function () {
    const baseInput = this.$el.querySelector('input[name="base_url"]');
    if (this.isOrca && baseInput) {
      const knownDefaults = Object.values(this.providerDefaults);
      if (!baseInput.value || knownDefaults.includes(baseInput.value)) {
        baseInput.value = this.orcaBaseUrl;
      }
      this.baseUrl = baseInput.value;
    }
    if (this.isOrca) {
      this.loadAll();
    }
  };

  state.onFieldChange = function (event) {
    if (!event.target) {
      return;
    }
    if (event.target.name === "provider") {
      this.provider = event.target.value;
      this.onProviderChange();
    }
    if (event.target.name === "base_url" && this.isOrca) {
      this.baseUrl = event.target.value;
      this.loadAll();
    }
    if (event.target.name === "api_key" && this.isOrca) {
      this.loadAll(Boolean(event.target.value.trim()));
    }
  };

  state.init = function () {
    if (this.isOrca) {
      this.loadAll();
    }
  };

  return state;
}

window.llmEndpoint = llmEndpoint;
