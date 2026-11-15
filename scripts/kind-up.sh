#!/usr/bin/env bash
# Builds every image, loads it into a local kind cluster, installs the Helm chart and runs its smoke test.
# Used by CI and on a laptop: scripts/kind-up.sh   (remove with: kind delete cluster --name benchline)
set -euo pipefail
cd "$(dirname "$0")/.."

CLUSTER=${KIND_CLUSTER:-benchline}
TAG=ci
CHART=deploy/helm/benchline

images=(
  "benchline-pricing-api deploy/docker/spring.Dockerfile APP=pricing-api"
  "benchline-benchmark-worker deploy/docker/spring.Dockerfile APP=benchmark-worker"
  "benchline-ml-service deploy/docker/ml.Dockerfile"
  "benchline-web deploy/docker/web.Dockerfile"
  "benchline-migrate deploy/docker/migrate.Dockerfile"
  "benchline-lag-monitor deploy/docker/lag-monitor.Dockerfile"
)

for entry in "${images[@]}"; do
  read -r name file arg <<<"$entry"
  echo "building $name"
  docker build -q -t "$name:$TAG" -f "$file" ${arg:+--build-arg "$arg"} . >/dev/null
done

kind get clusters 2>/dev/null | grep -qx "$CLUSTER" || kind create cluster --name "$CLUSTER" --wait 2m
kubectl config use-context "kind-$CLUSTER" >/dev/null

for entry in "${images[@]}"; do
  read -r name _ <<<"$entry"
  kind load docker-image "$name:$TAG" --name "$CLUSTER"
done

helm lint "$CHART" -f "$CHART/values-kind.yaml"
helm upgrade --install benchline "$CHART" -f "$CHART/values-kind.yaml" --wait --wait-for-jobs --timeout 10m
kubectl get pods
helm test benchline --logs --timeout 5m
