{{- define "taranis.labels" -}}
app.kubernetes.io/name: taranis
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "taranis.selectorLabels" -}}
app.kubernetes.io/part-of: taranis
{{- end }}

{{- define "taranis.image" -}}
{{- printf "%s:%s" .repository .tag -}}
{{- end }}
