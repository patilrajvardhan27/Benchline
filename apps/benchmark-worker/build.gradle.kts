plugins {
    java
    alias(libs.plugins.spring.boot)
    alias(libs.plugins.spring.dependency.management)
}

apply(from = rootProject.file("gradle/integration-test.gradle.kts"))

dependencies {
    implementation(project(":libs:java-common"))
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.kafka:spring-kafka")
    runtimeOnly("org.postgresql:postgresql")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")

    "integrationTestImplementation"(project(":libs:test-support"))
    "integrationTestRuntimeOnly"("org.flywaydb:flyway-database-postgresql")
    "integrationTestImplementation"("org.springframework.kafka:spring-kafka-test")
}

tasks.named<org.springframework.boot.gradle.tasks.bundling.BootJar>("bootJar") {
    archiveFileName.set("benchmark-worker.jar")
}
tasks.named<Jar>("jar") { enabled = false }
