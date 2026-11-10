plugins {
    // Lets Gradle download a JDK 21 toolchain when the machine only has another JDK.
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

rootProject.name = "benchline"

include(
    "libs:java-common",
    "libs:test-support",
    "apps:pricing-api",
    "apps:benchmark-worker",
)
