# Builds either Spring app: docker build -f deploy/docker/spring.Dockerfile --build-arg APP=pricing-api .
FROM eclipse-temurin:25-jdk-alpine AS build
ARG APP
WORKDIR /src
COPY gradlew settings.gradle.kts build.gradle.kts ./
COPY gradle gradle
COPY libs libs
COPY apps apps
RUN ./gradlew --no-daemon -q :apps:${APP}:bootJar -x test \
 && cp apps/${APP}/build/libs/${APP}.jar /app.jar

# OpenTelemetry agent. Turned on at runtime with JAVA_TOOL_OPTIONS=-javaagent:/otel/agent.jar
FROM alpine:3.22 AS otel
ARG OTEL_AGENT_VERSION=2.33.1
RUN wget -q -O /agent.jar \
    https://repo.maven.apache.org/maven2/io/opentelemetry/javaagent/opentelemetry-javaagent/${OTEL_AGENT_VERSION}/opentelemetry-javaagent-${OTEL_AGENT_VERSION}.jar

FROM eclipse-temurin:25-jre-alpine
# Numeric user so Kubernetes can enforce runAsNonRoot.
RUN addgroup -S -g 10001 app && adduser -S -u 10001 -G app app
WORKDIR /app
COPY --from=build /app.jar app.jar
COPY --from=otel /agent.jar /otel/agent.jar
USER 10001:10001
EXPOSE 8080 8081
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError"
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar app.jar"]
