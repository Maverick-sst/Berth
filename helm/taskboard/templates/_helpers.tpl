{{- define "berth.name" -}}berth{{- end -}}

{{- define "berth.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{ .Values.fullnameOverride }}
{{- else -}}
{{ .Release.Name }}-berth
{{- end -}}
{{- end -}}
