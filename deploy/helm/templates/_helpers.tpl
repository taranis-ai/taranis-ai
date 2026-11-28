{{- define "taranis.labels" -}}
app.kubernetes.io/name: taranis
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "taranis.image" -}}
{{- printf "%s:%s" .repository .tag -}}
{{- end }}

{{- define "taranis.waitForCore" -}}
initContainers:
  - name: wait-for-{{ .role }}
    image: {{ include "taranis.image" .root.Values.images.core | quote }}
    imagePullPolicy: {{ .root.Values.global.imagePullPolicy }}
    envFrom:
      - configMapRef:
          name: taranis-config
    command: ["curl", "-fsS", "--max-time", "5", "http://{{ .role }}:8080$(TARANIS_BASE_PATH)api/ready"]
{{- end }}
