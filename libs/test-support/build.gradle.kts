plugins {
    `java-library`
}

// Shared base class for integration tests. Only test source sets depend on it.
dependencies {
    api(platform("org.springframework.boot:spring-boot-dependencies:${libs.versions.spring.boot.get()}"))
    api("org.junit.jupiter:junit-jupiter-api")
    api("org.springframework:spring-test")
    api("org.springframework:spring-jdbc")
    api("org.testcontainers:postgresql")
    api("org.testcontainers:junit-jupiter")
    api("org.flywaydb:flyway-core")
    runtimeOnly("org.flywaydb:flyway-database-postgresql")
}
