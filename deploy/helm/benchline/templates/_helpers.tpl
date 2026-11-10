{{/* Labels shared by every object. */}}
{{- define "benchline.labels" -}}
app.kubernetes.io/part-of: benchline
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "benchline.selector" -}}
app.kubernetes.io/name: {{ . }}
{{- end }}

{{/* Full image reference: registry/name:tag, registry optional. */}}
{{- define "benchline.image" -}}
{{- $g := .root.Values.global -}}
{{- if $g.imageRegistry -}}{{ $g.imageRegistry }}/{{- end -}}{{ .image }}:{{ $g.imageTag }}
{{- end }}

{{/* Environment every service gets: database, Kafka, flags, tracing. */}}
{{- define "benchline.commonEnv" -}}
- name: POSTGRES_URL
  value: jdbc:postgresql://{{ .Values.postgres.host }}:{{ .Values.postgres.port }}/{{ .Values.postgres.database }}
- name: POSTGRES_USER
  value: {{ .Values.postgres.user | quote }}
- name: ML_DATABASE_URL
  value: postgresql://{{ .Values.postgres.user }}:$(POSTGRES_PASSWORD)@{{ .Values.postgres.host }}:{{ .Values.postgres.port }}/{{ .Values.postgres.database }}
- name: KAFKA_BOOTSTRAP
  value: {{ .Values.kafka.bootstrap | quote }}
- name: ML_KAFKA_BOOTSTRAP
  value: {{ .Values.kafka.bootstrap | quote }}
- name: FLAGD_HOST
  value: {{ .Values.flagd.host | quote }}
- name: FLAGD_PORT
  value: {{ .Values.flagd.port | quote }}
{{- if .Values.otel.enabled }}
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: {{ .Values.otel.endpoint | quote }}
- name: JAVA_TOOL_OPTIONS
  value: -javaagent:{{ .Values.otel.agentPath }}
{{- end }}
{{- end }}
